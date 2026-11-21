"""Run reproducible Python-side Lab 3 preparation.

The browser-side steps (interactive OrbitControls, PPM export and WebGL timing)
are intentionally manual and are documented in docs/Lab3_Analisis.md.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(script: str, *args: str) -> None:
    print(f"\n=== {script} {' '.join(args)} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def main() -> None:
    run("make_model.py")
    run("tests.py")
    run("lab3_benchmark.py", "--size", "128", "--repeats", "3")
    run("lab3_capture.py")
    print("\nLab 3 Python-side preparation selesai.")
    print("Lanjutkan viewer browser sesuai docs/Lab3_Analisis.md untuk ekspor PPM dan benchmark WebGL.")


if __name__ == "__main__":
    main()
