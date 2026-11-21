"""Small hard-shadow helper shared by the NumPy rasterizer and ray tracer.

The current coursework renderer shades one flat normal per OBJ triangle.
For a reproducible low-cost shadow experiment, this module tests the centroid
of each triangle against all other triangles along a directional-light ray.
A triangle is either lit or shadowed as a whole. This is a flat-face hard-shadow
approximation, not a per-fragment shadow map or physically based solution.
"""
from __future__ import annotations

import numpy as np


def triangle_light_visibility(vertices: np.ndarray, faces: np.ndarray,
                              light_dir=(0.4, 0.9, 0.6),
                              bias: float = 1e-4) -> np.ndarray:
    """Return a bool per face: True if its centroid is visible to the light.

    `light_dir` points from the surface toward the directional light. The
    triangle itself is excluded from the occluder set and the origin is offset
    toward the light to avoid self-intersection.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("faces must have shape (N, 3)")
    if len(faces) == 0:
        return np.ones(0, dtype=bool)

    L = np.asarray(light_dir, dtype=np.float64)
    norm = np.linalg.norm(L)
    if norm <= 1e-12:
        raise ValueError("light_dir must be non-zero")
    L /= norm

    triangles = vertices[faces]
    v0 = triangles[:, 0]
    e1 = triangles[:, 1] - v0
    e2 = triangles[:, 2] - v0
    pvec = np.cross(np.broadcast_to(L, e2.shape), e2)
    det = np.einsum("ij,ij->i", e1, pvec)
    valid_det = np.abs(det) > 1e-10
    inv_det = np.zeros_like(det)
    inv_det[valid_det] = 1.0 / det[valid_det]

    visible = np.ones(len(faces), dtype=bool)
    centroids = triangles.mean(axis=1)
    for source_index, centroid in enumerate(centroids):
        origin = centroid + L * bias
        tvec = origin[None, :] - v0
        u = np.einsum("ij,ij->i", tvec, pvec) * inv_det
        qvec = np.cross(tvec, e1)
        v = qvec @ L * inv_det
        t = np.einsum("ij,ij->i", e2, qvec) * inv_det
        hit = (valid_det & (u >= -1e-9) & (v >= -1e-9) &
               (u + v <= 1.0 + 1e-9) & (t > bias * 2.0))
        hit[source_index] = False
        visible[source_index] = not bool(np.any(hit))
    return visible
