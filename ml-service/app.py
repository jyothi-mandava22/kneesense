"""FastAPI entrypoint. POST /predict returns the locked contract shape."""
from fastapi import FastAPI, File, UploadFile

app = FastAPI()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    """Return {kl_grade, confidence, heatmap_base64, clinician_report, patient_report, source}
    or {"error": "<code>", "message": "<string>"}."""
    raise NotImplementedError