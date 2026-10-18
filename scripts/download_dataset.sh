#!/usr/bin/env bash
# download_dataset.sh - download the Kaggle "Knee Osteoarthritis Dataset with Severity
# Grading" and unzip it into ml-service/model/data/.
#
# !! REMINDER: ml-service/model/data/ (about 8,000 X-ray images) MUST be listed in
# !! .gitignore (a line `data/` is enough). NEVER commit the dataset to Git.
#
# Usage (from anywhere; on Windows use "Git Bash"):
#     bash scripts/download_dataset.sh            # skips if the data is already there
#     bash scripts/download_dataset.sh --force    # download and unzip again
#
# One-time setup:
#     python -m pip install kaggle
#     Kaggle website -> Settings -> API -> create a token, and save kaggle.json to
#     ~/.kaggle/kaggle.json  (Windows: C:\Users\<you>\.kaggle\kaggle.json)
#
# Optional: set KNEESENSE_DATA_DIR to download somewhere other than ml-service/model/data.

set -euo pipefail

DATASET="shashwatwork/knee-osteoarthritis-dataset-with-severity"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${KNEESENSE_DATA_DIR:-$REPO_ROOT/ml-service/model/data}"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

# --- 1. warn if the data folder is not git-ignored ---------------------------------
if ! grep -qE '^/?(ml-service/model/)?data/?[[:space:]]*$' "$REPO_ROOT/.gitignore" 2>/dev/null; then
  echo "WARNING: 'data/' is not in .gitignore. Add it before your next commit:"
  echo "         echo 'data/' >> .gitignore"
fi

# --- 2. is the data already there? -------------------------------------------------
if [[ $FORCE -eq 0 ]] && [[ -d "$DATA_DIR" ]] && \
   [[ -n "$(find "$DATA_DIR" -type d -name train -print -quit 2>/dev/null)" ]]; then
  echo "Dataset already present in $DATA_DIR - nothing to do (use --force to download again)."
  exit 0
fi

# --- 3. check the Kaggle CLI and credentials ---------------------------------------
if ! command -v kaggle >/dev/null 2>&1; then
  echo "ERROR: the 'kaggle' command was not found."
  echo "       Install it with:  python -m pip install kaggle"
  echo "       (on Windows, make sure Python's Scripts folder is on your PATH)"
  exit 1
fi
if [[ ! -f "$HOME/.kaggle/kaggle.json" && ! -f "$HOME/.kaggle/access_token" \
      && -z "${KAGGLE_API_TOKEN:-}" && ( -z "${KAGGLE_USERNAME:-}" || -z "${KAGGLE_KEY:-}" ) ]]; then
  echo "ERROR: no Kaggle credentials found."
  echo "       Create an API token on kaggle.com (Settings -> API) and save kaggle.json to ~/.kaggle/"
  exit 1
fi

# --- 4. download -------------------------------------------------------------------
mkdir -p "$DATA_DIR"
echo "Downloading $DATASET ..."
kaggle datasets download -d "$DATASET" -p "$DATA_DIR"

ZIP_FILE="$(find "$DATA_DIR" -maxdepth 1 -name '*.zip' -print -quit)"
if [[ -z "$ZIP_FILE" ]]; then
  echo "ERROR: no .zip file was downloaded into $DATA_DIR"
  exit 1
fi

# --- 5. unzip (Git Bash has no 'unzip', so fall back to Python) --------------------
echo "Unzipping $(basename "$ZIP_FILE") ..."
if command -v unzip >/dev/null 2>&1; then
  unzip -q -o "$ZIP_FILE" -d "$DATA_DIR"
else
  PY="$(command -v python3 || command -v python || true)"
  [[ -n "$PY" ]] || { echo "ERROR: need 'unzip' or Python to extract the archive"; exit 1; }
  "$PY" -m zipfile -e "$ZIP_FILE" "$DATA_DIR"
fi
rm -f "$ZIP_FILE"

# --- 6. sanity check: image counts per split --------------------------------------
echo
echo "Done. Images found in $DATA_DIR:"
for split in train val test; do
  dir="$(find "$DATA_DIR" -type d -name "$split" -print -quit)"
  if [[ -n "$dir" ]]; then
    count="$(find "$dir" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l)"
    echo "  $split: $count"
  else
    echo "  $split: NOT FOUND (unexpected dataset layout?)"
  fi
done
echo
echo "Reminder: keep data/ out of Git (it must be listed in .gitignore)."
