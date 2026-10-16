"""Grad-CAM explainability (pytorch-grad-cam) -> heatmap overlay as a base64 PNG.

Because the CORAL head shares ONE weight vector across all 4 thresholds, the gradient
is the same whichever threshold you pick. So the heatmap answers: "which regions push
the severity score UP?" - one heatmap per image, not one per grade.

Methods (pick with method=...):
    "hirescam" - DEFAULT. HiResCAM on EfficientNet-B0 features[5] (14x14 grid): finer
                 than Grad-CAM and highlights what the model actually used.
    "gradcam"  - fallback. Classic Grad-CAM on the last conv block (coarse 7x7 grid).

Requirements on the model: it must be the torchvision EfficientNet-B0 built by
train.build_model (the layer indices below refer to its .features), in eval mode, with
gradients enabled, and it must output the CORAL logits (the severity score is the
differentiable target).

Test (needs `pip install grad-cam`):
    python gradcam.py --weights best_model.pth --image some_xray.png --out heatmap.png
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn

try:
    from .dataset import apply_clahe, build_transforms, read_gray
except ImportError:  # running as a plain script
    from dataset import apply_clahe, build_transforms, read_gray


class SeverityTarget:
    """Grad-CAM target: the sum of the CORAL logits (= the severity score)."""

    def __call__(self, model_output: torch.Tensor) -> torch.Tensor:
        return model_output.sum()


def _to_rgb_float(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Any uint8/float image -> float32 RGB in [0, 1], resized to size = (width, height)."""
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 1) * 255
    image = cv2.resize(image.astype(np.uint8), size, interpolation=cv2.INTER_AREA)
    return image.astype(np.float32) / 255.0


def _png_base64(rgb_uint8: np.ndarray) -> str:
    """RGB uint8 image -> PNG bytes -> base64 text."""
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def preprocess_image(path: str | Path, image_size: int = 224) -> tuple[torch.Tensor, np.ndarray]:
    """Same preprocessing as dataset.py (CLAHE -> 3 channels -> resize -> normalize).

    Returns (tensor of shape (1, 3, H, W), original RGB uint8 image resized to H x W).
    """
    gray = read_gray(path)
    original = np.stack([cv2.resize(gray, (image_size, image_size))] * 3, axis=-1)
    enhanced = np.stack([apply_clahe(gray)] * 3, axis=-1)
    tensor = build_transforms(image_size, augment=False)(image=enhanced)["image"].unsqueeze(0)
    return tensor, original


def _overlay(base: np.ndarray, cam: np.ndarray, min_heat: float) -> np.ndarray:
    """Blend a JET heatmap onto the X-ray ONLY where cam > min_heat (cam in [0, 1]).
    Everywhere else the plain grayscale X-ray is left untouched (no blue tint)."""
    heat = cv2.cvtColor(cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    heat = heat.astype(np.float32) / 255.0
    alpha = np.clip((cam - min_heat) / (1.0 - min_heat), 0.0, 1.0)[..., None] * 0.65
    return np.uint8(np.clip(base * (1 - alpha) + heat * alpha, 0, 1) * 255)


def generate_heatmap(model: nn.Module, image_tensor: torch.Tensor, original_image: np.ndarray,
                     method: str = "hirescam", output_size: int = 448,
                     min_heat: float = 0.25) -> str:
    """Heatmap overlaid on the X-ray, returned as a base64 PNG string.

    Args:
        model: Trained model from train.build_model (weights loaded).
        image_tensor: Preprocessed input, shape (1, 3, H, W) (or (3, H, W)).
        original_image: The X-ray to draw the heatmap on (uint8, gray or RGB).
        method: "hirescam" (default) | "gradcam" (see module docstring).
        output_size: Side length of the returned square PNG (448 = 2x the model input).
        min_heat: Heat below this fraction of the image's peak is not drawn.

    Returns:
        PNG image encoded as base64 text - the `heatmap_base64` field of the API contract.
    """
    from pytorch_grad_cam import GradCAM, HiResCAM  # lazy: only needed here

    methods = {
        "hirescam": (HiResCAM, [model.features[5]]),  # 14x14 grid, 112 channels
        "gradcam": (GradCAM, [model.features[-1]]),   # 7x7 grid, 1280 channels
    }
    if method not in methods:
        raise ValueError(f"method must be one of {list(methods)}, got {method!r}")
    cam_cls, layers = methods[method]

    model.eval()
    device = next(model.parameters()).device
    x = image_tensor.to(device)
    if x.ndim == 3:
        x = x.unsqueeze(0)

    cam = cam_cls(model=model, target_layers=layers)
    cam_map = cam(input_tensor=x, targets=[SeverityTarget()])[0]  # (H, W) in [0, 1]

    size = (output_size, output_size)
    cam_big = np.clip(cv2.resize(cam_map, size, interpolation=cv2.INTER_CUBIC), 0.0, 1.0)
    base = _to_rgb_float(original_image, size)
    return _png_base64(_overlay(base, cam_big, min_heat))


# --------------------------------------------------------------------------- CLI test
def _main() -> None:
    ap = argparse.ArgumentParser(description="Generate a Grad-CAM heatmap PNG for one X-ray")
    ap.add_argument("--weights", required=True, help="path to best_model.pth")
    ap.add_argument("--image", required=True, help="path to an X-ray image")
    ap.add_argument("--out", default="heatmap.png")
    ap.add_argument("--image_size", type=int, default=224)
    ap.add_argument("--method", default="hirescam", choices=["hirescam", "gradcam"])
    ap.add_argument("--min_heat", type=float, default=0.25)
    args = ap.parse_args()

    try:
        from .train import build_model, logits_to_class_probs, logits_to_grades
    except ImportError:
        from train import build_model, logits_to_class_probs, logits_to_grades

    model = build_model(pretrained=False)
    model.load_state_dict(torch.load(args.weights, map_location="cpu"))
    model.eval()

    tensor, original = preprocess_image(args.image, args.image_size)
    with torch.no_grad():
        logits = model(tensor)
    grade = int(logits_to_grades(logits)[0])
    confidence = float(logits_to_class_probs(logits)[0, grade])

    b64 = generate_heatmap(model, tensor, original, args.method, min_heat=args.min_heat)
    Path(args.out).write_bytes(base64.b64decode(b64))
    print(f"predicted grade: {grade} | confidence: {confidence:.3f}")
    print(f"base64 length: {len(b64)} characters | first 30: {b64[:30]}")
    print(f"saved {args.out}")


if __name__ == "__main__":
    _main()
