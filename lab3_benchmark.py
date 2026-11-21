"""Measure NumPy rasterisation vs pinhole ray tracing for Module 3 Lab 3.

Both renderers use the same Tugu mesh, model yaw, camera, light, materials,
frame dimensions and no-shadow baseline. This measures CPU wall time of the
render() calls only; file loading and image writing are excluded.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

from objio import load_obj
from material_io import load_materials
from transforms import rot_y
import raster3d
import raytrace

ROOT = Path(__file__).resolve().parent


def measure(fn, repeats: int) -> list[float]:
    fn()  # warm-up / first-call overhead excluded
    results = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        results.append((time.perf_counter() - start) * 1000.0)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    if args.size < 16 or args.repeats < 1:
        ap.error("--size must be >=16 and --repeats must be >=1")

    mesh = load_obj(ROOT / "data" / "mymodel.obj")
    textures, colors, _ = load_materials(ROOT / "data" / "mymodel.obj")
    common = dict(w=args.size, h=args.size, tex_u8=textures,
                  material_colors=colors, model=rot_y(12.0))

    raster_times = measure(lambda: raster3d.render(mesh, **common), args.repeats)
    ray_times = measure(lambda: raytrace.render(mesh, **common), args.repeats)
    raster_median = statistics.median(raster_times)
    ray_median = statistics.median(ray_times)
    result = {
        "model": "Monumen Tugu Pahlawan dan Museum 10 November",
        "triangles": mesh.n_tris,
        "resolution": [args.size, args.size],
        "camera": {"eye": [3.4, 2.5, 4.2], "target": [0.0, 0.8, 0.0],
                   "fovy_degrees": 45.0, "near": 0.1, "far": 50.0},
        "model_transform": "Ry(12 degrees)",
        "shadow_mode": "off (baseline comparison)",
        "warmup_runs": 1,
        "measured_repeats": args.repeats,
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "python": sys.version.split()[0],
        },
        "rasterizer_numpy": {
            "samples_ms": [round(x, 4) for x in raster_times],
            "median_ms": round(raster_median, 4),
            "approx_fps": round(1000.0 / raster_median, 2),
        },
        "ray_tracer": {
            "samples_ms": [round(x, 4) for x in ray_times],
            "median_ms": round(ray_median, 4),
            "approx_fps": round(1000.0 / ray_median, 2),
        },
        "ray_to_raster_time_ratio": round(ray_median / max(raster_median, 1e-12), 3),
        "measurement_note": "CPU wall time around the renderer function; excludes model/texture loading and file output. Re-run on the student's laptop for its local measurements.",
    }
    out = ROOT / "out" / "lab3_python_benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    txt = ROOT / "out" / "lab3_python_benchmark.txt"
    txt.write_text(
        "MODULE 3 LAB 3 — PYTHON FRAME-TIME BENCHMARK\n"
        f"Model: {result['model']} ({mesh.n_tris:,} triangles)\n"
        f"Resolution: {args.size}x{args.size}; repeats: {args.repeats}; one warm-up each\n"
        f"Rasterizer median: {raster_median:.4f} ms ({1000/raster_median:.2f} FPS)\n"
        f"Ray tracer median: {ray_median:.4f} ms ({1000/ray_median:.2f} FPS)\n"
        f"Ray/raster time ratio: {ray_median/max(raster_median,1e-12):.3f}x\n"
        f"Environment: {platform.platform()} | {platform.processor() or platform.machine()} | Python {sys.version.split()[0]}\n"
        "Note: CPU function wall time; model and texture loading excluded.\n",
        encoding="utf-8")

    print(txt.read_text(encoding="utf-8"))
    print(f"Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
