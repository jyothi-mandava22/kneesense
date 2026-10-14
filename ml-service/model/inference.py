"""ONNX inference - the only module other teammates call."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import onnxruntime as ort


def load_model(onnx_path: str | Path) -> "ort.InferenceSession":
    """Load best_model.onnx into a CPU onnxruntime session."""
    raise NotImplementedError


def predict(session: "ort.InferenceSession", image_path: str | Path) -> dict[str, Any]:
    """Run one X-ray through the guard, the CNN and Grad-CAM.

    Returns:
        A dict with EXACTLY these three keys (locked API contract):
            kl_grade (int, 0-4)
            confidence (float, 0.0-1.0): the predicted-class probability P(predicted
                grade) derived from the CORAL cumulative-link output - not raw
                logits, never null.
            heatmap_base64 (str): PNG heatmap encoded as base64.

    Raises:
        An invalid-input-image error (exact type agreed with Lahari) when
        input_guard rejects the image; app.py maps it to
        {"error": "invalid_input_image", "message": "<string>"}.
    """
    raise NotImplementedError
