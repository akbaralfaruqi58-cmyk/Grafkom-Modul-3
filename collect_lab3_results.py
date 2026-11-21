"""Compare the exported WebGL PPM with NumPy and merge the browser benchmark."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import math
import numpy as np
from ppm_io import read_ppm, write_ppm
from metrics import psnr, ssim

ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web-frame", default="web/mymodel_three.ppm")
    ap.add_argument("--web-benchmark", default="out/webgl_benchmark.json")
    args = ap.parse_args()

    web_frame = ROOT / args.web_frame
    numpy_frame = ROOT / "out" / "tugu_raster_512.ppm"
    benchmark_path = ROOT / args.web_benchmark
    for required in (web_frame, numpy_frame, benchmark_path):
        if not required.is_file():
            raise FileNotFoundError(f"File belum ada: {required.relative_to(ROOT)}")

    a = read_ppm(numpy_frame)
    b = read_ppm(web_frame)
    if a.shape != b.shape:
        raise ValueError(f"Resolusi berbeda: NumPy {a.shape[1]}x{a.shape[0]} vs WebGL {b.shape[1]}x{b.shape[0]}")
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    diff_vis = np.clip(diff.astype(np.float64) * 6.0, 0, 255).astype(np.uint8)
    diff_path = ROOT / "docs" / "evidence" / "lab3_webgl_numpy_difference_x6.ppm"
    write_ppm(diff_path, diff_vis)

    browser = json.loads(benchmark_path.read_text(encoding="utf-8"))
    p = psnr(a, b)
    s = ssim(a, b)
    result = {
        "webgl_numpy_comparison": {
            "resolution": [a.shape[1], a.shape[0]],
            "psnr_db": "inf" if math.isinf(p) else round(p, 4),
            "ssim_global": round(s, 6),
            "mean_absolute_difference": float(diff.mean()),
            "max_absolute_difference": int(diff.max()),
            "difference_image": str(diff_path.relative_to(ROOT)),
        },
        "webgl_benchmark": browser,
    }
    output = ROOT / "out" / "lab3_browser_results.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = ROOT / "docs" / "Lab3_WebGL_Hasil.md"
    report.write_text(
        "# Hasil WebGL Lab 3\n\n"
        f"- Resolusi: {a.shape[1]} × {a.shape[0]}\n"
        f"- PSNR NumPy vs WebGL: {'∞' if math.isinf(p) else f'{p:.2f}'} dB\n"
        f"- SSIM global: {s:.4f}\n"
        f"- Mean absolute difference: {diff.mean():.3f}\n"
        f"- Maximum absolute difference: {int(diff.max())}\n"
        f"- WebGL mean frame: {browser.get('meanFrameMilliseconds', 'n/a')} ms\n"
        f"- Perkiraan FPS: {browser.get('approximateFps', 'n/a')}\n\n"
        "Residual visual perlu dibaca bersama citra selisih: tepi (raster coverage/anti-aliasing), "
        "filter mipmap, normal, serta perbedaan model shading dapat menimbulkan residual; "
        "pergeseran besar di bagian dalam objek biasanya menandakan kamera, transformasi, atau UV belum cocok.\n",
        encoding="utf-8")
    print(report.read_text(encoding="utf-8"))
    print(f"Saved: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
