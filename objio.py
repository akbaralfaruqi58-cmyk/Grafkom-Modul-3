"""Small Wavefront OBJ loader used by the from-scratch Module 3 renderers.

Supported records: v, vt, f, mtllib and usemtl. Polygons are triangulated
with a fan. Face material IDs and per-corner UV indices are retained so the
NumPy rasteriser and ray tracer can use the same material/texture assignment.

OBJ UVs are bottom-left-origin; image arrays are top-left-origin. With
flip_v=True the conversion is performed exactly once at load time.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np


class Mesh:
    def __init__(self, positions, uvs, faces, face_uvs=None,
                 face_material_ids=None, material_names=None):
        self.positions = np.asarray(positions, dtype=np.float64)
        self.uvs = np.asarray(uvs, dtype=np.float64) if len(uvs) else np.zeros((0, 2))
        self.faces = np.asarray(faces, dtype=np.int64).reshape((-1, 3))
        self.face_uvs = (np.asarray(face_uvs, dtype=np.int64).reshape((-1, 3))
                         if face_uvs is not None and len(face_uvs) else None)
        self.material_names = list(material_names or [])
        if face_material_ids is None:
            self.face_material_ids = np.full(len(self.faces), -1, dtype=np.int32)
        else:
            self.face_material_ids = np.asarray(face_material_ids, dtype=np.int32)
        if self.face_material_ids.shape != (len(self.faces),):
            raise ValueError("face_material_ids must have one item per triangle")

    @property
    def n_tris(self):
        return len(self.faces)

    def triangle_positions(self):
        return self.positions[self.faces]

    def triangle_uvs(self):
        if self.face_uvs is None:
            return np.zeros((len(self.faces), 3, 2), dtype=np.float64)
        return self.uvs[self.face_uvs]

    def face_material(self, face_index: int) -> str | None:
        mid = int(self.face_material_ids[face_index])
        return self.material_names[mid] if 0 <= mid < len(self.material_names) else None


def _parse_index(tok, n_pos, n_uv):
    parts = (tok.split("/") + ["", ""])[:3]
    pi = int(parts[0])
    pi = pi - 1 if pi > 0 else n_pos + pi
    ui = None
    if parts[1] != "":
        u = int(parts[1])
        ui = u - 1 if u > 0 else n_uv + u
    return pi, ui


def load_obj(path, flip_v=True):
    path = Path(path)
    positions, uvs, faces, face_uvs, face_mats = [], [], [], [], []
    material_names, material_lookup = [], {}
    current_material = -1
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("v "):
                positions.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                u, v = (float(x) for x in line.split()[1:3])
                uvs.append([u, 1.0 - v if flip_v else v])
            elif line.startswith("usemtl "):
                name = line.split(maxsplit=1)[1].strip()
                if name not in material_lookup:
                    material_lookup[name] = len(material_names)
                    material_names.append(name)
                current_material = material_lookup[name]
            elif line.startswith("f "):
                toks = line.split()[1:]
                idx = [_parse_index(t, len(positions), len(uvs)) for t in toks]
                for k in range(1, len(idx) - 1):
                    tri = [idx[0], idx[k], idx[k + 1]]
                    faces.append([v[0] for v in tri])
                    # A face without UVs gets a neutral (0,0) corner mapping.
                    face_uvs.append([v[1] if v[1] is not None else 0 for v in tri])
                    face_mats.append(current_material)
    any_uv = any(line.strip().startswith("vt ") for line in path.open("r", encoding="utf-8", errors="replace"))
    return Mesh(positions, uvs, faces, face_uvs if any_uv else None,
                face_mats, material_names)


def save_obj(path, positions, uvs, faces, face_uvs=None):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Module 3 -- deterministic Pusaka3D temple (make_model.py)\n")
        for p in positions:
            fh.write(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n")
        for t in uvs:
            fh.write(f"vt {t[0]:.5f} {t[1]:.5f}\n")
        for i, f in enumerate(faces):
            if face_uvs is not None:
                a, b, c = f
                ua, ub, uc = face_uvs[i]
                fh.write(f"f {a+1}/{ua+1} {b+1}/{ub+1} {c+1}/{uc+1}\n")
            else:
                fh.write(f"f {f[0]+1} {f[1]+1} {f[2]+1}\n")
