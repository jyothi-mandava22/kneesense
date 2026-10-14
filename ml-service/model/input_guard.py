"""Rule-based gate that rejects non-X-ray images before they reach the CNN."""
from __future__ import annotations

import numpy as np


def is_valid_xray(image: np.ndarray) -> bool:
    """Cheap heuristic check that an image looks like a radiograph.

    Checks grayscale dominance, aspect ratio and histogram shape.

    Args:
        image: Image as a numpy array (H, W) or (H, W, 3).

    Returns:
        True if it plausibly is an X-ray, False otherwise (caller then raises
        the invalid_input_image condition).
    """
    raise NotImplementedError
