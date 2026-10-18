---
library_name: onnx
pipeline_tag: image-classification
tags:
  - knee-osteoarthritis
  - kellgren-lawrence
  - ordinal-classification
  - medical-imaging
  - grad-cam
---

# KneeSense CNN: knee osteoarthritis severity (KL grade 0-4)

EfficientNet-B0 with a CORAL ordinal head that grades a knee X-ray on the Kellgren-Lawrence (KL)
scale and also returns a Grad-CAM heatmap. Built for the KneeSense student project (AI/DL part).

**Not a medical device. Not clinically validated.** For education and research demos only; do not
use it to make or support clinical decisions.

## Files

- `best_model.onnx`: the model (CPU inference with `onnxruntime`)
- `model_card.md`: this card

## Class labels

| KL grade | Label |
|---|---|
| 0 | Normal |
| 1 | Doubtful |
| 2 | Mild |
| 3 | Moderate |
| 4 | Severe |

## Input / output (ONNX interface)

- **Input** `image`: float32, shape `(batch, 3, 224, 224)`, preprocessed as below.
- **Output** `logits`: float32 `(batch, 4)`, CORAL cumulative-link logits. `sigmoid(logit_k) = P(grade > k)`.
- **Output** `cam`: float32 `(batch, 7, 7)`, values in [0, 1]. Grad-CAM of the last convolutional layer
  (for this architecture it has a closed form, so it is computed inside the graph; ONNX Runtime cannot
  compute gradients).

**Predicted grade** = number of `P(grade > k)` values above 0.5.
**Confidence** = `P(predicted grade)`, where `P(grade = k) = P(grade > k-1) - P(grade > k)`
(not raw logits). Because the grade is picked by thresholding (the median of the distribution), the
confidence can be low even for a sensible prediction; it is not calibrated and is not the probability
that the prediction is correct.

### Preprocessing (done for you by `inference.py`)

1. Read as 8-bit grayscale
2. CLAHE contrast enhancement (OpenCV, clip limit 2.0, 8x8 tiles)
3. Copy to 3 channels, resize to 224x224 (bilinear)
4. Scale to [0, 1], normalise with ImageNet mean `(0.485, 0.456, 0.406)` and std `(0.229, 0.224, 0.225)`

## Training data

Kaggle "Knee Osteoarthritis Dataset with Severity Grading", pre-split into train / val / test folders
(224x224 knee X-rays; roughly two images per patient ID in the filenames).

| Split | Images | Grade 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|---|
| Train | 5778 | 2286 | 1046 | 1516 | 757 | 173 |
| Val | 826 | 328 | 153 | 212 | 106 | 27 |
| Test | 1656 | 639 | 296 | 447 | 223 | 51 |

**Leakage check:** a perceptual-hash (pHash) + patient-ID check was run on the original split
**before training**: 0 exact duplicates and 0 patients shared across train/val/test. (222 near-duplicate
hash pairs at Hamming distance <= 4 were found; they were different patients, mostly with different
grades, and were treated as coincidental similarity.)

## Training

- Backbone: torchvision EfficientNet-B0, ImageNet-pretrained, fully fine-tuned; classifier replaced by
  dropout (0.3) + CORAL head (one shared weight vector, 4 biases)
- Loss: CORAL (binary cross-entropy over the 4 cumulative levels)
- Class imbalance (Grade 0 dominates): weighted random sampler on the training set
- Augmentation: rotation +/-10 degrees, zoom 0.9-1.1x, brightness/contrast +/-15%, **no horizontal flips**
  (laterality matters)
- Optimiser: AdamW (lr 3e-4, weight decay 1e-4), batch size 32, ReduceLROnPlateau on validation QWK,
  mixed precision on GPU, early stopping (patience 7), seed 42
- Checkpoint: best **validation quadratic weighted kappa** (0.8129). Trained on a Kaggle GPU.

## Results (test set, 1656 images)

| Metric | Value |
|---|---|
| Accuracy | 63.0% |
| Macro F1 | 0.587 |
| Quadratic weighted kappa (QWK) | 0.820 |
| Mean absolute error | 0.432 grades |
| Within +/-1 grade | 94.1% |
| Mean confidence | 0.508 (below the 63.0% accuracy: under-confident on average) |

Minority classes (one-vs-rest):

| Grade | Sensitivity | Specificity |
|---|---|---|
| 1 (Doubtful) | 0.297 | 0.875 |
| 2 (Mild) | 0.472 | 0.923 |

Most errors are off by one grade (94% within +/-1), which is why QWK is much higher than plain
accuracy. Per-class precision / recall / F1 and the confusion matrix are in the evaluation report
(`python ml-service/model/evaluate.py`).

## Limitations

- **Grade 1 (Doubtful) is the weakest class**: the model finds only about 30% of true Grade 1 knees.
  Early disease is hard to separate from normal, even for human readers.
- Grade 4 has few examples (173 train / 51 test), so its metrics are uncertain.
- Trained and tested on one public dataset. Performance on other scanners, hospitals, populations or
  image qualities is unknown. Not clinically validated.
- **Heatmap:** coarse (7x7 grid upsampled), shows regions that push the severity score up, is an
  explanation aid and not a precise localisation or a diagnosis.
- **Input guard** (`input_guard.py`) is a rule-based heuristic (size, aspect ratio, grayscale, histogram
  shape), not a classifier or an authenticity check. A grayscale photo or an X-ray of another body part
  can still pass.
- Confidence is not calibrated (see above).

## Export check and speed

- The ONNX model was compared with the PyTorch model on one test image per grade: predicted grade,
  confidence, logits and cam all match within 1e-3.
- CPU latency (`onnxruntime`, 20 test images): about 40 ms per image end to end (max 48 ms), of which
  the model forward pass is about 7 ms.

## Usage

```python
from huggingface_hub import hf_hub_download
from inference import load_model, predict, InvalidInputImageError   # from the KneeSense repo

load_model(hf_hub_download(repo_id="<this repo>", filename="best_model.onnx"))
result = predict(image_bytes)   # {"kl_grade": int, "confidence": float, "heatmap_base64": str}
```
A non-X-ray input raises `InvalidInputImageError`; `err.to_dict()` is
`{"error": "invalid_input_image", "message": "..."}`.
