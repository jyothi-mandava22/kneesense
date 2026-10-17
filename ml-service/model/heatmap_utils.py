"""Torch-free heatmap rendering shared by inference.py (production) and gradcam.py.

Takes a small CAM map in [0, 1] (e.g. 7x7) plus the X-ray and returns the overlay as a
base64 PNG. Needs only numpy + OpenCV, so the deployed service does not need PyTorch.
"""
from __future__ import annotations

import base64

import cv2
import numpy as np


def to_rgb_float(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Any uint8/float image -> float32 RGB in [0, 1], resized to size = (width, height)."""
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 1) * 255
    image = cv2.resize(image.astype(np.uint8), size, interpolation=cv2.INTER_AREA)
    return image.astype(np.float32) / 255.0


def png_base64(rgb_uint8: np.ndarray) -> str:
    """RGB uint8 image -> PNG bytes -> base64 text."""
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def overlay(base: np.ndarray, cam: np.ndarray, min_heat: float) -> np.ndarray:
    """Blend a JET heatmap onto the X-ray ONLY where cam > min_heat (cam in [0, 1]).
    Everywhere else the plain grayscale X-ray is left untouched (no blue tint)."""
    heat = cv2.cvtColor(cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    heat = heat.astype(np.float32) / 255.0
    alpha = np.clip((cam - min_heat) / (1.0 - min_heat), 0.0, 1.0)[..., None] * 0.65
    return np.uint8(np.clip(base * (1 - alpha) + heat * alpha, 0, 1) * 255)


def render_heatmap(original_rgb: np.ndarray, cam_small: np.ndarray,
                   output_size: int = 448, min_heat: float = 0.25) -> str:
    """CAM map (any size, values 0-1) + X-ray -> base64 PNG of size output_size x output_size.
    The map is upsampled smoothly (cubic) and re-normalised so its peak is 1."""
    size = (output_size, output_size)
    cam = cv2.resize(cam_small.astype(np.float32), size, interpolation=cv2.INTER_CUBIC)
    cam = np.clip(cam, 0.0, None)
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-7)
    return png_base64(overlay(to_rgb_float(original_rgb, size), cam, min_heat))
