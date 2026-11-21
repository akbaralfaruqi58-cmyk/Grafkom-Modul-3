"""Copy the prepared Tugu OBJ/MTL and its PNG maps into the static web root.

This keeps `npx serve web` and GitHub Pages deployments self-contained: the
viewer does not request files from outside the published `web/` directory.
"""
from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WEB_ASSETS = ROOT / "web" / "assets"


def main() -> None:
    obj = DATA / "mymodel.obj"
    mtl = DATA / "mymodel.mtl"
    if not obj.is_file() or not mtl.is_file():
        raise FileNotFoundError("Model Tugu belum tersedia. Jalankan: python prepare_tugu.py")

    WEB_ASSETS.mkdir(parents=True, exist_ok=True)
    # Remove stale model/texture files before copying the current prepared set.
    for pattern in ("*.obj", "*.mtl", "*.png"):
        for old in WEB_ASSETS.glob(pattern):
            old.unlink()

    shutil.copy2(obj, WEB_ASSETS / obj.name)
    shutil.copy2(mtl, WEB_ASSETS / mtl.name)

    copied = 0
    for texture in DATA.glob("*.png"):
        shutil.copy2(texture, WEB_ASSETS / texture.name)
        copied += 1

    # Validate every diffuse map named by the MTL is available next to the OBJ.
    missing: list[str] = []
    for line in mtl.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.strip().split()
        if fields and fields[0].lower() == "map_kd" and len(fields) >= 2:
            texture_name = " ".join(fields[1:])
            if not (WEB_ASSETS / texture_name).is_file():
                missing.append(texture_name)
    if missing:
        raise FileNotFoundError("Texture MTL belum tersalin: " + ", ".join(missing))

    print(f"Web assets: {WEB_ASSETS.relative_to(ROOT)}")
    print(f"Copied: mymodel.obj, mymodel.mtl, {copied} PNG texture(s)")
    print("Asset path validation: OK")


if __name__ == "__main__":
    main()
