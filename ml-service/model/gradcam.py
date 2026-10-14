"""Grad-CAM explainability (pytorch-grad-cam)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from torch import nn


def generate_heatmap(model: "nn.Module", image_tensor, original_image: "np.ndarray",
                     target_grade: int | None = None) -> str:
    """Generate a Grad-CAM heatmap overlay for one image.

    Args:
        model: Trained PyTorch model.
        image_tensor: Preprocessed input tensor of shape (1, 3, H, W).
        original_image: Original RGB image (uint8 array) to overlay on.
        target_grade: Grade to explain; defaults to the predicted grade.

    Returns:
        PNG image encoded as a base64 string (the `heatmap_base64` field).
    """
    raise NotImplementedError
