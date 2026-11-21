"""From-scratch NumPy rasteriser for Module 3 Lab 2.

Pipeline: model/view/projection -> homogeneous near clipping -> perspective
 divide -> viewport -> barycentric coverage -> NDC z-buffer -> perspective-
correct UV -> bilinear texture sampling -> Lambert shading.

Texture PNG/MTL decoding is delegated to material_io.py (Pillow image I/O).
All geometric and per-fragment rendering operations are implemented here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from transforms import perspective, look_at, rot_y, translate, scale
from objio import load_obj, Mesh
from ppm_io import read_ppm, write_ppm
from srgb import srgb_to_linear, linear_to_srgb
from material_io import load_materials


def sample_bilinear(tex_lin, u, v):
    """Bilinear sample in linear light; repeat-wrap U/V; arrays are broadcast."""
    H, W = tex_lin.shape[:2]
    u = np.mod(u, 1.0) * W - 0.5
    v = np.mod(v, 1.0) * H - 0.5
    x0 = np.floor(u).astype(np.int64); y0 = np.floor(v).astype(np.int64)
    fx = (u - x0)[..., None]; fy = (v - y0)[..., None]
    x0m = np.mod(x0, W); x1m = np.mod(x0 + 1, W)
    y0m = np.mod(y0, H); y1m = np.mod(y0 + 1, H)
    top = tex_lin[y0m, x0m] * (1.0 - fx) + tex_lin[y0m, x1m] * fx
    bot = tex_lin[y1m, x0m] * (1.0 - fx) + tex_lin[y1m, x1m] * fx
    return top * (1.0 - fy) + bot * fy


def build_mip_pyramid(tex_u8, levels=4):
    """Build 4 (default) mip levels using gamma-correct 2x2 box filtering.

    The returned arrays are linear-light RGB float arrays. Averaging therefore
    occurs after sRGB decoding, not directly on encoded 8-bit values.
    """
    current = srgb_to_linear(np.asarray(tex_u8, dtype=np.float64) / 255.0)
    chain = [current]
    for _ in range(1, max(1, int(levels))):
        h, w = current.shape[:2]
        if h == 1 and w == 1:
            break
        # Edge replication ensures odd dimensions are not discarded.
        pad_h = h % 2; pad_w = w % 2
        padded = np.pad(current, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
        current = (padded[0::2, 0::2] + padded[1::2, 0::2] +
                   padded[0::2, 1::2] + padded[1::2, 1::2]) * 0.25
        chain.append(current)
    return chain


def _texture_chains(tex_u8, mipmap=False):
    if tex_u8 is None:
        return {}
    if isinstance(tex_u8, dict):
        return {k: build_mip_pyramid(v, 4 if mipmap else 1) for k, v in tex_u8.items()}
    return {None: build_mip_pyramid(tex_u8, 4 if mipmap else 1)}


def _material_texture(mesh, face_index, chains):
    name = mesh.face_material(face_index)
    if name in chains:
        return name, chains[name]
    if None in chains:
        return None, chains[None]
    return name, None


def _lod_for_triangle(sx, sy, uv, tex_shape, levels):
    """Estimate a triangle's texture footprint and choose a mip level."""
    if levels <= 1:
        return 0
    A = np.column_stack((sx, sy, np.ones(3)))
    try:
        cu = np.linalg.solve(A, uv[:, 0])
        cv = np.linalg.solve(A, uv[:, 1])
    except np.linalg.LinAlgError:
        return 0
    tex_h, tex_w = tex_shape[:2]
    rho_x = np.hypot(cu[0] * tex_w, cv[0] * tex_h)
    rho_y = np.hypot(cu[1] * tex_w, cv[1] * tex_h)
    rho = max(float(rho_x), float(rho_y), 1.0)
    return int(np.clip(np.rint(np.log2(rho)), 0, levels - 1))


def clip_triangle_near(vc, attrs):
    """Clip one triangle against OpenGL near plane z+w>=0 (Sutherland-Hodgman).

    Returns zero, one, or two triangles. Attributes are linearly clipped in
    homogeneous clip space and later perspective-corrected after division.
    """
    def inside(p):
        return p[2] + p[3] >= 0.0
    poly = [(vc[i], attrs[i]) for i in range(3)]
    out = []
    for i in range(len(poly)):
        cur_v, cur_a = poly[i]
        prv_v, prv_a = poly[(i - 1) % len(poly)]
        ci, pi = inside(cur_v), inside(prv_v)
        if ci != pi:
            d0 = prv_v[2] + prv_v[3]
            d1 = cur_v[2] + cur_v[3]
            t = d0 / (d0 - d1)
            out.append((prv_v + t * (cur_v - prv_v), prv_a + t * (cur_a - prv_a)))
        if ci:
            out.append((cur_v, cur_a))
    if len(out) < 3:
        return []
    return [(np.stack([out[0][0], out[k][0], out[k + 1][0]]),
             np.stack([out[0][1], out[k][1], out[k + 1][1]]))
            for k in range(1, len(out) - 1)]


