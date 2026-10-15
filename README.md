# KneeSense

AI-powered knee osteoarthritis severity grading (KL 0–4) with Grad-CAM explainability
and dual-audience report generation (clinician + patient).

## Team

- Tejaswi Pise — AI / Deep Learning Lead
- T. Lahari — NLP / GenAI Lead
- M. Jyothi Krishna — Full-Stack & Integration Lead

## Architecture

- `backend-java/` — Spring Boot backend, serves the frontend from `src/main/resources/static/`
- `ml-service/` — FastAPI service: ONNX inference + Grad-CAM + RAG + LLM reports
- `docs/api_contract.md` — locked contract between Java and ml-service

## Status

Day 0 — repository skeleton committed. Implementation begins Week 1.

## Setup

Will be documented once each component builds. Target: `docker compose up --build`
from a fresh clone with zero manual steps.