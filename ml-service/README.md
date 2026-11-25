# KneeSense ML Service

The Python FastAPI service performs knee X-ray validation, ONNX model inference, Grad-CAM heatmap generation, guideline retrieval, and clinician/patient report generation.

## Technology Stack

- Python 3.11
- FastAPI and Uvicorn
- ONNX Runtime
- OpenCV and NumPy
- BM25 retrieval
- Groq and Gemini
- Hugging Face model hosting

## Responsibilities

1. Validate the input image and internal authentication header.
2. Download and load the ONNX model.
3. Predict a KL grade and uncalibrated confidence score.
4. Generate a Grad-CAM heatmap.
5. Retrieve relevant guideline snippets using BM25.
6. Generate clinician and patient reports.
7. Validate report citations against retrieved snippet IDs.
8. Use cached reports when live report generation is unavailable or globally limited.

## API Endpoints

### Health Check

`GET /health`

Returns service status, model-loaded state, and available cache grades.

### Prediction

`POST /predict`

- Content type: `multipart/form-data`
- File field: `file`
- Maximum image size: 5 MiB
- Accepted formats: PNG and JPEG
- Required internal header: `X-Internal-Auth`

The Java backend sends the request and supplies the internal authentication header. The browser must never call this service directly.

The response contains the KL grade, confidence, heatmap, clinician report, patient report, and a `live` or `cached` source label.

See [the API contract](../docs/api_contract.md) for request and response details.

## Environment Configuration

The Docker Compose service reads `ml-service/.env`.

Create it from the tracked example:

```powershell
Copy-Item .env.example .env
```

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API credential |
| `GROQ_MODEL` | Groq model identifier |
| `GEMINI_API_KEY` | Gemini API credential |
| `GEMINI_MODEL` | Gemini model identifier |
| `HF_MODEL_REPO` | Hugging Face model repository |
| `HF_TOKEN` | Optional Hugging Face access token |
| `INTERNAL_AUTH_SECRET` | Must match Java's `ML_SERVICE_SECRET` |
| `GLOBAL_DAILY_CAP` | Global live-report allowance per rolling 24 hours |

At least one working report provider credential is required for live report generation. The service tries Groq first and Gemini second.

## Global Report Limit

The default global live-report allowance is:

```text
GLOBAL_DAILY_CAP=200
```

The Python counter is held in process memory and resets when the ML service restarts.

For cached-only local testing, set `GLOBAL_DAILY_CAP=0` in the ignored local `.env` file. Do not change the tracked example from 200.

The Java backend also maintains a per-user live-report allowance. Its forced-cache request header is not yet processed by the current Python endpoint. This integration item is documented in [known limitations](../docs/known-limitations.md).

## Model

The service downloads `best_model.onnx` from the configured Hugging Face repository during startup. Model weights are not committed to this repository.

The model uses EfficientNet-B0 with a CORAL ordinal classification head. It returns a KL grade, uncalibrated confidence, and coarse Grad-CAM heatmap.

See [`model/model_card.md`](model/model_card.md) for architecture, preprocessing, training details, evaluation results, and limitations.

## Retrieval and Report Generation

Guideline snippets are maintained under:

```text
rag/guidelines/
```

The BM25 index is generated from these files during the Docker image build:

```powershell
python -m rag.build_index
```

The generated `rag/bm25_index.pkl` is a build artifact and is not committed.

The report generator:

1. Retrieves guideline snippets for the predicted KL grade.
2. Sends the snippets to Groq.
3. Tries Gemini if Groq fails.
4. Checks generated citations against retrieved snippet IDs.
5. Falls back to the cached report for the predicted grade when live report generation fails.

Cached reports are maintained in `cache/cached_reports.json`.

## Run Locally

From this directory, after configuring the environment file:

```powershell
python -m pip install -r requirements.txt
python -m rag.build_index
uvicorn app:app --host 127.0.0.1 --port 8000
```

For the complete integrated application, use Docker Compose from the repository root.

## Data Handling and Safety

- Uploaded image bytes are processed in memory and are not retained as image files.
- The browser does not communicate directly with this service.
- The internal authentication secret must not appear in browser code or logs.
- The model is not clinically validated and must not be used to make medical decisions.
- Confidence is uncalibrated.
- Grad-CAM is a coarse explanation aid, not precise disease localisation.