"""Lab 2: reproduce, diagnose and fix three deliberately broken scenes.

Run:
  python broken_scene.py --bug inside-out
  python broken_scene.py --bug zfight
  python broken_scene.py --bug stretched
  python broken_scene.py --all

For the building-related cases the actual Lab 1 Tugu Pahlawan OBJ + MTL
textures are used, rather than the optional Pusaka3D teaching fallback.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import numpy as np

from transforms import rot_y, translate, scale
from objio import load_obj, Mesh
from material_io import load_materials
from ppm_io import write_ppm
from metrics import psnr, ssim
import raster3d

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
GOOD_MODEL = rot_y(12.0)
CAMERA = dict(eye=(3.4, 2.5, 4.2), center=(0, 0.8, 0), near=0.1, far=50.0)


def _load():
    path = ROOT / "data" / "mymodel.obj"
    mesh = load_obj(path)
    textures, colors, _ = load_materials(path)
    return mesh, textures, colors


def _write_depth(path: Path, depth: np.ndarray):
    finite = np.isfinite(depth)
    vis = np.ones(depth.shape, dtype=np.float64)
    if finite.any():
        vals = depth[finite]
        if vals.min() < -1.0:  # NDC z from the rasteriser
            vis[finite] = (vals + 1.0) * 0.5
        else:                  # camera-space positive depth
            lo, hi = vals.min(), vals.max()
            vis[finite] = (vals - lo) / max(hi - lo, 1e-12)
    rgb = np.repeat((np.clip(vis, 0, 1) * 255).astype(np.uint8)[..., None], 3, axis=2)
    write_ppm(path, rgb)


def bug_inside_out(mesh, textures, colors, w=192, h=192):
    flipped = Mesh(mesh.positions, mesh.uvs, mesh.faces[:, ::-1].copy(),
                   None if mesh.face_uvs is None else mesh.face_uvs[:, ::-1].copy(),
                   mesh.face_material_ids.copy(), mesh.material_names)
    # View from the opposite side to make the reversed winding visible. The
    # supplied OBJ has mixed exporter winding, so the safe repair for this
    # particular asset is to restore its face order and leave culling off.
    diagnostic_camera = dict(eye=(0.0, 2.0, -6.0), center=(0.0, 0.8, 0.0),
                             near=0.1, far=50.0)
    bad, db, fb = raster3d.render(flipped, w=w, h=h, tex_u8=textures,
                                  material_colors=colors, model=GOOD_MODEL,
                                  cull_back=True, **diagnostic_camera)
    good, dg, fg = raster3d.render(mesh, w=w, h=h, tex_u8=textures,
                                   material_colors=colors, model=GOOD_MODEL,
                                   cull_back=False, **diagnostic_camera)
    common = np.isfinite(db) & np.isfinite(dg)
    avg_depth_delta = float(np.mean(np.abs(db[common] - dg[common]))) if common.any() else None
    evidence = {
        "diagnosis": "Varian scene membalik urutan vertex face lalu mengaktifkan back-face culling. Face yang menghadap kamera dapat diklasifikasikan sebagai back-face dan hilang. OBJ Tugu Pahlawan yang diberikan juga memiliki winding yang tidak sepenuhnya seragam.",
        "fix": "Pulihkan urutan face dari OBJ sumber dan nonaktifkan back-face culling untuk aset ini. Untuk mesh dengan winding konsisten, alternatifnya adalah memperbaiki winding agar seluruh front-face mengikuti konvensi yang sama.",
        "bad_fragments_written": int(fb), "fixed_fragments_written": int(fg),
        "common_visible_pixels": int(common.sum()), "mean_depth_delta_ndc": avg_depth_delta,
        "ssim_bad_vs_fixed": ssim(bad, good), "psnr_bad_vs_fixed": psnr(bad, good),
        "matrix_convention": "back-face culling memakai signed screen-space triangle area; kamera menghadap -Z, screen Y ke bawah.",
        "camera": diagnostic_camera,
        "note": "Culling sengaja dimatikan pada frame perbaikan karena aset OBJ sumber memiliki campuran winding; periksa konsistensi winding sebelum mengaktifkan culling pada model produksi."
    }
    return bad, good, db, dg, evidence


def _zfight_scene():
    """Two almost-coplanar crossing quads at view depth ~9, with different colors."""
    cz = -9.0
    quad_a = np.array([[-3.0, -1.0, 0.0], [3.0, -1.0, 0.0],
                       [3.0, 3.0, 0.0], [-3.0, 3.0, 0.0]]) + [0, 0, cz]
    angle = np.radians(1.2)
    R = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)],
                  [0, np.sin(angle), np.cos(angle)]])
    quad_b = (quad_a - [0, 1.0, cz]) @ R.T + [0, 1.0, cz]
    pos = np.vstack([quad_a, quad_b])
    faces = [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6]]
    return Mesh(pos, np.zeros((0, 2)), faces)


def bug_zfight(w=192, h=192):
    mesh = _zfight_scene()
    common = dict(eye=(0, 1, 6), center=(0, 1, -1), far=200,
                  cull_back=False, tri_colors=[(230, 130, 40)] * 2 + [(60, 120, 210)] * 2,
                  light_dir=(0, 0.2, 1))
    bad, bad_depth, _ = raster3d.render(mesh, w=w, h=h, near=1e-3,
                                         depth_bits=16, **common)
    near_fixed_16, near_fixed_depth, _ = raster3d.render(mesh, w=w, h=h, near=1.0,
                                                          depth_bits=16, **common)
    fixed, fixed_depth, _ = raster3d.render(mesh, w=w, h=h, near=1.0,
                                             depth_bits=None, **common)
    reference = fixed
    bad_error = int(np.sum(np.any(np.abs(bad.astype(np.int16) - reference.astype(np.int16)) > 60, axis=2)))
    near_fixed_error = int(np.sum(np.any(np.abs(near_fixed_16.astype(np.int16) - reference.astype(np.int16)) > 60, axis=2)))
    fixed_error = int(np.sum(np.any(np.abs(fixed.astype(np.int16) - reference.astype(np.int16)) > 60, axis=2)))
    finite = bad_depth[np.isfinite(bad_depth)]
    hist, edges = np.histogram(finite, bins=32, range=(-1.0, 1.0))
    evidence = {
        "diagnosis": "Near plane 0.001 membuat distribusi depth 1/z sangat terkompresi; depth 16-bit tidak cukup memisahkan dua permukaan yang berpotongan dekat.",
        "fix": "Naikkan near plane menjadi 1.0 untuk scene uji ini; pilih near/far yang ketat terhadap volume scene.",
        "bad_near": 1e-3, "fixed_near": 1.0, "depth_bits": 16,
        "pixels_bad_vs_float_reference": bad_error,
        "pixels_near1_16bit_vs_float_reference": near_fixed_error,
        "pixels_fixed_float64_vs_reference": fixed_error,
        "ssim_bad_vs_reference": ssim(bad, reference),
        "ssim_near1_16bit_vs_reference": ssim(near_fixed_16, reference),
        "ssim_fixed_float64_vs_reference": ssim(fixed, reference),
        "depth_histogram_bins": hist.tolist(),
        "depth_histogram_edges": edges.tolist(),
    }
    return bad, fixed, bad_depth, fixed_depth, evidence


def bug_stretched(mesh, textures, colors, w=192, h=192):
    # Correct composition is T @ R @ S (column vectors); broken composition
    # reverses factors and adds anisotropic scale so the error is visible.
    T = translate((0.18, 0.0, -0.08))
    R = rot_y(12.0)
    S = scale((1.0, 1.0, 1.0))
    good_model = T @ R @ S
    bad_model = scale((2.0, 0.55, 1.0)) @ R @ T
    bad, db, fb = raster3d.render(mesh, w=w, h=h, tex_u8=textures,
                                  material_colors=colors, model=bad_model,
                                  **CAMERA)
    good, dg, fg = raster3d.render(mesh, w=w, h=h, tex_u8=textures,
                                   material_colors=colors, model=good_model,
                                   **CAMERA)
    evidence = {
        "diagnosis": "Faktor matriks dikalikan dengan urutan yang salah; skala non-seragam terjadi sebelum/di sisi yang salah dari rotasi dan translasi ikut berubah.",
        "fix": "Dengan vektor kolom gunakan M = T @ R @ S: skala lokal, lalu rotasi, lalu translasi world.",
        "bad_fragments_written": int(fb), "fixed_fragments_written": int(fg),
        "ssim_bad_vs_fixed": ssim(bad, good), "psnr_bad_vs_fixed": psnr(bad, good),
        "bad_model_matrix": bad_model.tolist(), "fixed_model_matrix": good_model.tolist(),
        "camera": CAMERA,
    }
    return bad, good, db, dg, evidence


BUGS = {"inside-out": bug_inside_out, "zfight": bug_zfight, "stretched": bug_stretched}


def run(name, mesh=None, textures=None, colors=None):
    OUT.mkdir(exist_ok=True)
    if name == "zfight":
        bad, fixed, db, df, evidence = bug_zfight()
    elif name == "inside-out":
        bad, fixed, db, df, evidence = bug_inside_out(mesh, textures, colors)
    else:
        bad, fixed, db, df, evidence = bug_stretched(mesh, textures, colors)
    write_ppm(OUT / f"bug_{name}_bad.ppm", bad)
    write_ppm(OUT / f"bug_{name}_fixed.ppm", fixed)
    _write_depth(OUT / f"bug_{name}_depth_bad.ppm", db)
    _write_depth(OUT / f"bug_{name}_depth_fixed.ppm", df)
    if name == "zfight":
        # Supplementary comparison isolates the near-plane change while keeping
        # a 16-bit depth buffer; the main fixed image uses float64 depth.
        zmesh = _zfight_scene()
        near16, _, _ = raster3d.render(
            zmesh, w=192, h=192, near=1.0, far=200.0,
            eye=(0, 1, 6), center=(0, 1, -1), cull_back=False,
            tri_colors=[(230, 130, 40)] * 2 + [(60, 120, 210)] * 2,
            light_dir=(0, 0.2, 1), depth_bits=16)
        write_ppm(OUT / "bug_zfight_near1_16bit.ppm", near16)
        hist = np.asarray(evidence["depth_histogram_bins"], dtype=int)
        edges = np.asarray(evidence["depth_histogram_edges"], dtype=float)
        with (OUT / "bug_zfight_depth_histogram.csv").open("w", encoding="utf-8") as f:
            f.write("bin_left,bin_right,pixel_count\n")
            for i, count in enumerate(hist):
                f.write(f"{edges[i]:.8f},{edges[i+1]:.8f},{count}\n")
    (OUT / f"bug_{name}_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\n== {name} ==")
    print("diagnosis:", evidence["diagnosis"])
    print("fix:", evidence["fix"])
    for key, value in evidence.items():
        if key not in ("diagnosis", "fix", "bad_model_matrix", "fixed_model_matrix", "depth_histogram_bins", "depth_histogram_edges", "camera"):
            print(f"{key}: {value}")
    print(f"saved bad/fixed renders, depth images and out/bug_{name}_evidence.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bug", choices=list(BUGS))
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    mesh, textures, colors = _load()
    names = list(BUGS) if args.all or not args.bug else [args.bug]
    for name in names:
        run(name, mesh, textures, colors)
    print("\nDiagnosis artifacts written to out/.")


if __name__ == "__main__":
    main()
