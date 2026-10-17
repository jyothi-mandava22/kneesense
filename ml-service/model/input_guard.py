"""Rule-based gate that rejects images that are not plausible knee X-rays.

LIMITATION - read this: this is a cheap HEURISTIC gate, not a trained classifier and not
a certified authenticity or medical-image check. It only catches obviously wrong uploads
(colour photos, selfies, screenshots, blank/over-exposed images, odd shapes). A grayscale
photo, an X-ray of another body part, or a doctored image can still pass. A passing image
is "plausibly a radiograph", never "verified knee X-ray". Thresholds were set from the
full Kaggle knee dataset (8260 images) (some real X-rays are low-contrast or bright) - re-check them (python input_guard.py --folder ...) if you change data.

Signals (all cheap, numpy/OpenCV only - no torch):
    1. size            - both sides at least MIN_SIDE pixels
    2. aspect ratio    - height/width inside ASPECT_RANGE
    3. gray dominance  - R, G, B channels nearly identical (radiographs are grayscale)
    4. histogram shape - real dynamic range, not mostly white/black, smooth wide spread
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

# ---- thresholds (tune with the --folder test below) --------------------------------
MIN_SIDE = 64
ASPECT_RANGE = (0.5, 2.0)            # height / width
MAX_MEAN_CHANNEL_SPREAD = 12.0       # mean(max-min over R,G,B), 0-255 scale
MAX_P95_CHANNEL_SPREAD = 40.0        # 95th percentile of the same spread
MIN_DYNAMIC_RANGE = 30               # p99 - p1 of gray values (dataset min seen: 43)
MAX_BRIGHT_FRACTION = 0.78           # share of pixels >= 240 (dataset max seen: 0.68)
MAX_DARK_FRACTION = 0.60             # share of pixels <= 15  (mostly black)
MIN_ENTROPY_BITS = 2.5               # entropy of a 64-bin gray histogram (dataset min seen: 3.16)
_STATS_SIDE = 256                    # images are shrunk to this before computing stats


def _to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image
    img = image.astype(np.float32)
    if img.max() <= 1.0:
        img = img * 255.0
    return np.clip(img, 0, 255).astype(np.uint8)


def compute_stats(image: np.ndarray) -> dict[str, float]:
    """Numbers the rules look at (also handy for tuning thresholds)."""
    h, w = image.shape[:2]
    img = _to_uint8(image)
    scale = _STATS_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (max(1, round(w * scale)), max(1, round(h * scale))),
                         interpolation=cv2.INTER_AREA)
    if img.ndim == 3 and img.shape[2] >= 3:
        rgb = img[..., :3].astype(np.int16)
        spread = rgb.max(axis=2) - rgb.min(axis=2)
        gray = rgb.mean(axis=2).astype(np.uint8)
    else:
        spread = np.zeros(img.shape[:2], dtype=np.int16)
        gray = img if img.ndim == 2 else img[..., 0]
    hist = np.bincount((gray // 4).ravel(), minlength=64).astype(np.float64)
    p = hist[hist > 0] / hist.sum()
    p1, p99 = np.percentile(gray, [1, 99])
    return {
        "height": h, "width": w, "aspect": h / w,
        "mean_spread": float(spread.mean()), "p95_spread": float(np.percentile(spread, 95)),
        "dynamic_range": float(p99 - p1),
        "bright_fraction": float((gray >= 240).mean()), "dark_fraction": float((gray <= 15).mean()),
        "entropy_bits": float(-(p * np.log2(p)).sum()),
    }


def check_xray(image: np.ndarray) -> tuple[bool, str]:
    """Run all rules. Returns (ok, reason); reason is "" when ok, otherwise a short
    human-readable message suitable for the API's invalid_input_image error."""
    if not isinstance(image, np.ndarray) or image.ndim not in (2, 3) or image.size == 0:
        return False, "Image could not be read as a valid picture."
    if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
        return False, "Unsupported number of colour channels."
    h, w = image.shape[:2]
    if min(h, w) < MIN_SIDE:
        return False, f"Image is too small ({w}x{h}); at least {MIN_SIDE} pixels per side are needed."
    s = compute_stats(image)
    if not ASPECT_RANGE[0] <= s["aspect"] <= ASPECT_RANGE[1]:
        return False, "Image proportions are not typical for a knee X-ray."
    if s["mean_spread"] > MAX_MEAN_CHANNEL_SPREAD or s["p95_spread"] > MAX_P95_CHANNEL_SPREAD:
        return False, "Image is a colour picture; X-rays are grayscale."
    if s["dynamic_range"] < MIN_DYNAMIC_RANGE:
        return False, "Image is too flat or blank to be an X-ray."
    if s["bright_fraction"] > MAX_BRIGHT_FRACTION:
        return False, "Image is mostly white (looks like a document or screenshot)."
    if s["dark_fraction"] > MAX_DARK_FRACTION:
        return False, "Image is mostly black."
    if s["entropy_bits"] < MIN_ENTROPY_BITS:
        return False, "Image brightness distribution is not typical for an X-ray."
    return True, ""


def is_valid_xray(image: np.ndarray) -> bool:
    """True if the image is a plausible radiograph (heuristic - see module docstring).

    Args:
        image: numpy array, (H, W) or (H, W, 3/4), uint8 (or float in 0-1 / 0-255).
    """
    return check_xray(image)[0]


# --------------------------------------------------------------------------- CLI test
def _read(path: Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)


def _main() -> None:
    ap = argparse.ArgumentParser(description="Test the input guard on a folder of images")
    ap.add_argument("--folder", required=True, help="folder with images (searched recursively)")
    ap.add_argument("--n", type=int, default=300, help="max images to sample")
    args = ap.parse_args()

    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    files = sorted(f for f in Path(args.folder).rglob("*") if f.suffix.lower() in exts)
    random.Random(0).shuffle(files)
    files = files[:args.n]
    if not files:
        raise SystemExit(f"No images found under {args.folder}")

    passed, fails, all_stats = 0, [], []
    for f in files:
        img = _read(f)
        ok, why = check_xray(img) if img is not None else (False, "unreadable file")
        passed += ok
        if not ok:
            fails.append((f.name, why))
        if img is not None and min(img.shape[:2]) >= 8:
            all_stats.append(compute_stats(img))
        if len(files) <= 20:
            print(f"{'PASS' if ok else 'FAIL'}  {f.name}" + ("" if ok else f"  -> {why}"))
    print(f"\npassed {passed}/{len(files)} ({100 * passed / len(files):.1f}%)")
    if fails and len(files) > 20:
        print("first failures:", *[f"\n  {n}: {w}" for n, w in fails[:10]])
    if all_stats:
        print("\nstat ranges over these images (min .. max):")
        for k in ("aspect", "mean_spread", "p95_spread", "dynamic_range",
                  "bright_fraction", "dark_fraction", "entropy_bits"):
            vals = [s[k] for s in all_stats]
            print(f"  {k:16s} {min(vals):8.3f} .. {max(vals):8.3f}")


if __name__ == "__main__":
    _main()
