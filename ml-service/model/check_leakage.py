"""Leakage check - run BEFORE any training.

Hashes every image in train/val/test with a perceptual hash (imagehash.phash) and
reports duplicate / near-duplicate images that appear in DIFFERENT splits. If leakage
is found, resplit_by_patient() builds a clean split grouped by patient ID.

Usage (from the repo root):
    python ml-service/model/check_leakage.py --data_dir ml-service/model/data
    python ml-service/model/check_leakage.py --data_dir ml-service/model/data --resplit
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import cv2
import numpy as np

try:
    from .dataset import IMAGE_EXTS, NUM_CLASSES, find_split_dir, read_gray
except ImportError:  # running as a plain script
    from dataset import IMAGE_EXTS, NUM_CLASSES, find_split_dir, read_gray

SPLITS = ("train", "val", "test")
HERE = Path(__file__).resolve().parent  # the ml-service/model folder: defaults live here, not in the current directory


# --------------------------------------------------------------------------- hashing
def _phash_cv(path: str) -> int:
    """Fallback pHash using only OpenCV/NumPy (used if imagehash can't be imported)."""
    small = cv2.resize(read_gray(path), (32, 32), interpolation=cv2.INTER_AREA)
    low = cv2.dct(small.astype(np.float32))[:8, :8]
    bits = (low > np.median(low)).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def _get_hasher():
    """Return a function path -> 64-bit int hash (imagehash.phash if available)."""
    try:
        import imagehash
        from PIL import Image

        def h(path: str) -> int:
            with Image.open(path) as im:
                return int(str(imagehash.phash(im)), 16)
        return h
    except Exception as e:  # e.g. scipy blocked on this machine
        print(f"[note] imagehash unavailable ({type(e).__name__}); using OpenCV pHash fallback")
        return _phash_cv


def _collect(data_dir: str | Path) -> list[tuple[str, str, int]]:
    """List (path, split, grade) for every image in train/val/test."""
    items = []
    for split in SPLITS:
        split_dir = find_split_dir(data_dir, split)
        for grade in range(NUM_CLASSES):
            class_dir = split_dir / str(grade)
            if class_dir.is_dir():
                for f in sorted(class_dir.iterdir()):
                    if f.suffix.lower() in IMAGE_EXTS:
                        items.append((str(f), split, grade))
    return items


def _compute_hashes(items: list[tuple[str, str, int]]) -> np.ndarray:
    hasher = _get_hasher()
    out = np.zeros(len(items), dtype=np.uint64)
    for i, (path, _, _) in enumerate(items):
        out[i] = np.uint64(hasher(path))
        if (i + 1) % 1000 == 0:
            print(f"  hashed {i + 1}/{len(items)}")
    return out


def _popcount(x: np.ndarray) -> np.ndarray:
    """Number of set bits in each uint64 element."""
    m1, m2 = np.uint64(0x5555555555555555), np.uint64(0x3333333333333333)
    m4, h01 = np.uint64(0x0F0F0F0F0F0F0F0F), np.uint64(0x0101010101010101)
    x = x - ((x >> np.uint64(1)) & m1)
    x = (x & m2) + ((x >> np.uint64(2)) & m2)
    x = (x + (x >> np.uint64(4))) & m4
    return ((x * h01) >> np.uint64(56)).astype(np.int64)


def _cross_split_pairs(items, hashes: np.ndarray, max_dist: int) -> list[tuple[int, int, int]]:
    """All (i, j, hamming_distance) with distance <= max_dist and different splits."""
    splits = np.array([s for _, s, _ in items])
    n, pairs = len(items), []
    for start in range(0, n, 512):
        block = hashes[start:start + 512]
        dist = _popcount(block[:, None] ^ hashes[None, :])
        rows = np.arange(start, start + len(block))[:, None]
        mask = (dist <= max_dist) & (np.arange(n)[None, :] > rows) \
            & (splits[start:start + len(block), None] != splits[None, :])
        for a, b in zip(*np.nonzero(mask)):
            pairs.append((start + int(a), int(b), int(dist[a, b])))
    return pairs


# --------------------------------------------------------------------------- public API
def find_leaked_images(data_dir: str | Path, max_hash_distance: int = 0
                       ) -> list[tuple[str, str, str, str]]:
    """Find duplicate / near-duplicate images across train/val/test.

    Returns a list of (path_a, split_a, path_b, split_b). Empty list = clean split.
    max_hash_distance is the max Hamming distance (0 = identical hash only).
    """
    items = _collect(data_dir)
    hashes = _compute_hashes(items)
    return [(items[i][0], items[i][1], items[j][0], items[j][1])
            for i, j, _ in _cross_split_pairs(items, hashes, max_hash_distance)]


def extract_patient_id(path: str | Path) -> str:
    """Patient ID from the filename: leading run of 5+ digits (e.g. '9003175L.png'
    -> '9003175'); if there is none, the whole file stem is used."""
    stem = Path(path).stem
    m = re.match(r"(\d{5,})", stem)
    return m.group(1) if m else stem


def _resplit(items, hashes, output_dir, test_size, val_size, seed) -> dict[str, list[str]]:
    from sklearn.model_selection import GroupShuffleSplit  # lazy: needs scipy

    n = len(items)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    # Same patient => same group; identical-hash images => same group.
    first_by_pid, first_by_hash = {}, {}
    for i, (path, _, _) in enumerate(items):
        union(i, first_by_pid.setdefault(extract_patient_id(path), i))
        union(i, first_by_hash.setdefault(int(hashes[i]), i))
    groups = np.array([find(i) for i in range(n)])
    print(f"  {n} images -> {len(set(groups.tolist()))} groups")

    idx = np.arange(n)
    trainval, test = next(GroupShuffleSplit(1, test_size=test_size, random_state=seed)
                          .split(idx, groups=groups))
    rel_val = val_size / (1.0 - test_size)
    tr, va = next(GroupShuffleSplit(1, test_size=rel_val, random_state=seed)
                  .split(trainval, groups=groups[trainval]))
    assignment = {"train": trainval[tr], "val": trainval[va], "test": test}

    out = Path(output_dir)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} already exists and is not empty - choose another output_dir")
    result: dict[str, list[str]] = {s: [] for s in SPLITS}
    for split, ids in assignment.items():
        for i in ids:
            src, _, grade = items[i]
            dest_dir = out / split / str(grade)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / Path(src).name
            if dest.exists():
                dest = dest_dir / f"{Path(src).stem}_{i}{Path(src).suffix}"
            shutil.copy2(src, dest)
            result[split].append(str(dest))

    # sanity checks
    for a in SPLITS:
        for b in SPLITS:
            if a < b:
                assert not (set(groups[assignment[a]]) & set(groups[assignment[b]])), "group leaked!"
    for split, ids in assignment.items():
        per_grade = np.bincount([items[i][2] for i in ids], minlength=NUM_CLASSES).tolist()
        print(f"  {split:5s}: {len(ids):5d} images | per grade 0-4: {per_grade}")
    print(f"  re-split written to: {out}")
    return result


