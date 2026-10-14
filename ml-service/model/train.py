"""EfficientNet-B0 + CORAL ordinal loss training loop for KL grade 0-4."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader


def build_model(num_classes: int = 5, pretrained: bool = True) -> "nn.Module":
    """Create EfficientNet-B0 (ImageNet weights) with a CORAL head.

    The head outputs num_classes - 1 cumulative-link logits (ordinal),
    not a plain softmax over classes.
    """
    raise NotImplementedError


def train_one_epoch(model: "nn.Module", loader: "DataLoader",
                    optimizer: "torch.optim.Optimizer", device: "torch.device",
                    class_weights: "torch.Tensor | None" = None) -> float:
    """Train for one epoch using a weighted CORAL loss.

    Returns:
        Mean training loss over the epoch.
    """
    raise NotImplementedError


def evaluate(model: "nn.Module", loader: "DataLoader", device: "torch.device"
             ) -> dict[str, float]:
    """Evaluate on a loader (used for validation each epoch).

    Returns:
        Dict with at least "loss", "accuracy" and "qwk" (quadratic weighted kappa).
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: parse args, load data, train, checkpoint best val QWK
    to best_model.pth, early-stop, and write a training log."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
