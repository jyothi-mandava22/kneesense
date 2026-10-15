"""EfficientNet-B0 + CORAL ordinal loss training for KL grade 0-4.

CORAL (rank-consistent ordinal regression): instead of a 5-way softmax the model
outputs 4 logits, one per question "is the grade greater than k?" (k = 0..3).
Sigmoid(logit_k) = P(grade > k). Targets are the 4 binary "levels" of the true grade
(grade 3 -> [1, 1, 1, 0]). This teaches the model that grade 4 is "further" from
grade 0 than grade 1 is.

Real training must run on a GPU (Kaggle/Colab). On a laptop use only:  --smoke
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader
from torchvision import models

try:
    from .dataset import NUM_CLASSES, get_dataloaders
except ImportError:  # running as a plain script
    from dataset import NUM_CLASSES, get_dataloaders


# --------------------------------------------------------------------------- model
class CoralHead(nn.Module):
    """One shared weight vector + (num_classes - 1) separate biases -> K-1 logits."""

    def __init__(self, in_features: int, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.fc = nn.Linear(in_features, 1, bias=False)
        self.biases = nn.Parameter(torch.linspace(1.0, -1.0, num_classes - 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x) + self.biases  # (B, 1) + (K-1,) -> (B, K-1)


def build_model(num_classes: int = NUM_CLASSES, pretrained: bool = True) -> nn.Module:
    """EfficientNet-B0 (ImageNet weights) with a CORAL head. Output: (B, num_classes-1) logits."""
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.efficientnet_b0(weights=weights)
    in_features = model.classifier[1].in_features  # 1280
    model.classifier = nn.Sequential(nn.Dropout(p=0.3), CoralHead(in_features, num_classes))
    return model


# --------------------------------------------------------------------------- ordinal helpers
def coral_loss(logits: torch.Tensor, y: torch.Tensor,
               sample_weights: torch.Tensor | None = None) -> torch.Tensor:
    """Binary cross-entropy over the K-1 cumulative levels, summed per sample, averaged."""
    thresholds = torch.arange(logits.shape[1], device=y.device)
    levels = (y.unsqueeze(1) > thresholds.unsqueeze(0)).float()  # (B, K-1)
    per_sample = F.binary_cross_entropy_with_logits(logits, levels, reduction="none").sum(dim=1)
    if sample_weights is not None:
        per_sample = per_sample * sample_weights
    return per_sample.mean()


def logits_to_grades(logits: torch.Tensor) -> torch.Tensor:
    """Predicted grade = number of thresholds with P(grade > k) > 0.5."""
    return (torch.sigmoid(logits.float()) > 0.5).sum(dim=1)


def logits_to_class_probs(logits: torch.Tensor) -> torch.Tensor:
    """Cumulative-link output -> probability of each grade 0..K-1 (rows sum to 1).
    P(grade = k) = P(grade > k-1) - P(grade > k), with P(>-1)=1 and P(>K-1)=0."""
    p = torch.sigmoid(logits.float())
    ones = torch.ones(p.shape[0], 1, device=p.device)
    zeros = torch.zeros(p.shape[0], 1, device=p.device)
    probs = (torch.cat([ones, p], dim=1) - torch.cat([p, zeros], dim=1)).clamp(min=0)
    return probs / probs.sum(dim=1, keepdim=True).clamp(min=1e-8)


def quadratic_weighted_kappa(y_true, y_pred, num_classes: int = NUM_CLASSES) -> float:
    """Quadratic weighted kappa in plain NumPy (1 = perfect, 0 = chance)."""
    y_true, y_pred = np.asarray(y_true, dtype=int), np.asarray(y_pred, dtype=int)
    observed = np.zeros((num_classes, num_classes))
    np.add.at(observed, (y_true, y_pred), 1)
    weights = np.subtract.outer(np.arange(num_classes), np.arange(num_classes)) ** 2
    weights = weights / (num_classes - 1) ** 2
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
    denom = (weights * expected).sum()
    return float(1.0 - (weights * observed).sum() / denom) if denom > 0 else 0.0


# --------------------------------------------------------------------------- loops
def train_one_epoch(model: nn.Module, loader: DataLoader, optimizer: torch.optim.Optimizer,
                    device: torch.device, class_weights: torch.Tensor | None = None,
                    scaler: "torch.amp.GradScaler | None" = None,
                    max_batches: int | None = None) -> float:
    """One pass over the training loader. Returns the mean CORAL loss.
    class_weights (optional) additionally weights the loss per true grade."""
    model.train()
    use_amp = scaler is not None and scaler.is_enabled()
    total, count = 0.0, 0
    for i, (x, y) in enumerate(loader):
        if max_batches is not None and i >= max_batches:
            break
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        w = class_weights.to(device)[y] if class_weights is not None else None
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            logits = model(x)
        loss = coral_loss(logits.float(), y, w)
        if use_amp:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        total += loss.item() * x.size(0)
        count += x.size(0)
    return total / max(count, 1)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device,
             max_batches: int | None = None) -> dict[str, float]:
    """Validation pass. Returns {"loss", "accuracy", "qwk", "mae"} (mae in grades)."""
    model.eval()
    total, count = 0.0, 0
    y_true, y_pred = [], []
    for i, (x, y) in enumerate(loader):
        if max_batches is not None and i >= max_batches:
            break
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        logits = model(x).float()
        total += coral_loss(logits, y).item() * x.size(0)
        count += x.size(0)
        y_true.extend(y.cpu().tolist())
        y_pred.extend(logits_to_grades(logits).cpu().tolist())
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return {
        "loss": total / max(count, 1),
        "accuracy": float((y_true == y_pred).mean()),
        "qwk": quadratic_weighted_kappa(y_true, y_pred),
        "mae": float(np.abs(y_true - y_pred).mean()),
    }


# --------------------------------------------------------------------------- main
def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Train KneeSense CNN (EfficientNet-B0 + CORAL)")
    ap.add_argument("--data_dir", default="data")
    ap.add_argument("--output_dir", default="output", help="best_model.pth + training_log.json go here")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--patience", type=int, default=7, help="early-stop after N epochs without val QWK gain")
    ap.add_argument("--num_workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--weighted_loss", action="store_true",
                    help="also weight the loss by class (off by default: the sampler already balances)")
    ap.add_argument("--no_pretrained", action="store_true", help="skip ImageNet weights download")
    ap.add_argument("--smoke", action="store_true", help="tiny CPU-friendly test run (2 epochs x 3 batches)")
    ap.add_argument("--allow_cpu", action="store_true", help="allow a full run on CPU (not recommended)")
    args = ap.parse_args(argv)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu" and not (args.smoke or args.allow_cpu):
        raise SystemExit("No GPU found. Never train on a laptop - use a Kaggle/Colab GPU "
                         "(or add --smoke for a quick wiring test).")
    max_batches = None
    if args.smoke:
        args.epochs, args.batch_size, args.num_workers, max_batches = 2, 8, 0, 3
    _set_seed(args.seed)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    print(f"device: {device} | epochs: {args.epochs} | batch_size: {args.batch_size} | smoke: {args.smoke}")

    train_loader, val_loader, _, class_weights = get_dataloaders(
        args.data_dir, batch_size=args.batch_size, num_workers=args.num_workers)
    model = build_model(pretrained=not args.no_pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    best_qwk, bad_epochs, log = -1.0, 0, []
    start = time.time()
    for epoch in range(1, args.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, device,
                                     class_weights if args.weighted_loss else None,
                                     scaler, max_batches)
        val = evaluate(model, val_loader, device, max_batches)
        scheduler.step(val["qwk"])
        lr = optimizer.param_groups[0]["lr"]
        saved = val["qwk"] > best_qwk
        if saved:
            best_qwk, bad_epochs = val["qwk"], 0
            torch.save(model.state_dict(), out_dir / "best_model.pth")
        else:
            bad_epochs += 1
        log.append({"epoch": epoch, "train_loss": train_loss, "lr": lr,
                    **{f"val_{k}": v for k, v in val.items()}, "saved": saved})
        print(f"epoch {epoch}/{args.epochs} | train_loss {train_loss:.4f} | val_loss {val['loss']:.4f} | "
              f"val_acc {val['accuracy']:.3f} | val_qwk {val['qwk']:.4f} | val_mae {val['mae']:.3f} | "
              f"lr {lr:.1e}{' | saved best_model.pth' if saved else ''}")
        if bad_epochs >= args.patience:
            print(f"early stopping: no val QWK improvement for {args.patience} epochs")
            break

    (out_dir / "training_log.json").write_text(
        json.dumps({"args": vars(args), "best_val_qwk": best_qwk, "epochs": log}, indent=2))
    print(f"done in {(time.time() - start) / 60:.1f} min | best val QWK {best_qwk:.4f} | saved to {out_dir}")


if __name__ == "__main__":
    main()
