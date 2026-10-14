"""Leakage check - run BEFORE any training (build-order step 1)."""
from __future__ import annotations

from pathlib import Path


def find_leaked_images(data_dir: str | Path, max_hash_distance: int = 0
                       ) -> list[tuple[str, str, str, str]]:
    """Find duplicate / near-duplicate images across train/val/test folders.

    Computes imagehash.phash for every image and compares hashes across splits.

    Args:
        data_dir: Root folder containing the train/val/test split folders.
        max_hash_distance: Max Hamming distance to count as a near-duplicate
            (0 = exact hash match only).

    Returns:
        List of (path_a, split_a, path_b, split_b) for each cross-split match.
        An empty list means the split is clean (note this in the model card).
    """
    raise NotImplementedError


def resplit_by_patient(data_dir: str | Path, output_dir: str | Path,
                       test_size: float = 0.15, val_size: float = 0.15,
                       seed: int = 42) -> dict[str, list[str]]:
    """Re-split images so no patient appears in more than one split.

    Uses sklearn.model_selection.GroupShuffleSplit grouped by patient ID.

    Returns:
        Dict {"train": [...], "val": [...], "test": [...]} of image paths.
    """
    raise NotImplementedError
