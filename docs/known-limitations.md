# Known Limitations and Pending Integration

This document records limitations that must not be represented as completed functionality.

## 1. Per-User Forced-Cache Handoff

The Java backend maintains a per-user live-report allowance and sends the internal header:

`X-Force-Cached-Reports: true`

when the allowance is exhausted.

The current Python `ml-service/app.py` does not read or act on this header. It currently checks only `GLOBAL_DAILY_CAP` before attempting live report generation.

Therefore, Java's per-user allowance does not yet guarantee that Python skips live report generation and serves the cached report.

The intended behavior is:

1. Java enforces the existing per-user allowance.
2. Java sends the force-cache header when the allowance is exhausted.
3. Python skips live report generation when the header is true.
4. Python returns the cached report for the predicted KL grade.
5. The existing global allowance remains 200 per rolling 24 hours by default.

The Python service owner must implement and test this handoff.

## 2. In-Memory Rate Limits

| Scope | Current Setting |
|---|---:|
| Login attempts | 5 per minute per IP |
| Java per-user live-report allowance | 10 per 24 hours |
| Python global live-report allowance | 200 per rolling 24 hours |

The counters are held in process memory. They reset when their respective services restart and are not shared across multiple application instances.

Persistent or distributed rate limiting is post-MVP work.

For cached-only local ML testing, `GLOBAL_DAILY_CAP=0` can be set in the ignored local `ml-service/.env`. The tracked environment example remains at 200.

## 3. Model Limitations

The model is an educational and research prototype and has not been clinically validated. Performance on external hospital datasets, other scanners, populations, and image qualities is unknown.

The confidence score is uncalibrated and is not the probability that the predicted grade is correct.

Grad-CAM is a coarse explanation aid, not precise disease localisation.

See `ml-service/model/model_card.md` for detailed evaluation results and limitations.

## 4. Deployment and Operational Hardening

The current integrated target is a local Docker Compose application.

Public deployment, production monitoring, distributed rate limiting, CI/CD, and advanced infrastructure are outside the current MVP scope.