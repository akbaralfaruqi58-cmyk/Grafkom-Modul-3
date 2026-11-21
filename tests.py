"""Run the Module 3 from-scratch tests. Exit status 0 means all checks pass.
Covers worked examples E1-E5, the Tugu Pahlawan OBJ/MTL asset, clipping,
texture mipmaps, deterministic raster output, and raster-vs-ray parity.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
import numpy as np

from transforms import (translate, rot_y, look_at, perspective, project,
                        viewport, perspective_divide_2d)

ROOT = Path(__file__).resolve().parent


def check(name, fn):
    try:
        fn(); print("OK   " + name); return True
    except Exception:
        print("FAIL " + name); traceback.print_exc(); return False


def t_e1_running_point():
    p = np.array([2.0, 3.0, 4.0, 1.0])
    world = rot_y(90) @ translate((1, 0, -1)) @ p
    assert np.allclose(world, [3, 3, -3, 1], atol=1e-9), world
    assert np.allclose(perspective_divide_2d(world[:3], d=2), [2, 2], atol=1e-9)
    other = translate((1, 0, -1)) @ rot_y(90) @ p
    assert not np.allclose(other, world)
    assert np.allclose(other, [5, 3, -3, 1], atol=1e-9), other


def t_e2_duality():
    p = np.array([5.0, 0.0, 0.0, 1.0])
    V = look_at(eye=(1, 0, 0), center=(1, 0, -1))
    M = translate((-1, 0, 0))
    assert np.allclose(V @ p, M @ p, atol=1e-9)


def t_e3_perspective_near_far():
    n, f = 1.0, 9.0
    P = perspective(60, 1.0, n, f)
    for z, want in [(-n, -1.0), (-f, +1.0), (-3.0, 0.5)]:
        clip = P @ np.array([0, 0, z, 1.0])
        assert abs(clip[2] / clip[3] - want) < 1e-9


def t_e4_perspective_correct_u():
    u_over_w = np.interp(50, [0, 100], [0 / 1, 1 / 9])
    inv_w = np.interp(50, [0, 100], [1 / 1, 1 / 9])
    u_pc = u_over_w / inv_w
    assert abs(u_pc - 0.1) < 1e-12
    assert abs(np.interp(50, [0, 100], [0, 1]) - 0.5) < 1e-12


def t_e5_barycentric_depth():
    z = 0.25 * 0.20 + 0.25 * 0.50 + 0.50 * 0.90
    assert abs(z - 0.625) < 1e-12


def t_projection_pipeline_shapes():
    verts = np.array([[0, 0, -2.0], [1, 0, -2.0], [0, 1, -3.0]])
    P = perspective(50, 4 / 3, 0.1, 100)
    V = look_at((0, 0, 3), (0, 0, 0))
    clip, ndc = project(P, V, np.eye(4), verts)
    assert clip.shape == (3, 4) and ndc.shape == (3, 3)
    assert viewport(ndc, 640, 480).shape == (3, 3)


def t_one_triangle_render():
    from objio import Mesh
    import raster3d
    pos = np.array([[-0.6, -0.6, -2.0], [0.6, -0.6, -2.0], [0.0, 0.6, -2.0]])
    mesh = Mesh(pos, np.zeros((0, 2)), [[0, 1, 2]])
    col, dep, filled = raster3d.render(mesh, w=48, h=48, near=1.0, far=50.0,
                                       eye=(0, 0, 0), center=(0, 0, -1),
                                       light_dir=(0, 0, 1))
    assert 200 < filled < 48 * 48, filled
    assert np.isfinite(dep).sum() == filled
    z = dep[np.isfinite(dep)]
    assert z.max() - z.min() < 1e-6
    assert col.shape == (48, 48, 3)


def t_near_plane_clipping():
    from raster3d import clip_triangle_near
    # One vertex outside near plane (z+w<0), two inside; clipping yields a quad
    # and therefore two triangles after fan triangulation.
    vc = np.array([[0.0, 0.0, -2.0, 1.0], [0.8, -0.5, 0.0, 1.0], [-0.8, 0.5, 0.0, 1.0]])
    attrs = np.array([[0, 0], [1, 0], [0, 1]], dtype=float)
    tris = clip_triangle_near(vc, attrs)
    assert len(tris) == 2, len(tris)
    for cv, ca in tris:
        assert cv.shape == (3, 4) and ca.shape == (3, 2)
        assert np.all(cv[:, 2] + cv[:, 3] >= -1e-9)


def t_lab1_tugu_model_and_materials():
    from objio import load_obj
    from material_io import load_materials
    path = ROOT / "data" / "mymodel.obj"
    assert path.exists(), "data/mymodel.obj missing; run python prepare_tugu.py"
    mesh = load_obj(path, flip_v=True)
    assert mesh.n_tris >= 200, mesh.n_tris
    assert mesh.uvs.shape[0] > 0 and mesh.face_uvs is not None
    assert mesh.face_uvs.shape == (mesh.n_tris, 3)
    assert len(mesh.material_names) >= 10, mesh.material_names
    extent = mesh.positions.max(axis=0) - mesh.positions.min(axis=0)
    assert abs(extent[1] - 2.0) < 1e-5, extent
    textures, colors, meta = load_materials(path)
    assert len(textures) >= 8, sorted(textures)
    assert len(colors) >= 10
    assert meta["mtl_path"] is not None


def t_mipmap_four_levels_gamma_correct():
    from raster3d import build_mip_pyramid
    tex = np.full((8, 8, 3), 128, dtype=np.uint8)
    chain = build_mip_pyramid(tex, levels=4)
    assert [x.shape[:2] for x in chain] == [(8, 8), (4, 4), (2, 2), (1, 1)]
    for level in chain:
        assert np.allclose(level, chain[-1][0, 0], atol=1e-12)


def t_tugu_reference_frame():
    """Deterministic Tugu frame compared with the frozen project reference."""
    from objio import load_obj
    from material_io import load_materials
    import raster3d
    from ppm_io import read_ppm, write_ppm
    from metrics import psnr
    path = ROOT / "data" / "mymodel.obj"
    mesh = load_obj(path)
    textures, colors, _ = load_materials(path)
    image, depth, filled = raster3d.render(mesh, w=128, h=128,
                                           tex_u8=textures, material_colors=colors,
                                           model=rot_y(12.0))
    ref_path = ROOT / "ref" / "tugu_raster_reference.ppm"
    if not ref_path.exists():
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        write_ppm(ref_path, image)
        print("     generated ref/tugu_raster_reference.ppm; commit this frozen reference")
    ref = read_ppm(ref_path)
    p = psnr(image, ref)
    assert p == float("inf") or p > 60.0, f"Tugu reference PSNR={p:.2f} dB"
    assert filled > 0 and np.isfinite(depth).any()


def t_tugu_raster_raytrace_parity():
    from objio import load_obj
    from material_io import load_materials
    import raster3d, raytrace
    from metrics import psnr, ssim
    path = ROOT / "data" / "mymodel.obj"
    mesh = load_obj(path)
    textures, colors, _ = load_materials(path)
    kwargs = dict(w=96, h=96, tex_u8=textures, material_colors=colors, model=rot_y(12.0))
    raster, depth, _ = raster3d.render(mesh, **kwargs)
    ray, ray_depth = raytrace.render(mesh, **kwargs)
    p = psnr(raster, ray)
    assert p == float("inf") or p >= 60.0, f"raster/ray PSNR={p:.2f} dB"
    assert ssim(raster, ray) > 0.999
    assert np.isfinite(depth).any() and np.isfinite(ray_depth).any()


def main():
    checks = [
        ("E1 running point and transform order", t_e1_running_point),
        ("E2 camera/model duality", t_e2_duality),
        ("E3 perspective near/far mapping", t_e3_perspective_near_far),
        ("E4 perspective-correct UV (0.1 vs naive 0.5)", t_e4_perspective_correct_u),
        ("E5 barycentric depth interpolation", t_e5_barycentric_depth),
        ("projection pipeline and viewport shapes", t_projection_pipeline_shapes),
        ("one-triangle rasterisation and z-buffer", t_one_triangle_render),
        ("near-plane homogeneous clipping", t_near_plane_clipping),
        ("Tugu Pahlawan OBJ, UV, MTL and texture assets", t_lab1_tugu_model_and_materials),
        ("four-level gamma-correct mipmap pyramid", t_mipmap_four_levels_gamma_correct),
        ("Tugu raster matches frozen reference (PSNR > 60 dB)", t_tugu_reference_frame),
        ("Tugu rasteriser vs independent ray tracer (PSNR >= 60 dB)", t_tugu_raster_raytrace_parity),
    ]
    ok = all(check(name, fn) for name, fn in checks)
    print("\n" + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