def render(mesh, *, w, h, tex_u8=None, material_colors=None, model=None,
           tri_colors=None, eye=(3.4, 2.5, 4.2), center=(0, 0.8, 0),
           fovy=45.0, near=0.1, far=50.0, light_dir=(0.4, 0.9, 0.6),
           ambient=0.15, cull_back=False, depth_bits=None, mipmap=False,
           perspective_correct=True):
    """Render a Mesh to (uint8 RGB, float NDC-depth, fragment-count).

    tex_u8 may be one RGB array (legacy starter) or {material_name: RGB array}.
    depth_bits optionally quantises depth to reproduce z-fighting.
    """
    if model is None:
        model = np.eye(4)
    model = np.asarray(model, dtype=np.float64)
    eye_pos = np.asarray(eye, dtype=np.float64)
    P = perspective(fovy, w / h, near, far)
    V = look_at(eye, center)
    pos_h = np.c_[mesh.positions, np.ones(len(mesh.positions))]
    world = (model @ pos_h.T).T[:, :3]
    clip = (P @ V @ model @ pos_h.T).T
    tris_pos = mesh.faces
    tris_uv = mesh.triangle_uvs()
    chains = _texture_chains(tex_u8, mipmap=mipmap)
    material_colors = material_colors or {}
    L = np.asarray(light_dir, dtype=np.float64)
    L /= max(np.linalg.norm(L), 1e-12)

    color = np.zeros((h, w, 3), dtype=np.float64)
    depth = np.full((h, w), np.inf, dtype=np.float64)
    filled = 0

    for fi, vidx in enumerate(tris_pos):
        vc = clip[vidx]
        wp = world[vidx]
        nrm = np.cross(wp[1] - wp[0], wp[2] - wp[0])
        nl = np.linalg.norm(nrm)
        if nl < 1e-12:
            continue
        nrm /= nl
        if nrm @ (eye_pos - wp[0]) < 0:
            nrm = -nrm
        shade = ambient + (1.0 - ambient) * max(0.0, float(nrm @ L))
        uv = tris_uv[fi]
        attrs = np.c_[uv, np.ones(3)]

        mat_name, chain = _material_texture(mesh, fi, chains)
        for cvc, cattr in clip_triangle_near(vc, attrs):
            wv = cvc[:, 3]
            if np.any(np.abs(wv) < 1e-12):
                continue
            ndc = cvc[:, :3] / wv[:, None]
            sx = (ndc[:, 0] * 0.5 + 0.5) * w
            sy = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * h
            sz = ndc[:, 2]
            inv_w = 1.0 / wv
            uvw = cattr[:, :2] * inv_w[:, None]

            minx = max(0, int(np.floor(sx.min())))
            maxx = min(w - 1, int(np.ceil(sx.max())))
            miny = max(0, int(np.floor(sy.min())))
            maxy = min(h - 1, int(np.ceil(sy.max())))
            if minx > maxx or miny > maxy:
                continue

            ax, ay = sx[0], sy[0]
            bx, by = sx[1], sy[1]
            cx, cy = sx[2], sy[2]
            area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            if abs(area) < 1e-12:
                continue
            # Screen coordinates have y down; CCW front faces have negative area.
            if cull_back and area > 0:
                continue

            ys, xs = np.mgrid[miny:maxy + 1, minx:maxx + 1]
            px, py = xs + 0.5, ys + 0.5
            lA = ((cx - bx) * (py - by) - (cy - by) * (px - bx)) / area
            lB = ((ax - cx) * (py - cy) - (ay - cy) * (px - cx)) / area
            lC = 1.0 - lA - lB
            inside = (lA >= -1e-10) & (lB >= -1e-10) & (lC >= -1e-10)
            if not inside.any():
                continue
            frag_z = lA * sz[0] + lB * sz[1] + lC * sz[2]
            if depth_bits is not None:
                q = float(2 ** int(depth_bits) - 1)
                frag_z = np.round((frag_z * 0.5 + 0.5) * q) / q * 2.0 - 1.0
            inv_w_i = lA * inv_w[0] + lB * inv_w[1] + lC * inv_w[2]
            region_d = depth[miny:maxy + 1, minx:maxx + 1]
            wins = inside & (frag_z < region_d)
            if not wins.any():
                continue
            region_d[wins] = frag_z[wins]

            if chain is not None:
                level = 0
                if mipmap and len(chain) > 1:
                    level = _lod_for_triangle(sx, sy, cattr[:, :2], chain[0].shape, len(chain))
                tex = chain[level]
                if perspective_correct:
                    uu = (lA * uvw[0, 0] + lB * uvw[1, 0] + lC * uvw[2, 0]) / np.maximum(inv_w_i, 1e-12)
                    vv = (lA * uvw[0, 1] + lB * uvw[1, 1] + lC * uvw[2, 1]) / np.maximum(inv_w_i, 1e-12)
                else:
                    # Deliberately incorrect teaching path: screen-linear UV.
                    uu = lA * cattr[0, 0] + lB * cattr[1, 0] + lC * cattr[2, 0]
                    vv = lA * cattr[0, 1] + lB * cattr[1, 1] + lC * cattr[2, 1]
                tex_rgb = sample_bilinear(tex, uu, vv)
            elif tri_colors is not None:
                tex_rgb = np.broadcast_to(srgb_to_linear(np.asarray(tri_colors[fi], dtype=float) / 255.0),
                                          (*lA.shape, 3))
            else:
                kd = material_colors.get(mat_name, (0.7, 0.7, 0.7))
                tex_rgb = np.broadcast_to(srgb_to_linear(np.asarray(kd, dtype=float)), (*lA.shape, 3))
            lit = linear_to_srgb(np.clip(tex_rgb * shade, 0.0, 1.0))
            region_c = color[miny:maxy + 1, minx:maxx + 1]
            region_c[wins] = lit[wins]
            filled += int(wins.sum())

    return np.clip(np.rint(color * 255.0), 0, 255).astype(np.uint8), depth, filled


