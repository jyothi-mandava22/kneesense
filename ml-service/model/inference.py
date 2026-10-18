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
import platform
import time
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

HERE = Path(__file__).resolve().parent  # the ml-service/model folder: defaults live here, not in the current directory
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
def predict(image: Any, session=None, timings: dict[str, float] | None = None) -> dict[str, Any]:
    """Grade one knee X-ray.

    Args:
        image: file path, raw bytes (e.g. an upload) or a numpy array.
        session: optional onnxruntime session; defaults to the one from load_model().
        timings: optional dict; if given, timings["onnx_ms"] is set to the time spent in the
            ONNX forward pass (milliseconds). The returned dict is not affected.

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
    t0 = time.perf_counter()
    logits, cam = sess.run(["logits", "cam"], {"image": x})
    if timings is not None:
        timings["onnx_ms"] = (time.perf_counter() - t0) * 1000.0
    grade, confidence = grade_and_confidence(logits)
    return {"kl_grade": grade, "confidence": confidence,
            "heatmap_base64": render_heatmap(original, cam[0])}


# --------------------------------------------------------------------------- latency
def _summary(values: list[float]) -> dict[str, float]:
    return {"avg": float(np.mean(values)), "median": float(np.median(values)),
            "min": float(np.min(values)), "max": float(np.max(values))}


def measure_latency(image_paths, session=None, warmup: int = 3) -> dict[str, Any]:
    """Time predict() on a list of images (CPU).

    Does `warmup` untimed runs first (the first onnxruntime call is slower). For every image
    records (a) the ONNX forward pass alone and (b) the whole predict() call (decode + guard +
    preprocessing + ONNX + heatmap). Images rejected by the guard are counted, not timed.
    """
    sess = session or _session or load_model()
    paths = list(image_paths)
    if not paths:
        raise ValueError("No images given")
    for _ in range(warmup):
        try:
            predict(paths[0], sess)
        except InvalidInputImageError:
            break
    onnx_ms: list[float] = []
    total_ms: list[float] = []
    rejected = 0
    for p in paths:
        timings: dict[str, float] = {}
        t0 = time.perf_counter()
        try:
            predict(p, sess, timings)
        except InvalidInputImageError:
            rejected += 1
            continue
        total_ms.append((time.perf_counter() - t0) * 1000.0)
        onnx_ms.append(timings["onnx_ms"])
    if not total_ms:
        raise RuntimeError("All images were rejected by input_guard - nothing to time")
    return {"n_images": len(total_ms), "rejected": rejected, "warmup_runs": warmup,
            "onnx_ms": _summary(onnx_ms), "predict_ms": _summary(total_ms)}


def log_latency(stats: dict[str, Any], out_path: str | Path = HERE / "output" / "latency.txt") -> str:
    """Write the latency numbers to a short text file (copy it into the README). Returns the text."""
    try:
        import onnxruntime as ort
        ort_version = ort.__version__
    except Exception:
        ort_version = "n/a"
    o, t = stats["onnx_ms"], stats["predict_ms"]
    text = "\n".join([
        "KneeSense inference latency (CPU only, onnxruntime)",
        f"Measured: {time.strftime('%Y-%m-%d')} | {stats['n_images']} test images "
        f"(after {stats['warmup_runs']} untimed warm-up runs; {stats['rejected']} rejected by the guard)",
        f"Machine: {platform.system()} {platform.machine()}, {os.cpu_count()} logical CPUs, "
        f"Python {platform.python_version()}, onnxruntime {ort_version}",
        "",
        f"ONNX forward pass only : avg {o['avg']:.1f} ms | median {o['median']:.1f} | "
        f"min {o['min']:.1f} | max {o['max']:.1f}",
        f"Full predict() call    : avg {t['avg']:.1f} ms | median {t['median']:.1f} | "
        f"min {t['min']:.1f} | max {t['max']:.1f}",
        "  (full call = image decoding + input guard + preprocessing + ONNX + heatmap PNG)",
        "",
        "README line:",
        f"Average CPU latency: {t['avg']:.0f} ms per image end-to-end "
        f"(max {t['max']:.0f} ms); model forward pass alone {o['avg']:.0f} ms. "
        f"Measured on {stats['n_images']} test images, onnxruntime on CPU.",
    ])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return text


# --------------------------------------------------------------------------- CLI self-test
def _main() -> None:
    import base64

    ap = argparse.ArgumentParser(description="Self-test and latency measurement for inference.py")
    ap.add_argument("--onnx", default=None, help="path to best_model.onnx (or set KNEESENSE_MODEL_PATH)")
    ap.add_argument("--image", help="one image to run through predict()")
    ap.add_argument("--out", default=str(HERE / "output" / "heatmap_from_onnx.png"))
    ap.add_argument("--check_preproc", action="store_true",
                    help="compare NumPy preprocessing with dataset.py (needs torch)")
    ap.add_argument("--latency", type=int, default=0, metavar="N",
                    help="time predict() on N random test images (needs --data_dir)")
    ap.add_argument("--data_dir", help="dataset root (for --latency)")
    ap.add_argument("--latency_out", default=str(HERE / "output" / "latency.txt"))
    args = ap.parse_args()
    if not args.image and not args.latency:
        raise SystemExit("Give --image for a single prediction and/or --latency N --data_dir DIR")

    load_model(args.onnx)

    if args.latency:
        if not args.data_dir:
            raise SystemExit("--latency needs --data_dir")
        import random

        try:
            from .dataset import find_split_dir
        except ImportError:
            from dataset import find_split_dir
        files = sorted(f for f in find_split_dir(args.data_dir, "test").rglob("*.png"))
        random.Random(0).shuffle(files)
        print(f"Timing predict() on {min(args.latency, len(files))} test images ...")
        stats = measure_latency(files[:args.latency])
        print(log_latency(stats, args.latency_out))
        print(f"\nsaved {args.latency_out}")

    if args.image:
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
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(base64.b64decode(result["heatmap_base64"]))
        print("keys:", sorted(result))
        print(f"kl_grade: {result['kl_grade']} ({type(result['kl_grade']).__name__}) | "
              f"confidence: {result['confidence']:.4f} ({type(result['confidence']).__name__}) | "
              f"heatmap_base64: {len(result['heatmap_base64'])} chars | {ms:.0f} ms")
        print(f"saved {args.out}")


if __name__ == "__main__":
    _main()
