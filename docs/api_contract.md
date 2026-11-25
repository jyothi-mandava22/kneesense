# KneeSense ML Service API Contract

This document records the existing contract between the Java backend and the Python ML service.
The contract is based on `ml-service/app.py` and Lahari's integration handoff. Do not change field
names or endpoint behavior without agreement from the ML-service owners.

## Service configuration

The Java backend reads these values from environment variables:

- `ML_SERVICE_URL`: base URL of the deployed or local ML service, without a trailing slash.
- `ML_SERVICE_SECRET`: shared secret sent only by the Java backend.

Never put either value in frontend JavaScript, HTML, source control, screenshots, or logs.

## Health

`GET {ML_SERVICE_URL}/health`

Example response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "cache_grades": ["0", "1", "2", "3", "4"]
}
```

## Prediction

`POST {ML_SERVICE_URL}/predict`

- Content type: `multipart/form-data`
- File field: `file`
- Required internal header: `X-Internal-Auth: <ML_SERVICE_SECRET>`
- Maximum upload size: 5 MiB
- Accepted image formats: PNG and JPEG
- Initial Java HTTP timeout: 90 seconds to account for ML-service cold starts.

Success response (HTTP 200):

```json
{
  "kl_grade": 2,
  "confidence": 0.51,
  "heatmap_base64": "<base64-encoded PNG>",
  "clinician_report": "...",
  "patient_report": "...",
  "source": "live"
}
```

The response must retain these exact field names. `source` is `live` or `cached` and must be
passed through from the ML service, not inferred by Java.

## Error responses

The service returns `{"error":"<code>","message":"<text>"}`.

| HTTP status | Error code | Backend handling |
|---|---|---|
| 401 | `unauthorized` | Configuration failure; log a safe operational error, never expose the secret. |
| 422 | `invalid_input_image` | Return a friendly image-validation message to the user. |
| 503 | `model_unavailable` | Ask the user to retry after the service has loaded. |
| 500 | `internal_error` | Return a generic error without stack traces. |

## Application privacy and authorization rules

- The browser calls Spring Boot only. The browser must never call the ML service directly.
- Java adds `X-Internal-Auth` server-side. The secret must never reach the browser.
- Patient responses must not contain `clinician_report`; strip it in the Java response DTO.
- Doctors may receive clinician reports only for patients assigned to them.
- Patients may access only their own assessments. Missing and forbidden ownership lookups return 404.
- Do not persist uploaded X-ray bytes or heatmap images. Store only approved assessment metadata and reports.
- Never log image bytes, report bodies, authorization headers, or secrets.

## Confidence and heatmap presentation

- Label confidence as **Model confidence score (uncalibrated)**.
- Explain that it is not the probability that the predicted grade is correct.
- Do not represent it as model accuracy or as a probability of correctness.
- The heatmap is a coarse explanation aid, not precise localisation or a diagnosis.

Both reports already include the disclaimer:

> AI-generated summary — not a diagnosis, confirm with a doctor.

Do not remove or shorten that disclaimer.