def _demo_triangle(w, h):
    pos = np.array([[-0.8, -0.6, -2.0], [0.9, -0.7, -3.5], [-0.2, 0.9, -2.5]])
    uv = np.array([[0, 0], [1, 0], [0.5, 1.0]])
    m = Mesh(pos, uv, [[0, 1, 2]], [[0, 1, 2]])
    tex = read_ppm("data/relief.ppm") if Path("data/relief.ppm").exists() else None
    P = perspective(60, w / h, 1.0, 50.0)
    clip = (P @ np.c_[pos, np.ones(3)].T).T
    invw = 1.0 / clip[:, 3]
    pc = (uv * invw[:, None]).mean(0) / invw.mean()
    print(f"perspective-correct UV at triangle centroid: ({pc[0]:.3f}, {pc[1]:.3f}); "
          f"naive: ({uv[:,0].mean():.3f}, {uv[:,1].mean():.3f})")
    col, dep, filled = render(m, w=w, h=h, tex_u8=tex, eye=(0, 0, 0),
                              center=(0, 0, -1), near=1, far=50,
                              light_dir=(0, 0, 1))
    Path("out").mkdir(exist_ok=True)
    write_ppm("out/tri_raster.ppm", col)
    finite = dep[np.isfinite(dep)]
    print(f"filled fragments: {filled}; depth range: [{finite.min():.3f}, {finite.max():.3f}]")
    print("wrote out/tri_raster.ppm")


def _demo_overlap(w, h):
    front = [[-0.7, -0.7, -1.5], [0.7, -0.7, -1.5], [0.0, 0.7, -1.5]]
    back = [[-0.2, -0.7, -3.0], [1.2, -0.7, -3.0], [0.5, 0.7, -3.0]]
    pos = np.array(front + back)
    m = Mesh(pos, np.zeros((0, 2)), [[0, 1, 2], [3, 4, 5]])
    colors = [(230, 130, 40), (60, 120, 210)]
    col, dep, filled = render(m, w=w, h=h, near=1, far=50,
                              eye=(0, 0, 0), center=(0, 0, -1),
                              tri_colors=colors, light_dir=(0, 0, 1))
    Path("out").mkdir(exist_ok=True)
    write_ppm("out/overlap.ppm", col)
    print(f"z-buffer demo: {filled} visible fragments; back triangle is occluded in overlap")


def main():
    ap = argparse.ArgumentParser(description="NumPy 3D rasteriser")
    ap.add_argument("--model")
    ap.add_argument("--w", type=int, default=192)
    ap.add_argument("--h", type=int, default=192)
    ap.add_argument("--out", default="out/tugu_raster.ppm")
    ap.add_argument("--demo-triangle", action="store_true")
    ap.add_argument("--demo-overlap", action="store_true")
    ap.add_argument("--mipmap", action="store_true")
    args = ap.parse_args()
    if args.demo_triangle:
        _demo_triangle(args.w, args.h); return
    if args.demo_overlap:
        _demo_overlap(args.w, args.h); return
    if not args.model:
        ap.error("provide --model, --demo-triangle, or --demo-overlap")
    mesh = load_obj(args.model)
    tex, colors, meta = load_materials(args.model)
    # Deterministic camera and neutral model transform for the normalized Lab 1 asset.
    model = rot_y(12.0)
    img, dep, filled = render(mesh, w=args.w, h=args.h, tex_u8=tex,
                              material_colors=colors, model=model, mipmap=args.mipmap)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_ppm(out, img)
    finite = np.isfinite(dep)
    depth_vis = np.where(finite, (dep + 1.0) * 0.5, 1.0)
    depth_rgb = np.repeat((np.clip(depth_vis, 0, 1) * 255).astype(np.uint8)[..., None], 3, axis=2)
    depth_path = out.with_name(out.stem.replace("raster", "depth") + ".ppm")
    write_ppm(depth_path, depth_rgb)
    print(f"model: {mesh.n_tris:,} triangles; frame: {args.w}x{args.h}; materials: {len(mesh.material_names)}")
    print(f"textured materials loaded: {len(tex)}; filled fragments: {filled:,}")
    if finite.any():
        print(f"NDC depth range: [{dep[finite].min():.6f}, {dep[finite].max():.6f}]")
    print(f"wrote {out} and {depth_path}; mipmap={'on' if args.mipmap else 'off'}")


if __name__ == "__main__":
    main()
