"""Export the trained PyTorch model to ONNX and verify it matches."""
from __future__ import annotations

from pathlib import Path


def export_model(weights_path: str | Path, onnx_path: str | Path,
                 image_size: int = 224) -> None:
    """Load best_model.pth and export it to best_model.onnx (CPU, fixed input size)."""
    raise NotImplementedError


def verify_export(weights_path: str | Path, onnx_path: str | Path,
                  test_image_path: str | Path, atol: float = 1e-4) -> bool:
    """Run the same test image through the .pth and .onnx models.

    Returns:
        True if outputs match within atol, else False. The export is NOT final
        until this returns True.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
