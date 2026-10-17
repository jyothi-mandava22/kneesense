"""Test-set evaluation with per-class AND ordinal metrics.

    python evaluate.py --model output/best_model.onnx --data_dir data
    python evaluate.py --model output/best_model.pth  --data_dir data   # cross-check: same numbers

Reports: classification_report + confusion_matrix (all 5 KL grades), sensitivity/specificity
for Grade 1 and Grade 2 (minority classes), Quadratic Weighted Kappa, MAE in grades and
adjacent-grade accuracy (within +/-1 grade). Writes everything to a text file.
The model is evaluated on the RAW test images - input_guard is not applied here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from .dataset import CLASS_NAMES, NUM_CLASSES, load_dataset
except ImportError:  # running as a plain script
    from dataset import CLASS_NAMES, NUM_CLASSES, load_dataset


HERE = Path(__file__).resolve().parent  # the ml-service/model folder: defaults live here, not in the current directory


# --------------------------------------------------------------------------- predictions
def _grades_and_confidence(logits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """CORAL logits (N, 4) -> predicted grades (N,) and probability of that grade (N,)."""
    p = 1.0 / (1.0 + np.exp(-logits.astype(np.float64)))                   # P(grade > k)
    n = len(p)
    probs = np.clip(np.hstack([np.ones((n, 1)), p]) - np.hstack([p, np.zeros((n, 1))]), 0.0, None)
    probs /= np.maximum(probs.sum(axis=1, keepdims=True), 1e-8)
    grades = (p > 0.5).sum(axis=1)
    return grades, probs[np.arange(n), grades]


def _logits_onnx(onnx_path: Path, samples: list[tuple[str, int]], batch_size: int = 32) -> np.ndarray:
    import onnxruntime as ort

    try:
        from .inference import _decode, _preprocess, _to_gray
    except ImportError:
        from inference import _decode, _preprocess, _to_gray
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    out = []
    for i in range(0, len(samples), batch_size):
        x = np.concatenate([_preprocess(_to_gray(_decode(p)))[0] for p, _ in samples[i:i + batch_size]])
        out.append(session.run(["logits"], {"image": x})[0])
        print(f"  evaluated {min(i + batch_size, len(samples))}/{len(samples)}", end="\r")
    print()
    return np.concatenate(out)


def _logits_torch(pth_path: Path, data_dir: str | Path) -> np.ndarray:
    import torch
    from torch.utils.data import DataLoader

    try:
        from .train import build_model
    except ImportError:
        from train import build_model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(pretrained=False)
    model.load_state_dict(torch.load(str(pth_path), map_location="cpu"))
    model.to(device).eval()
    loader = DataLoader(load_dataset(data_dir, "test"), batch_size=64, shuffle=False, num_workers=0)
    out = []
    with torch.no_grad():
        for x, _ in loader:
            out.append(model(x.to(device)).float().cpu().numpy())
    return np.concatenate(out)


# --------------------------------------------------------------------------- report
def build_report(y_true: np.ndarray, y_pred: np.ndarray, confidence: np.ndarray,
                 model_name: str) -> tuple[str, dict[str, float]]:
    """Turn labels/predictions into the full text report and a dict of headline metrics."""
    from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix, f1_score

    labels = list(range(NUM_CLASSES))
    names = [f"{g} {CLASS_NAMES[g]}" for g in labels]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    abs_err = np.abs(y_pred - y_true)

    m = {
        "accuracy": float((y_true == y_pred).mean()),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(abs_err.mean()),
        "adjacent_accuracy": float((abs_err <= 1).mean()),
        "mean_confidence": float(confidence.mean()),
    }

    def sens_spec(g: int) -> tuple[float, float]:
        tp = cm[g, g]
        fn = cm[g].sum() - tp
        fp = cm[:, g].sum() - tp
        tn = cm.sum() - tp - fn - fp
        return tp / max(tp + fn, 1), tn / max(tn + fp, 1)

    L = ["KneeSense - test-set evaluation", "=" * 62,
         f"model: {model_name}", f"test images: {len(y_true)}",
         "images per true grade: " + ", ".join(f"{n}: {int((y_true == g).sum())}" for g, n in zip(labels, names)),
         "", "CLASSIFICATION REPORT (per-class precision / recall / F1)", "-" * 62,
         classification_report(y_true, y_pred, labels=labels, target_names=names, digits=3, zero_division=0),
         "CONFUSION MATRIX (rows = true grade, columns = predicted grade)", "-" * 62,
         "true\\pred " + "".join(f"{g:>7d}" for g in labels)]
    L += [f"{g:>9d} " + "".join(f"{v:>7d}" for v in cm[g]) for g in labels]
    L += ["", "SENSITIVITY / SPECIFICITY (one-vs-rest)", "-" * 62]
    for g in labels:
        se, sp = sens_spec(g)
        star = "   <-- minority class" if g in (1, 2) else ""
        L.append(f"Grade {g} ({CLASS_NAMES[g]:>8s}): sensitivity {se:.3f} | specificity {sp:.3f}{star}")
    for g in (1, 2):
        m[f"sensitivity_grade{g}"], m[f"specificity_grade{g}"] = (float(v) for v in sens_spec(g))
    L += ["", "ORDINAL METRICS", "-" * 62,
          f"Quadratic Weighted Kappa (QWK) : {m['qwk']:.4f}   (1 = perfect, 0 = chance)",
          f"Mean Absolute Error (grades)   : {m['mae']:.4f}   (average |predicted - true|)",
          f"Adjacent-grade accuracy (+/-1) : {100 * m['adjacent_accuracy']:.2f}%",
          "", "OVERALL", "-" * 62,
          f"Accuracy                       : {100 * m['accuracy']:.2f}%",
          f"Macro F1                       : {m['macro_f1']:.4f}",
          f"Mean confidence                : {m['mean_confidence']:.4f}   (compare with accuracy: "
          f"{'over' if m['mean_confidence'] > m['accuracy'] else 'under'}-confident)"]
    return "\n".join(L), m


# --------------------------------------------------------------------------- public API
def run_evaluation(model_path: str | Path, data_dir: str | Path,
                   output_dir: str | Path = HERE / "output") -> dict[str, float]:
    """Evaluate a .onnx (production model) or .pth model on the test split, print the
    report and save it to <output_dir>/evaluation_report.txt (+ metrics.json).

    Returns:
        Dict of headline metrics (accuracy, macro_f1, qwk, mae, adjacent_accuracy, ...).
    """
    model_path = Path(model_path)
    samples = load_dataset(data_dir, "test").samples
    y_true = np.array([g for _, g in samples])
    print(f"Evaluating {model_path.name} on {len(samples)} test images ...")
    if model_path.suffix == ".onnx":
        logits = _logits_onnx(model_path, samples)
    elif model_path.suffix == ".pth":
        logits = _logits_torch(model_path, data_dir)
    else:
        raise ValueError("model_path must end in .onnx or .pth")

    y_pred, confidence = _grades_and_confidence(logits)
    text, metrics = build_report(y_true, y_pred, confidence, model_path.name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evaluation_report.txt").write_text(text + "\n", encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("\n" + text + f"\n\nsaved {out / 'evaluation_report.txt'} and metrics.json")
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Evaluate the trained model on the test split")
    ap.add_argument("--model", default=str(HERE / "output" / "best_model.onnx"), help=".onnx or .pth file")
    ap.add_argument("--data_dir", default=str(HERE / "data"))
    ap.add_argument("--output_dir", default=str(HERE / "output"))
    a = ap.parse_args()
    run_evaluation(a.model, a.data_dir, a.output_dir)
