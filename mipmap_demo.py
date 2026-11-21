"""Lab 2 texture/minification experiment using Tugu Pahlawan materials.
Writes before/after renders, an amplified difference image, mip dimensions,
and a simple image-space high-frequency energy measurement.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np

from objio import load_obj
from material_io import load_materials
from transforms import rot_y
from raster3d import render, build_mip_pyramid
from ppm_io import write_ppm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"


def hf_energy(img):
    x = img.astype(np.float64).mean(axis=2) / 255.0
    mask = img.max(axis=2) > 4
    dx_mask = mask[:, 1:] & mask[:, :-1]
    dy_mask = mask[1:, :] & mask[:-1, :]
    dx = np.abs(x[:, 1:] - x[:, :-1])[dx_mask]
    dy = np.abs(x[1:, :] - x[:-1, :])[dy_mask]
    if not len(dx) and not len(dy):
        return 0.0
    parts = [v for v in (dx, dy) if len(v)]
    return float(np.concatenate(parts).mean())


def main():
    OUT.mkdir(exist_ok=True)
    model_path = ROOT / "data" / "mymodel.obj"
    mesh = load_obj(model_path)
    textures, colors, _ = load_materials(model_path)
    mip_info = {}
    for name, tex in textures.items():
        chain = build_mip_pyramid(tex, levels=4)
        mip_info[name] = [list(level.shape[:2][::-1]) for level in chain]
    # Far camera causes texture minification over the small projected model.
    camera = dict(eye=(8.0, 5.8, 10.0), center=(0.0, 0.8, 0.0),
                  near=0.1, far=60.0, fovy=48.0)
    no_mip, _, _ = render(mesh, w=256, h=256, tex_u8=textures,
                          material_colors=colors, model=rot_y(12),
                          mipmap=False, **camera)
    with_mip, _, _ = render(mesh, w=256, h=256, tex_u8=textures,
                            material_colors=colors, model=rot_y(12),
                            mipmap=True, **camera)
    diff = np.clip(np.abs(no_mip.astype(np.int16) - with_mip.astype(np.int16)) * 4,
                   0, 255).astype(np.uint8)
    write_ppm(OUT / "mipmap_without.ppm", no_mip)
    write_ppm(OUT / "mipmap_with.ppm", with_mip)
    write_ppm(OUT / "mipmap_difference_x4.ppm", diff)
    result = {
        "method": "Four-level box-filter mip pyramid; sRGB decoded to linear light before 2x2 averaging.",
        "camera": camera,
        "mip_dimensions_width_height": mip_info,
        "high_frequency_energy_without_mipmap": hf_energy(no_mip),
        "high_frequency_energy_with_mipmap": hf_energy(with_mip),
        "interpretation": "Compare high-frequency energy and the paired renders; energy can also include geometry edges, so inspect the model's textured surfaces rather than treating it as a perceptual metric."
    }
    (OUT / "mipmap_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "mipmap_metrics.txt").write_text(
        "MIPMAP EXPERIMENT\n" + result["method"] + "\n\n" +
        f"High-frequency energy without mipmap: {result['high_frequency_energy_without_mipmap']:.6f}\n" +
        f"High-frequency energy with mipmap   : {result['high_frequency_energy_with_mipmap']:.6f}\n\n" +
        "Four-level dimensions (width x height):\n" +
        "\n".join(f"{k}: {v}" for k, v in mip_info.items()) + "\n",
        encoding="utf-8")
    print("Wrote out/mipmap_without.ppm, out/mipmap_with.ppm, out/mipmap_difference_x4.ppm")
    print(f"High-frequency energy: no mip={result['high_frequency_energy_without_mipmap']:.6f}; "
          f"mip={result['high_frequency_energy_with_mipmap']:.6f}")
    print("Four-level mip dimensions:")
    for name, dims in mip_info.items():
        print(f"  {name}: {dims}")


if __name__ == "__main__":
    main()
