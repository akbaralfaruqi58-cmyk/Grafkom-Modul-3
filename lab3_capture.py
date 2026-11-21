"""Create Lab 3 NumPy reference frames and optional hard-shadow comparison."""
from __future__ import annotations

import json
from pathlib import Path
import time

from objio import load_obj
from material_io import load_materials
from transforms import rot_y
from ppm_io import write_ppm
from metrics import psnr, ssim
import raster3d
import raytrace

ROOT = Path(__file__).resolve().parent


def main() -> None:
    mesh = load_obj(ROOT / "data" / "mymodel.obj")
    textures, colors, _ = load_materials(ROOT / "data" / "mymodel.obj")
    common = dict(tex_u8=textures, material_colors=colors, model=rot_y(12.0))
    out = ROOT / "out"
    out.mkdir(exist_ok=True)

    t0 = time.perf_counter()
    raster512, depth512, filled512 = raster3d.render(mesh, w=512, h=512, **common)
    raster_ms = (time.perf_counter() - t0) * 1000.0
    ref = out / "tugu_raster_512.ppm"
    write_ppm(ref, raster512)

    # A second, low-resolution pair activates the same centroid-based hard
    # shadow experiment in both renderers. It is not used for the baseline
    # WebGL comparison because the NumPy and shadow-map algorithms differ.
    small_size = 96
    shadow_raster, _, _ = raster3d.render(mesh, w=small_size, h=small_size,
                                          hard_shadows=True, **common)
    shadow_ray, _ = raytrace.render(mesh, w=small_size, h=small_size,
                                    hard_shadows=True, **common)
    no_shadow, _, _ = raster3d.render(mesh, w=small_size, h=small_size, **common)
    write_ppm(out / "tugu_hard_shadow_raster_96.ppm", shadow_raster)
    write_ppm(out / "tugu_hard_shadow_ray_96.ppm", shadow_ray)
    write_ppm(out / "tugu_no_shadow_96.ppm", no_shadow)

    import numpy as np
    shadow_diff = np.abs(shadow_raster.astype(np.int16) - no_shadow.astype(np.int16))
    result = {
        "reference_frame": "out/tugu_raster_512.ppm",
        "resolution": [512, 512],
        "model_triangles": mesh.n_tris,
        "rasterizer_512_frame_ms_this_environment": round(raster_ms, 3),
        "visible_fragments": int(filled512),
        "depth_finite_pixels": int(__import__("numpy").isfinite(depth512).sum()),
        "hard_shadow_demo": {
            "resolution": [small_size, small_size],
            "pixels_changed_vs_unshadowed": int(np.any(shadow_diff > 0, axis=2).sum()),
            "mean_absolute_difference_vs_unshadowed": float(shadow_diff.mean()),
            "raster_vs_raytrace_psnr_db": ("inf" if float("inf") == psnr(shadow_raster, shadow_ray) else psnr(shadow_raster, shadow_ray)),
            "raster_vs_raytrace_ssim": ssim(shadow_raster, shadow_ray),
            "note": "The same per-face centroid hard-shadow visibility is used in both NumPy renderers. This is a flat-face approximation, not a per-fragment shadow map.",
        },
    }
    (out / "lab3_capture_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {ref.relative_to(ROOT)} (512x512), raster time {raster_ms:.2f} ms")
    print("Hard-shadow demo: "
          f"PSNR={result['hard_shadow_demo']['raster_vs_raytrace_psnr_db']}, "
          f"SSIM={result['hard_shadow_demo']['raster_vs_raytrace_ssim']:.4f}")


if __name__ == "__main__":
    main()
