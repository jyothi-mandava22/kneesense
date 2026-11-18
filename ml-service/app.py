"""KneeSense ml-service. POST /predict returns the locked contract shape.

Order of work per request: check secret -> read upload -> model predict ->
(live reports unless global cap hit or generation fails) -> cached reports.
"""
import hmac
import json
import logging
import os
import sys
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse

load_dotenv()
logger = logging.getLogger("ml-service")
logging.basicConfig(level=logging.INFO)

# Teju's files must stay together; her code imports them as top-level modules.
MODEL_DIR = Path(__file__).parent / "model"
sys.path.insert(0, str(MODEL_DIR))

from inference import load_model, predict  # noqa: E402

try:
    from inference import InvalidInputImageError  # noqa: E402
except ImportError:
    InvalidInputImageError = None  # older inference.py raises ValueError for bad images

from rag.report_generator import ReportGenerationError, generate_reports  # noqa: E402
from rag.retriever import retrieve  # noqa: E402

CACHE_PATH = Path(__file__).parent / "cache" / "cached_reports.json"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
HF_REPO = os.environ.get("HF_MODEL_REPO") or "KneeSense-cnn/kneesense-cnn"
GLOBAL_DAILY_CAP = int(os.environ.get("GLOBAL_DAILY_CAP", "200"))

STATE = {"model_loaded": False, "session": None, "cache": {}}
_calls: deque = deque()
_calls_lock = threading.Lock()


def error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


def try_reserve_live_call() -> bool:
    """Rolling 24h counter (in memory; resets on restart). False means cap reached."""
    now = time.time()
    with _calls_lock:
        while _calls and now - _calls[0] > 86400:
            _calls.popleft()
        if len(_calls) >= GLOBAL_DAILY_CAP:
            return False
        _calls.append(now)
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=HF_REPO,
            filename="best_model.onnx",
            token=os.environ.get("HF_TOKEN") or None,
        )
        STATE["session"] = load_model(path)
        STATE["model_loaded"] = True
        logger.info("Model loaded from %s", HF_REPO)
    except Exception:
        logger.exception("Model failed to load; /predict will return model_unavailable")
    try:
        STATE["cache"] = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Cached reports could not be loaded")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": STATE["model_loaded"], "cache_grades": sorted(STATE["cache"])}


@app.post("/predict")
def predict_endpoint(request: Request, file: UploadFile = File(...)):
    # 1. Shared-secret check (constant time). No secret configured = refuse everything.
    expected = os.environ.get("INTERNAL_AUTH_SECRET", "")
    supplied = request.headers.get("X-Internal-Auth", "")
    if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Missing or invalid credentials."})

    # 2. Read upload (size capped)
    image_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        return error("invalid_input_image", "Empty file.", 422)
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        return error("invalid_input_image", "File is larger than 5 MB.", 422)

    # 3. Model
    if not STATE["model_loaded"]:
        return error("model_unavailable", "The model is not loaded yet. Please retry shortly.", 503)
    try:
        result = predict(image_bytes, STATE["session"])
    except Exception as err:
        is_bad_image = isinstance(err, ValueError) or (
            InvalidInputImageError is not None and isinstance(err, InvalidInputImageError)
        )
        if is_bad_image:
            body = err.to_dict() if hasattr(err, "to_dict") else {
                "error": "invalid_input_image", "message": str(err)}
            return JSONResponse(status_code=422, content=body)
        logger.exception("Prediction failed")
        return error("internal_error", "Prediction failed.", 500)

    kl_grade, confidence = int(result["kl_grade"]), float(result["confidence"])

    # 4. Reports: live if allowed, otherwise (or on any failure) cached
    reports, source = None, "live"
    if try_reserve_live_call():
        try:
            reports = generate_reports(kl_grade, confidence, retrieve(kl_grade, top_k=4))
        except ReportGenerationError as exc:
            logger.warning("Live reports failed, using cache: %s", exc)
        except Exception:
            logger.exception("Unexpected report error, using cache")
    else:
        logger.warning("Global cap reached, serving cached reports")
    if reports is None:
        reports, source = STATE["cache"].get(str(kl_grade)), "cached"
    if not reports:
        return error("internal_error", "Reports are unavailable.", 500)

    return {
        "kl_grade": kl_grade,
        "confidence": confidence,
        "heatmap_base64": result["heatmap_base64"],
        "clinician_report": reports["clinician_report"],
        "patient_report": reports["patient_report"],
        "source": source,
    }