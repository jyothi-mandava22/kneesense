"""Export the trained PyTorch model to ONNX and verify the two models agree.

    python export_onnx.py --weights output/best_model.pth --onnx output/best_model.onnx --data_dir data

Needs: torch, onnx, onnxruntime.  The .onnx file must NEVER be committed to Git.

ONNX interface
    input  "image"  (batch, 3, 224, 224) float32, ImageNet-normalized (same as dataset.py)
    output "logits" (batch, 4)  CORAL cumulative-link logits
    output "cam"    (batch, 7, 7) heatmap in [0, 1]: Grad-CAM of the last conv layer.
            For this model (global-average-pool -> linear head) Grad-CAM has a closed form:
            relu(sum_c w_c * feature_map_c), min-max normalised. onnxruntime cannot compute
            gradients, so we bake this closed form into the graph instead.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch import nn

try:
    from .gradcam import SeverityTarget, preprocess_image
    from .inference import grade_and_confidence
    from .train import build_model
except ImportError:  # running as a plain script
    from gradcam import SeverityTarget, preprocess_image
    from inference import grade_and_confidence
    from train import build_model


HERE = Path(__file__).resolve().parent  # the ml-service/model folder: defaults live here, not in the current directory


class OnnxWrapper(nn.Module):
    """Wraps the trained model so one forward pass returns (logits, cam)."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        m = self.model
        fmap = m.features(x)                                   # (B, 1280, 7, 7)
        logits = m.classifier(torch.flatten(m.avgpool(fmap), 1))
        w = m.classifier[1].fc.weight.view(1, -1, 1, 1)        # shared CORAL weight vector
        cam = torch.relu((fmap * w).sum(dim=1))                # (B, 7, 7)
        flat = cam.flatten(1)
        lo = flat.min(dim=1, keepdim=True).values.unsqueeze(-1)
        hi = flat.max(dim=1, keepdim=True).values.unsqueeze(-1)
        return logits, (cam - lo) / (hi - lo + 1e-7)


def _load_wrapped_model(weights_path: str | Path) -> OnnxWrapper:
    model = build_model(pretrained=False)
    model.load_state_dict(torch.load(str(weights_path), map_location="cpu"))
    return OnnxWrapper(model.eval()).eval()


def export_model(weights_path: str | Path, onnx_path: str | Path, image_size: int = 224) -> None:
    """Load best_model.pth and write best_model.onnx (dynamic batch size), then run
    the ONNX structural checker."""
    import onnx

    wrapped = _load_wrapped_model(weights_path)
    dummy = torch.randn(1, 3, image_size, image_size)
    Path(onnx_path).parent.mkdir(parents=True, exist_ok=True)
    kwargs = dict(input_names=["image"], output_names=["logits", "cam"],
                  dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}, "cam": {0: "batch"}},
                  opset_version=17, do_constant_folding=True)
    try:  # newer torch: use the classic exporter explicitly
        torch.onnx.export(wrapped, dummy, str(onnx_path), dynamo=False, **kwargs)
    except TypeError:  # older torch has no `dynamo` argument
        torch.onnx.export(wrapped, dummy, str(onnx_path), **kwargs)
    onnx.checker.check_model(onnx.load(str(onnx_path)))
    print(f"exported {onnx_path} ({Path(onnx_path).stat().st_size / 1e6:.1f} MB), structure check OK")


def _library_cam_diff(wrapped: OnnxWrapper, tensor: torch.Tensor, onnx_cam: np.ndarray) -> str:
    """Compare the ONNX cam with pytorch-grad-cam's GradCAM (if that library can be imported)."""
    try:
        import cv2
        from pytorch_grad_cam import GradCAM

        model = wrapped.model
        ref = GradCAM(model=model, target_layers=[model.features[-1]])(
            input_tensor=tensor, targets=[SeverityTarget()])[0]                    # (224, 224) in [0, 1]
        mine = cv2.resize(onnx_cam[0].astype(np.float32), (224, 224), interpolation=cv2.INTER_LINEAR)
        mine = (mine - mine.min()) / (mine.max() - mine.min() + 1e-7)
        return f"max diff vs pytorch-grad-cam GradCAM: {float(np.abs(ref - mine).max()):.2e}"
    except Exception as e:  # library missing or blocked on this machine
        return f"pytorch-grad-cam comparison skipped ({type(e).__name__})"


def verify_export(weights_path: str | Path, onnx_path: str | Path,
                  test_image_path: str | Path, atol: float = 1e-3) -> bool:
    """Run the same image through the .pth and .onnx models.

    Passes only if: predicted grade is identical, confidence differs by <= atol, the raw
    logits and the cam map differ by <= atol, and the ONNX model also accepts a batch of 2
    (dynamic axis). Returns True/False (details printed). Not final until True.
    """
    import onnxruntime as ort

    wrapped = _load_wrapped_model(weights_path)
    tensor, _ = preprocess_image(test_image_path)  # (1, 3, 224, 224), same as training
    with torch.no_grad():
        t_logits, t_cam = (t.numpy() for t in wrapped(tensor))

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    o_logits, o_cam = session.run(None, {"image": tensor.numpy()})
    b_logits, _ = session.run(None, {"image": np.repeat(tensor.numpy(), 2, axis=0)})

    t_grade, t_conf = grade_and_confidence(t_logits)
    o_grade, o_conf = grade_and_confidence(o_logits)
    logit_diff = float(np.abs(t_logits - o_logits).max())
    cam_diff = float(np.abs(t_cam - o_cam).max())
    batch_ok = b_logits.shape == (2, t_logits.shape[1]) and \
        float(np.abs(b_logits[0] - o_logits[0]).max()) <= atol

    ok = (t_grade == o_grade and abs(t_conf - o_conf) <= atol and logit_diff <= atol
          and cam_diff <= atol and batch_ok)
    print(f"{'PASS' if ok else 'FAIL'}  {Path(test_image_path).name}: "
          f"torch grade {t_grade} conf {t_conf:.4f} | onnx grade {o_grade} conf {o_conf:.4f} | "
          f"logit diff {logit_diff:.1e} | cam diff {cam_diff:.1e} | batch-of-2 {'ok' if batch_ok else 'BAD'}")
    print("      " + _library_cam_diff(wrapped, tensor, o_cam))
    return ok


def _main() -> None:
    ap = argparse.ArgumentParser(description="Export best_model.pth to ONNX and verify it")
    ap.add_argument("--weights", default=str(HERE / "output" / "best_model.pth"))
    ap.add_argument("--onnx", default=str(HERE / "output" / "best_model.onnx"))
    ap.add_argument("--data_dir", help="dataset root; verifies one test image per grade 0-4")
    ap.add_argument("--image", nargs="+", help="verify these image files instead")
    ap.add_argument("--verify_only", action="store_true", help="skip export, only verify")
    ap.add_argument("--atol", type=float, default=1e-3)
    args = ap.parse_args()

    if args.image:
        images = args.image
    elif args.data_dir:
        try:
            from .dataset import find_split_dir
        except ImportError:
            from dataset import find_split_dir
        test_dir = find_split_dir(args.data_dir, "test")
        images = [str(sorted((test_dir / str(g)).glob("*.png"))[0]) for g in range(5)]
    else:
        raise SystemExit("Give --data_dir or --image to pick test images.")

    if not args.verify_only:
        export_model(args.weights, args.onnx)
    results = [verify_export(args.weights, args.onnx, img, args.atol) for img in images]
    assert all(results), "ONNX output does not match PyTorch - do NOT use this export"
    print(f"\nALL {len(results)} IMAGES MATCH - export verified")


if __name__ == "__main__":
    _main()
