"""Test-set evaluation with ordinal metrics."""
from __future__ import annotations

from pathlib import Path


def run_evaluation(model_path: str | Path, data_dir: str | Path,
                   output_dir: str | Path = "reports") -> dict[str, float]:
    """Evaluate on the test set and report:
    classification_report + confusion_matrix, Grade 1 and 2 sensitivity/
    specificity, Quadratic Weighted Kappa, MAE in grades, and adjacent-grade
    accuracy (within +/-1 grade).

    Returns:
        Dict of the headline metrics (also saved under output_dir).
    """
    raise NotImplementedError
