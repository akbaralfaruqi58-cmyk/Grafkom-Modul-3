"""Lab 2 Example E4: render screen-linear UV (incorrect) vs perspective-correct UV.
The floor-like triangle has vertex camera depths 1, 9 and 3. On its near-to-far
edge the midpoint should be u=0.1 with perspective correction, not 0.5.
"""
from pathlib import Path
import numpy as np
from objio import Mesh
from raster3d import render
from ppm_io import write_ppm


def checker_texture(w=256, h=64):
    yy, xx = np.mgrid[0:h, 0:w]
    band = ((xx // 8) % 2)
    row = ((yy // 8) % 2)
    v = np.where(band ^ row, 235, 25).astype(np.uint8)
    # Encode a vivid periodic pattern so spatial stretching is visible.
    return np.dstack((v, np.roll(v, 13, axis=1), 255 - v))


def main():
    out = Path("out")
    out.mkdir(exist_ok=True)
    # Chosen so the left and right bottom vertices project well apart on screen.
    positions = np.array([
        [-0.35, -0.55, -1.0],   # L: near, w=1
        [ 3.00, -4.95, -9.0],   # R: far,  w=9
        [ 0.00,  1.80, -3.0],   # apex
    ], dtype=np.float64)
    uv = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64)
    mesh = Mesh(positions, uv, [[0, 1, 2]], [[0, 1, 2]])
    tex = checker_texture()
    common = dict(w=256, h=192, tex_u8=tex, eye=(0, 0, 0), center=(0, 0, -1),
                  fovy=60.0, near=0.5, far=20.0, light_dir=(0, 0, 1), ambient=1.0)
    naive, _, _ = render(mesh, perspective_correct=False, **common)
    correct, _, _ = render(mesh, perspective_correct=True, **common)
    write_ppm(out / "uv_naive_linear.ppm", naive)
    write_ppm(out / "uv_perspective_correct.ppm", correct)
    diff = np.clip(np.abs(naive.astype(np.int16) - correct.astype(np.int16)) * 2,
                   0, 255).astype(np.uint8)
    write_ppm(out / "uv_linear_vs_correct_difference_x2.ppm", diff)
    # E4 screen midpoint analytic result for depth wL=1, wR=9.
    t = 0.5
    uow_mid = (1 - t) * (0.0 / 1.0) + t * (1.0 / 9.0)
    invw_mid = (1 - t) * (1.0 / 1.0) + t * (1.0 / 9.0)
    u_pc = uow_mid / invw_mid
    u_naive = (1 - t) * 0.0 + t * 1.0
    text = (
        "EXAMPLE E4 - PERSPECTIVE-CORRECT TEXTURE COORDINATES\n"
        f"u naive (screen-linear)       = {u_naive:.6f}\n"
        f"u perspective-correct        = {u_pc:.6f}\n"
        "Method: interpolate u/w and 1/w linearly in screen space, then divide.\n"
        "Outputs: uv_naive_linear.ppm, uv_perspective_correct.ppm, "
        "uv_linear_vs_correct_difference_x2.ppm\n"
    )
    (out / "uv_demo_results.txt").write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
