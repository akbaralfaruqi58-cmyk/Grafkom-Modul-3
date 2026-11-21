"""One-frame pinhole ray tracer for Module 3 Lab 2.

Uses Moller-Trumbore triangle intersection, nearest-hit visibility, the same
OBJ UV convention, MTL textures, bilinear sampling and Lambert shading as the
NumPy rasteriser. It is intentionally a simple O(pixels * triangles) reference
renderer, not a real-time acceleration-structure implementation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from transforms import rot_y
from objio import load_obj
from material_io import load_materials
from ppm_io import write_ppm
from srgb import srgb_to_linear, linear_to_srgb
from raster3d import sample_bilinear


def moller_trumbore(orig, dirs, v0, v1, v2):
    """Vectorised Moller-Trumbore test; `dirs` is (P,3), misses return t=inf."""
    eps = 1e-9
    e1, e2 = v1 - v0, v2 - v0
    pvec = np.cross(dirs, e2)
    det = pvec @ e1
    valid_det = np.abs(det) >= eps
    inv_det = np.zeros_like(det)
    inv_det[valid_det] = 1.0 / det[valid_det]
    tvec = orig - v0
    u = (pvec @ tvec) * inv_det
    qvec = np.cross(tvec, e1)
    v = (dirs @ qvec) * inv_det
    t = (qvec @ e2) * inv_det
    hit = valid_det & (u >= -eps) & (v >= -eps) & (u + v <= 1.0 + eps) & (t > eps)
    return np.where(hit, t, np.inf), u, v


def render(mesh, *, w, h, tex_u8=None, material_colors=None, model=None,
           eye=(3.4, 2.5, 4.2), center=(0, 0.8, 0), fovy=45.0,
           near=0.1, far=50.0, light_dir=(0.4, 0.9, 0.6), ambient=0.15,
           triangle_chunk=None):
    """Cast a camera ray through each pixel and shade the nearest hit."""
    if model is None:
        model = np.eye(4)
    pos_h = np.c_[mesh.positions, np.ones(len(mesh.positions))]
    world = (np.asarray(model) @ pos_h.T).T[:, :3]
    tris = world[mesh.faces]
    tuv = mesh.triangle_uvs()
    eye = np.asarray(eye, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)
    fwd = center - eye
    fwd /= np.linalg.norm(fwd)
    up_seed = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up_seed)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    aspect = w / h
    tan_half = np.tan(np.radians(fovy) / 2.0)

    ii, jj = np.mgrid[0:h, 0:w]
    ndc_x = (jj + 0.5) / w * 2.0 - 1.0
    ndc_y = 1.0 - (ii + 0.5) / h * 2.0
    dirs = (ndc_x[..., None] * right * tan_half * aspect +
            ndc_y[..., None] * up * tan_half + fwd)
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    D = dirs.reshape(-1, 3)
    view_cos = D @ fwd

    best_t = np.full(len(D), np.inf, dtype=np.float64)
    best_face = np.full(len(D), -1, dtype=np.int32)
    best_uv = np.zeros((len(D), 2), dtype=np.float64)
    # Loop over triangles; every vector operation is performed for all pixels.
    for fi, tri in enumerate(tris):
        v0, v1, v2 = tri
        t, bu, bv = moller_trumbore(eye, D, v0, v1, v2)
        view_depth = t * view_cos
        valid = (view_depth >= near) & (view_depth <= far)
        t = np.where(valid, t, np.inf)
        closer = t < best_t
        if closer.any():
            best_t[closer] = t[closer]
            best_face[closer] = fi
            bw = 1.0 - bu - bv
            uvv = (bw[:, None] * tuv[fi, 0] +
                   bu[:, None] * tuv[fi, 1] +
                   bv[:, None] * tuv[fi, 2])
            best_uv[closer] = uvv[closer]

    light = np.asarray(light_dir, dtype=np.float64)
    light /= max(np.linalg.norm(light), 1e-12)
    out_linear = np.zeros((len(D), 3), dtype=np.float64)
    colors = material_colors or {}
    texture_linear = {}
    if tex_u8:
        for name, arr in tex_u8.items():
            texture_linear[name] = srgb_to_linear(np.asarray(arr, dtype=np.float64) / 255.0)
    hit_pixels = np.flatnonzero(best_face >= 0)
    # Group pixels by the intersected triangle to keep the same flat-face normal
    # and material as the rasteriser.
    if hit_pixels.size:
        for fi in np.unique(best_face[hit_pixels]):
            pix = np.flatnonzero(best_face == fi)
            v0, v1, v2 = tris[fi]
            normal = np.cross(v1 - v0, v2 - v0)
            normal /= max(np.linalg.norm(normal), 1e-12)
            centroid = (v0 + v1 + v2) / 3.0
            if normal @ (eye - centroid) < 0:
                normal = -normal
            lambert = ambient + (1.0 - ambient) * max(0.0, float(normal @ light))
            mat_name = mesh.face_material(int(fi))
            if mat_name in texture_linear:
                rgb = sample_bilinear(texture_linear[mat_name],
                                      best_uv[pix, 0], best_uv[pix, 1])
            else:
                kd = np.asarray(colors.get(mat_name, (0.7, 0.7, 0.7)), dtype=np.float64)
                rgb = np.broadcast_to(srgb_to_linear(kd), (len(pix), 3))
            out_linear[pix] = np.clip(rgb * lambert, 0.0, 1.0)

    image = linear_to_srgb(out_linear).reshape(h, w, 3)
    depth = (best_t * view_cos).reshape(h, w)
    return np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8), depth


def main():
    ap = argparse.ArgumentParser(description="Pinhole ray tracer (Moller-Trumbore)")
    ap.add_argument("--model", default="data/mymodel.obj")
    ap.add_argument("--w", type=int, default=128)
    ap.add_argument("--h", type=int, default=128)
    ap.add_argument("--out", default="out/tugu_raytrace.ppm")
    args = ap.parse_args()
    mesh = load_obj(args.model)
    textures, colors, _ = load_materials(args.model)
    image, depth = render(mesh, w=args.w, h=args.h, tex_u8=textures,
                          material_colors=colors, model=rot_y(12.0))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_ppm(out, image)
    hit = np.isfinite(depth)
    print(f"model: {mesh.n_tris:,} triangles; frame: {args.w}x{args.h}; "
          f"pixels hit: {int(hit.sum()):,}/{args.w * args.h}")
    if hit.any():
        print(f"camera-space depth range: [{depth[hit].min():.4f}, {depth[hit].max():.4f}]")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
