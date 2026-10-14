"""Dataset loading, CLAHE preprocessing, augmentation and class-balancing for KneeSense.

Expected on-disk layout (Kaggle "Knee Osteoarthritis Dataset with Severity"):
    <data_dir>/.../train/{0,1,2,3,4}/*.png
    <data_dir>/.../val/{0,1,2,3,4}/*.png
    <data_dir>/.../test/{0,1,2,3,4}/*.png
Folder names 0-4 are the KL grades. The split folders are found automatically, so
<data_dir> can be the unzipped root, however deeply the split folders are nested.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import albumentations as A
import cv2
import numpy as np
import torch
from albumentations.pytorch import ToTensorV2
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

NUM_CLASSES = 5
CLASS_NAMES = ["Normal", "Doubtful", "Mild", "Moderate", "Severe"]  # KL 0..4
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
SPLIT_ALIASES = {"train": {"train"}, "val": {"val", "valid", "validation"}, "test": {"test"}}


# --------------------------------------------------------------------------- helpers
def find_split_dir(data_dir: str | Path, split: str) -> Path:
    """Locate the folder for a split (train/val/test) anywhere under data_dir."""
    if split not in SPLIT_ALIASES:
        raise ValueError(f"split must be one of {list(SPLIT_ALIASES)}, got {split!r}")
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"data_dir does not exist: {root}")
    matches = []
    for dirpath, dirnames, _ in os.walk(root):
        p = Path(dirpath)
        if p.name.lower() in SPLIT_ALIASES[split] and any(
                (p / str(g)).is_dir() for g in range(NUM_CLASSES)):
            matches.append(p)
    if not matches:
        raise FileNotFoundError(
            f"No '{split}' folder with class sub-folders 0-4 found under {root}")
    return min(matches, key=lambda p: len(p.parts))  # shallowest match


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0,
                tile_grid: tuple[int, int] = (8, 8)) -> np.ndarray:
    """CLAHE contrast enhancement on a uint8 grayscale image (H, W)."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    return clahe.apply(gray)


def read_gray(path: str | Path) -> np.ndarray:
    """Read an image as uint8 grayscale. Uses imdecode so Windows paths with
    spaces / non-ASCII characters work."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


def build_transforms(image_size: int = 224, augment: bool = False) -> A.Compose:
    """Albumentations pipeline. Augmentation = small rotation, small zoom,
    brightness/contrast. NO horizontal flip (knee laterality matters)."""
    steps = [A.Resize(image_size, image_size)]
    if augment:
        steps += [
            A.Affine(rotate=(-10, 10), scale=(0.9, 1.1), p=0.7),
            A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.5),
        ]
    steps += [A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD), ToTensorV2()]
    return A.Compose(steps)


def compute_class_weights(labels: list[int], num_classes: int = NUM_CLASSES) -> torch.Tensor:
    """Inverse-frequency weights: weight[c] = N / (num_classes * count[c])."""
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    weights = len(labels) / (num_classes * np.maximum(counts, 1.0))
    return torch.tensor(weights, dtype=torch.float32)


# --------------------------------------------------------------------------- dataset
class KneeDataset(Dataset):
    """Yields (image_tensor [3,H,W] float32, kl_grade int). Pipeline per image:
    read grayscale -> CLAHE -> replicate to 3 channels -> resize/augment/normalize."""

    def __init__(self, split_dir: Path, image_size: int = 224, augment: bool = False):
        self.samples: list[tuple[str, int]] = []
        for grade in range(NUM_CLASSES):
            class_dir = split_dir / str(grade)
            if not class_dir.is_dir():
                continue
            for f in sorted(class_dir.iterdir()):
                if f.suffix.lower() in IMAGE_EXTS:
                    self.samples.append((str(f), grade))
        if not self.samples:
            raise FileNotFoundError(f"No images found under {split_dir}")
        self.targets = [g for _, g in self.samples]
        self.transform = build_transforms(image_size, augment)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        path, grade = self.samples[idx]
        gray = apply_clahe(read_gray(path))
        rgb = np.stack([gray] * 3, axis=-1)
        return self.transform(image=rgb)["image"], grade


# --------------------------------------------------------------------------- public API
def load_dataset(data_dir: str | Path, split: str, image_size: int = 224,
                 augment: bool = False) -> KneeDataset:
    """Build a Dataset for one split ("train", "val" or "test")."""
    return KneeDataset(find_split_dir(data_dir, split), image_size, augment)


def get_dataloaders(data_dir: str | Path, batch_size: int = 32, num_workers: int = 2,
                    image_size: int = 224
                    ) -> tuple[DataLoader, DataLoader, DataLoader, torch.Tensor]:
    """Build train/val/test loaders.

    Class imbalance: the TRAIN loader uses a WeightedRandomSampler (each image is
    drawn with probability proportional to 1 / its class frequency), so batches are
    roughly class-balanced. Val/test are never resampled (honest metrics).
    Returns (train_loader, val_loader, test_loader, class_weights). class_weights is
    for logging/optional loss weighting - don't ALSO weight the loss unless you
    intend to, since the sampler already balances the classes.
    """
    train_ds = load_dataset(data_dir, "train", image_size, augment=True)
    val_ds = load_dataset(data_dir, "val", image_size, augment=False)
    test_ds = load_dataset(data_dir, "test", image_size, augment=False)

    class_weights = compute_class_weights(train_ds.targets)
    sample_weights = class_weights[torch.tensor(train_ds.targets)]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(train_ds), replacement=True)

    common = dict(batch_size=batch_size, num_workers=num_workers,
                  pin_memory=torch.cuda.is_available(),
                  persistent_workers=num_workers > 0)
    train_loader = DataLoader(train_ds, sampler=sampler, **common)
    val_loader = DataLoader(val_ds, shuffle=False, **common)
    test_loader = DataLoader(test_ds, shuffle=False, **common)
    return train_loader, val_loader, test_loader, class_weights


# --------------------------------------------------------------------------- self-test
def _self_test(data_dir: str, preview: bool) -> None:
    print(f"Using data_dir: {data_dir}")
    for split in ("train", "val", "test"):
        ds = load_dataset(data_dir, split)
        counts = np.bincount(ds.targets, minlength=NUM_CLASSES).tolist()
        print(f"{split:5s}: {len(ds):5d} images | per grade 0-4: {counts}")

    train_loader, _, _, weights = get_dataloaders(data_dir, batch_size=32, num_workers=0)
    print("class_weights:", [round(float(w), 3) for w in weights])
    x, y = next(iter(train_loader))
    print("batch image shape:", tuple(x.shape), "dtype:", x.dtype, "| labels shape:", tuple(y.shape))

    drawn = np.zeros(NUM_CLASSES, dtype=int)
    for i, (_, yb) in enumerate(train_loader):
        drawn += np.bincount(yb.numpy(), minlength=NUM_CLASSES)
        if i >= 19:
            break
    print("grades drawn in 20 sampled batches (should be roughly even):", drawn.tolist())

    if preview:
        path, _ = load_dataset(data_dir, "train").samples[0]
        raw = read_gray(path)
        out = np.hstack([cv2.resize(raw, (224, 224)), cv2.resize(apply_clahe(raw), (224, 224))])
        cv2.imwrite("clahe_preview.png", out)
        print("saved clahe_preview.png (left = original, right = CLAHE)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Self-test for dataset.py")
    ap.add_argument("--data_dir", default="data", help="folder where the dataset was unzipped")
    ap.add_argument("--preview", action="store_true", help="save clahe_preview.png")
    args = ap.parse_args()
    _self_test(args.data_dir, args.preview)
