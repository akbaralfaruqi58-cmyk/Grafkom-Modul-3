"""One-command Lab 2 runner for Windows/macOS/Linux.
Run from the Module3 project root: python run_lab2.py
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STEPS = [
    [PY, "tests.py"],
    [PY, "raster3d.py", "--model", "data/mymodel.obj", "--w", "128", "--h", "128", "--out", "out/tugu_raster.ppm"],
    [PY, "raytrace.py", "--model", "data/mymodel.obj", "--w", "128", "--h", "128", "--out", "out/tugu_raytrace.ppm"],
    [PY, "compare.py", "out/tugu_raster.ppm", "out/tugu_raytrace.ppm", "--diff", "out/tugu_raster_ray_difference_x6.ppm", "--scale", "6"],
    [PY, "broken_scene.py", "--all"],
    [PY, "uv_demo.py"],
    [PY, "mipmap_demo.py"],
]


def main():
    (ROOT / "out").mkdir(exist_ok=True)
    log = ROOT / "out" / "lab2_run_log.txt"
    transcript = []
    for i, cmd in enumerate(STEPS, 1):
        header = f"\n[{i}/{len(STEPS)}] {' '.join(cmd[1:])}\n"
        print(header, end="", flush=True)
        transcript.append(header)
        result = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        print(result.stdout, end="", flush=True)
        transcript.append(result.stdout)
        if result.returncode != 0:
            transcript.append(f"\nFAILED with exit code {result.returncode}\n")
            log.write_text("".join(transcript), encoding="utf-8")
            raise SystemExit(result.returncode)
    transcript.append("\nLAB 2 COMPLETED: all stages returned exit code 0.\n")
    log.write_text("".join(transcript), encoding="utf-8")
    print(f"\nLab 2 complete. Transcript saved to {log.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
