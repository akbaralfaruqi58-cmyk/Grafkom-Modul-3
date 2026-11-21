"""Module 3 Lab 1: inspect the supplied Tugu Pahlawan model and trace one vertex.

Run from the Module3 folder:
    python lab1_analysis.py

Writes a reproducible numeric transcript to out/lab1_vertex_trace.txt.
"""
from __future__ import annotations

from pathlib import Path
import json
import numpy as np

from objio import load_obj
from transforms import translate, rot_y, scale, look_at, perspective, viewport

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "data" / "mymodel.obj"
OUTPUT_DIR = ROOT / "out"
OUTPUT_DIR.mkdir(exist_ok=True)


def count_records(path: Path) -> dict[str, int]:
    counts = {"v": 0, "vt": 0, "vn": 0, "f": 0, "o": 0, "usemtl": 0}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        token = line.split(maxsplit=1)[0]
        if token in counts:
            counts[token] += 1
    return counts


def fmt(v: np.ndarray) -> str:
    return np.array2string(np.asarray(v), precision=6, suppress_small=True)


def main() -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model belum dibuat. Jalankan: python prepare_tugu.py")

    mesh = load_obj(MODEL_PATH, flip_v=True)
    raw_counts = count_records(MODEL_PATH)
    bounds_min = mesh.positions.min(axis=0)
    bounds_max = mesh.positions.max(axis=0)
    extent = bounds_max - bounds_min

    # The prepared OBJ is Y-up, centered on X/Z, and grounded at Y=0.
    # Lab 1 model transform: uniform scale, yaw 35 degrees, then translation.
    S = scale((1.0, 1.0, 1.0))
    R = rot_y(35.0)
    T = translate((0.15, 0.0, -0.10))
    M = T @ R @ S

    # Fixed camera/projection values so the same trace can be reproduced.
    eye_position = (3.2, 2.5, 4.0)
    target = (0.0, 0.9, 0.0)
    V = look_at(eye=eye_position, center=target, up=(0.0, 1.0, 0.0))
    near, far, fovy, aspect = 0.1, 50.0, 45.0, 1.0
    P = perspective(fovy, aspect, near, far)
    width = height = 512
    det_model = float(np.linalg.det(M[:3, :3]))
    det_view = float(np.linalg.det(V[:3, :3]))
    if det_model <= 0.0 or det_view <= 0.0:
        raise AssertionError("Transform unexpectedly flips handedness (determinant <= 0).")

    # Select a real vertex at the model's highest Y coordinate (1-based index).
    highest_y = float(bounds_max[1])
    candidates = np.flatnonzero(np.isclose(mesh.positions[:, 1], highest_y, atol=1e-8))
    chosen = candidates[np.argmin(np.linalg.norm(mesh.positions[candidates][:, (0, 2)], axis=1))]
    vertex_id = int(chosen + 1)
    p_obj = mesh.positions[chosen]
    p_h = np.r_[p_obj, 1.0]

    p_world = M @ p_h
    p_view = V @ p_world
    p_clip = P @ p_view
    if abs(p_clip[3]) < 1e-10:
        raise ArithmeticError("Perspective divide tidak valid karena clip.w mendekati nol.")
    p_ndc = p_clip[:3] / p_clip[3]
    p_screen = viewport(p_ndc[None, :], width, height)[0]
    depth01 = (p_ndc[2] + 1.0) * 0.5

    lines: list[str] = []
    add = lines.append
    add("MODUL 3 - LAB 1: INSPEKSI MODEL DAN TELUSURAN SATU VERTEX")
    add("Model: Monumen Tugu Pahlawan dan Museum 10 November")
    add("")
    add("A. DATA MODEL")
    add(f"OBJ: {MODEL_PATH.relative_to(ROOT)}")
    add(f"Jumlah vertex (v) : {raw_counts['v']:,}")
    add(f"Jumlah UV (vt)    : {raw_counts['vt']:,}")
    add(f"Jumlah normal(vn) : {raw_counts['vn']:,}")
    add(f"Jumlah face       : {raw_counts['f']:,} (semua segitiga pada file ini)")
    add(f"Jumlah object     : {raw_counts['o']:,}")
    add(f"Jumlah usemtl     : {raw_counts['usemtl']:,} (pernyataan pergantian material)")
    add(f"Jumlah material berbeda: {len({line.split(maxsplit=1)[1] for line in MODEL_PATH.read_text(encoding='utf-8', errors='replace').splitlines() if line.startswith('usemtl ')})}")
    add(f"Bounding box min  : {fmt(bounds_min)}")
    add(f"Bounding box max  : {fmt(bounds_max)}")
    add(f"Ukuran XYZ        : {fmt(extent)} world units")
    add("UV tersedia pada seluruh face; nilai UV sumber dapat berada di luar 0..1 sehingga material viewer memakai RepeatWrapping.")
    add("")
    add("B. KONVENSI DAN MATRIKS")
    add("Vektor kolom, p' = M @ p; urutan komposisi dibaca dari kanan ke kiri.")
    add("Sumbu right-handed; kamera melihat ke -Z; NDC OpenGL [-1,1].")
    add(f"S =\n{fmt(S)}")
    add(f"Ry(35 deg) =\n{fmt(R)}")
    add(f"T(0.15, 0, -0.10) =\n{fmt(T)}")
    add(f"M = T @ Ry @ S =\n{fmt(M)}")
    add(f"V = look_at(eye={eye_position}, target={target}) =\n{fmt(V)}")
    add(f"P = perspective(fovy={fovy}, aspect={aspect}, near={near}, far={far}) =\n{fmt(P)}")
    add(f"det(M[0:3,0:3]) = {det_model:.6f}; det(V[0:3,0:3]) = {det_view:.6f} (positif = tidak ada refleksi handedness)")
    add("")
    add("C. TELUSURAN-KOLOM M (arah model ke world)")
    for name, axis in [("+X", [1, 0, 0, 0]), ("+Y", [0, 1, 0, 0]), ("+Z", [0, 0, 1, 0]), ("origin", [0, 0, 0, 1])]:
        add(f"M @ {name:6s} = {fmt(M @ np.asarray(axis, dtype=float))}")
    add("")
    add("D. TELUSURAN-KOLOM V (arah world ke view/kamera)")
    for name, axis in [("+X", [1, 0, 0, 0]), ("+Y", [0, 1, 0, 0]), ("+Z", [0, 0, 1, 0]), ("origin", [0, 0, 0, 1])]:
        add(f"V @ {name:6s} = {fmt(V @ np.asarray(axis, dtype=float))}")
    add("")
    add("E. KOLOM GABUNGAN V @ M (arah sumbu model langsung ke view)")
    VM = V @ M
    for name, axis in [("+X", [1, 0, 0, 0]), ("+Y", [0, 1, 0, 0]), ("+Z", [0, 0, 1, 0]), ("origin", [0, 0, 0, 1])]:
        add(f"V @ M @ {name:6s} = {fmt(VM @ np.asarray(axis, dtype=float))}")
    add("")
    add("F. TELUSURAN SATU VERTEX DARI MODEL ASLI")
    add(f"Indeks vertex OBJ (1-based): {vertex_id}")
    add(f"Object p                  : {fmt(p_h)}")
    add(f"World  M @ p               : {fmt(p_world)}")
    add(f"View   V @ (M @ p)         : {fmt(p_view)}")
    add(f"Clip   P @ view            : {fmt(p_clip)}")
    add(f"NDC    clip.xyz / clip.w   : {fmt(p_ndc)}")
    add(f"Screen ({width}x{height})       : {fmt(p_screen)}")
    add(f"Depth buffer [0,1]         : {depth01:.6f}")
    add("")
    add("G. PERHITUNGAN TANGAN UNTUK DUA LANGKAH PERTAMA")
    add("Ambil p = (x,y,z,1) dari baris Object di atas.")
    add("M = [[cos35, 0, sin35, 0.15], [0,1,0,0], [-sin35,0,cos35,-0.10], [0,0,0,1]].")
    add(f"x_world = cos35*x + sin35*z + 0.15 = {p_world[0]:.6f}")
    add(f"y_world = y = {p_world[1]:.6f}")
    add(f"z_world = -sin35*x + cos35*z - 0.10 = {p_world[2]:.6f}")
    add("Langkah view dihitung dengan mengalikan V dengan koordinat world; hasilnya cocok dengan baris View di atas.")
    add("")
    add("H. KETERANGAN PIPELINE")
    add("Object: koordinat asli vertex pada mymodel.obj.")
    add("World: vertex sesudah model matrix M (skala, yaw, translasi).");
    add("View: koordinat world dinyatakan relatif terhadap kamera melalui V.")
    add("Clip: koordinat homogen sesudah projection matrix P; clipping dilakukan sebelum divide.")
    add("NDC: clip dibagi clip.w, menghasilkan koordinat dalam rentang clip yang telah diproyeksikan.")
    add("Screen: NDC dipetakan ke pixel; sumbu Y dibalik karena koordinat layar bertambah ke bawah.")

    transcript = "\n".join(lines) + "\n"
    output_txt = OUTPUT_DIR / "lab1_vertex_trace.txt"
    output_txt.write_text(transcript, encoding="utf-8")

    info = {
        "model": "Monumen Tugu Pahlawan dan Museum 10 November",
        "obj": "data/mymodel.obj",
        "counts": raw_counts,
        "unique_materials": len({line.split(maxsplit=1)[1] for line in MODEL_PATH.read_text(encoding='utf-8', errors='replace').splitlines() if line.startswith('usemtl ')}),
        "bounds_min": bounds_min.tolist(),
        "bounds_max": bounds_max.tolist(),
        "extent": extent.tolist(),
        "vertex_index_1_based": vertex_id,
        "object": p_h.tolist(),
        "world": p_world.tolist(),
        "view": p_view.tolist(),
        "clip": p_clip.tolist(),
        "ndc": p_ndc.tolist(),
        "screen": p_screen.tolist(),
        "depth_01": float(depth01),
        "model_matrix": M.tolist(),
        "view_matrix": V.tolist(),
        "projection_matrix": P.tolist(),
        "det_model_3x3": det_model,
        "det_view_3x3": det_view,
        "camera": {"eye": list(eye_position), "target": list(target), "near": near, "far": far, "fovy_deg": fovy, "aspect": aspect},
    }
    (OUTPUT_DIR / "lab1_model_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(transcript, end="")
    print(f"\nSaved: {output_txt.relative_to(ROOT)}")
    print(f"Saved: {(OUTPUT_DIR / 'lab1_model_info.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