def resplit_by_patient(data_dir: str | Path, output_dir: str | Path,
                       test_size: float = 0.15, val_size: float = 0.15,
                       seed: int = 42) -> dict[str, list[str]]:
    """Re-split all images so no patient (and no identical-hash image) is in two splits.

    Uses sklearn GroupShuffleSplit grouped by patient ID from the filename. Images
    are COPIED into output_dir/{train,val,test}/{0..4}/. Returns split -> new paths.
    """
    items = _collect(data_dir)
    return _resplit(items, _compute_hashes(items), output_dir, test_size, val_size, seed)


# --------------------------------------------------------------------------- CLI
def _main() -> None:
    ap = argparse.ArgumentParser(description="Cross-split leakage check")
    ap.add_argument("--data_dir", default=str(HERE / "data"))
    ap.add_argument("--near_dist", type=int, default=4, help="Hamming distance for 'near' duplicates")
    ap.add_argument("--resplit", action="store_true", help="re-split by patient if leakage is found")
    ap.add_argument("--output_dir", default=None, help="default: <data_dir>_resplit")
    ap.add_argument("--report", default=str(HERE / "output" / "leakage_report.txt"))
    args = ap.parse_args()

    items = _collect(args.data_dir)
    print(f"Found {len(items)} images. Hashing (this can take a minute or two)...")
    hashes = _compute_hashes(items)

    pids = {extract_patient_id(p) for p, _, _ in items}
    print(f"Sample filenames: {[Path(p).name for p, _, _ in items[:5]]}")
    print(f"Unique patient IDs from filenames: {len(pids)} (images: {len(items)})")
    pid_splits: dict[str, set[str]] = {}
    for p, sp, _ in items:
        pid_splits.setdefault(extract_patient_id(p), set()).add(sp)
    shared = {k: sorted(v) for k, v in pid_splits.items() if len(v) > 1}
    print(f"Patients appearing in more than one split: {len(shared)}")

    exact = _cross_split_pairs(items, hashes, 0)
    near = _cross_split_pairs(items, hashes, args.near_dist)
    print(f"\nExact-hash duplicates across splits : {len(exact)} pairs")
    print(f"Near duplicates (distance <= {args.near_dist})   : {len(near)} pairs")

    lines = []
    for tag, plist in (("EXACT", exact), (f"NEAR<={args.near_dist}", near[:200])):
        for i, j, d in plist:
            lines.append(f"{tag} d={d}: [{items[i][1]}] {items[i][0]}  <->  [{items[j][1]}] {items[j][0]}")
    lines += [f"PATIENT {k} in splits {v}" for k, v in list(shared.items())[:200]]
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(lines) or "No cross-split duplicates found.", encoding="utf-8")
    print(f"Details saved to {args.report}")

    leaked = bool(exact) or bool(shared)
    print("\nVERDICT:", "LEAKAGE FOUND - fix the split before training." if leaked
          else "No exact duplicates and no patient shared across splits." + (
              " Near-duplicates exist: inspect leakage_report.txt." if near else " Clean."))

    if args.resplit and leaked:
        out = args.output_dir or str(Path(args.data_dir).parent / (Path(args.data_dir).name + "_resplit"))
        print(f"\nRe-splitting by patient into {out} ...")
        _resplit(items, hashes, out, 0.15, 0.15, 42)


if __name__ == "__main__":
    _main()
