"""ONNX-only inference - the module the API service (Lahari's app.py) calls.

    from inference import load_model, predict, InvalidInputImageError
    load_model("path/to/best_model.onnx")        # once, at startup
    result = predict(image_bytes_or_path)        # per request
    # -> {"kl_grade": int, "confidence": float, "heatmap_base64": str}

Needs only numpy, OpenCV and onnxruntime (CPU) - NO PyTorch. The heatmap is the
"cam" output of the ONNX model (closed-form Grad-CAM of the last conv layer) drawn by
heatmap_utils.render_heatmap.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    from .heatmap_utils import png_base64, render_heatmap  # noqa: F401
    from .input_guard import check_xray
except ImportError:  # running as a plain script
    from heatmap_utils import png_base64, render_heatmap  # noqa: F401
    from input_guard import check_xray

IMAGE_SIZE = 224
MODEL_PATH_ENV = "KNEESENSE_MODEL_PATH"
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_session = None  # loaded once by load_model()


class InvalidInputImageError(ValueError):
    """Raised when the input is not a plausible knee X-ray (input_guard said no).
    app.py should answer with  err.to_dict()  ==  {"error": "invalid_input_image", "message": "..."}"""

    error = "invalid_input_image"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"error": self.error, "message": self.message}


def load_model(onnx_path: str | Path | None = None):
    """Load best_model.onnx into a CPU-only onnxruntime session (once) and remember it.
    If onnx_path is None the path is read from the KNEESENSE_MODEL_PATH env variable."""
    global _session
    import onnxruntime as ort

    path = onnx_path or os.environ.get(MODEL_PATH_ENV)
    if not path:
        raise ValueError(f"No model path given: pass onnx_path or set {MODEL_PATH_ENV}")
    if not Path(path).is_file():
        raise FileNotFoundError(f"ONNX model not found: {path}")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    outputs = [o.name for o in session.get_outputs()]
    if "logits" not in outputs or "cam" not in outputs:
        raise ValueError(f"Model outputs are {outputs}; expected 'logits' and 'cam' - re-export it")
    _session = session
    return session


def grade_and_confidence(logits: np.ndarray) -> tuple[int, float]:
    """CORAL logits (1, 4) -> (predicted grade, probability of that exact grade).
    P(grade = k) = P(grade > k-1) - P(grade > k) from the cumulative-link output."""
    p = 1.0 / (1.0 + np.exp(-logits[0].astype(np.float64)))  # P(grade > k)
    probs = np.clip(np.concatenate([[1.0], p]) - np.concatenate([p, [0.0]]), 0.0, None)
    probs = probs / max(probs.sum(), 1e-8)
    grade = int((p > 0.5).sum())
    return grade, float(probs[grade])


# --------------------------------------------------------------------------- image handling
def _decode(image: Any) -> np.ndarray:
    """path / bytes / numpy array -> numpy image (uint8 or float). Raises InvalidInputImageError."""
    arr = None
    if isinstance(image, (str, Path)):
        arr = cv2.imdecode(np.fromfile(str(image), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    elif isinstance(image, (bytes, bytearray)):
        arr = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    elif isinstance(image, np.ndarray):
        arr = image
    if arr is None or arr.size == 0:
        raise InvalidInputImageError("Image could not be read as a valid picture.")
    if arr.dtype == np.uint16:  # 16-bit PNG radiographs
        arr = (arr / 257.0).astype(np.uint8)
    return arr


def _as_uint8(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.uint8:
        return arr
    a = arr.astype(np.float32)
    return np.clip(a * 255.0 if a.max() <= 1.0 else a, 0, 255).astype(np.uint8)


def _to_gray(arr: np.ndarray) -> np.ndarray:
    arr = _as_uint8(arr)
    if arr.ndim == 2:
        return arr
    if arr.shape[2] == 1:
        return arr[..., 0]
    return cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)


def _preprocess(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Same pipeline as dataset.py (CLAHE -> 3 channels -> resize -> ImageNet normalize),
    in NumPy. Returns (model input (1, 3, 224, 224) float32, 224x224 RGB image for the overlay)."""
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    resized = cv2.resize(np.stack([enhanced] * 3, axis=-1), (IMAGE_SIZE, IMAGE_SIZE),
                         interpolation=cv2.INTER_LINEAR)
    x = (resized.astype(np.float32) / 255.0 - _MEAN) / _STD
    x = np.ascontiguousarray(x.transpose(2, 0, 1)[None])
    original = np.stack([cv2.resize(gray, (IMAGE_SIZE, IMAGE_SIZE))] * 3, axis=-1)
    return x, original


# --------------------------------------------------------------------------- public API
def predict(image: Any, session=None) -> dict[str, Any]:
    """Grade one knee X-ray.

    Args:
        image: file path, raw bytes (e.g. an upload) or a numpy array.
        session: optional onnxruntime session; defaults to the one from load_model().

    Returns:
        EXACTLY these keys (locked API contract):
            kl_grade (int, 0-4)
            confidence (float, 0-1): probability of the predicted grade from the CORAL output
            heatmap_base64 (str): PNG heatmap overlay, base64 encoded

    Raises:
        InvalidInputImageError: input_guard rejected the image (use err.to_dict()).
    """
    sess = session or _session or load_model()
    arr = _decode(image)
    ok, reason = check_xray(arr)
    if not ok:
        raise InvalidInputImageError(reason)

    x, original = _preprocess(_to_gray(arr))
    logits, cam = sess.run(["logits", "cam"], {"image": x})
    grade, confidence = grade_and_confidence(logits)
    return {"kl_grade": grade, "confidence": confidence,
            "heatmap_base64": render_heatmap(original, cam[0])}


# --------------------------------------------------------------------------- CLI self-test
def _main() -> None:
    import base64
    import time

    ap = argparse.ArgumentParser(description="Self-test for inference.py")
    ap.add_argument("--onnx", default=None, help="path to best_model.onnx (or set KNEESENSE_MODEL_PATH)")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", default="heatmap_from_onnx.png")
    ap.add_argument("--check_preproc", action="store_true",
                    help="compare NumPy preprocessing with dataset.py (needs torch)")
    args = ap.parse_args()

    load_model(args.onnx)
    if args.check_preproc:
        from gradcam import preprocess_image  # torch-based training pipeline
        ref, _ = preprocess_image(args.image)
        mine, _ = _preprocess(_to_gray(_decode(args.image)))
        diff = float(np.abs(ref.numpy() - mine).max())
        print(f"preprocessing max abs diff vs dataset.py: {diff:.2e} ({'OK' if diff < 1e-3 else 'MISMATCH'})")
    try:
        t0 = time.time()
        result = predict(args.image)
        ms = (time.time() - t0) * 1000
    except InvalidInputImageError as e:
        print("REJECTED:", e.to_dict())
        return
    Path(args.out).write_bytes(base64.b64decode(result["heatmap_base64"]))
    print("keys:", sorted(result))
    print(f"kl_grade: {result['kl_grade']} ({type(result['kl_grade']).__name__}) | "
          f"confidence: {result['confidence']:.4f} ({type(result['confidence']).__name__}) | "
          f"heatmap_base64: {len(result['heatmap_base64'])} chars | {ms:.0f} ms")
    print(f"saved {args.out}")


if __name__ == "__main__":
    _main()
