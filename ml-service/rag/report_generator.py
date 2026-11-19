"""Generate clinician + patient reports from retrieved guideline snippets.

Flow: Groq -> Gemini -> raise ReportGenerationError (app.py then serves cache).
Every output must cite retrieved snippet IDs like [g2-1]; invalid or missing
citations count as a failed generation.
"""
import json
import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DISCLAIMER = "AI-generated summary — not a diagnosis, confirm with a doctor."
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")  # set to the current free Flash model name from AI Studio
STRIP_CITATIONS_FOR_PATIENT = True  # patient text is shown without [g2-1] tags after verification

BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")


class ReportGenerationError(Exception):
    """Raised when Groq, Gemini, or the citation check fails."""


def _build_prompt(kl_grade: int, confidence: float, chunks: list[dict]) -> str:
    snippets = "\n".join(f"[{c['id']}] {c['text']}" for c in chunks)
    return f"""You write two short reports about a knee X-ray result.

Result: Kellgren-Lawrence (KL) grade {kl_grade} (scale 0-4), predicted by an AI model from a knee X-ray. Do not state any confidence number or percentage.

Guideline snippets (the ONLY allowed source of medical content):
{snippets}

Rules:
- Only use the retrieved guideline text above. Do not add outside medical claims, drug doses, or new diagnoses.
- End every sentence that states guideline information with the snippet ID in square brackets, e.g. [g2-1]. Use only the IDs listed above.
- Do not write any disclaimer; it is added automatically.
- clinician_report: concise structured note (grade and guideline-based next steps), under 150 words.
- patient_report: plain language, calm tone, under 150 words: what the grade means, what to expect, when to see a specialist.

Return ONLY a JSON object with exactly these keys: "clinician_report", "patient_report"."""


def _call_groq(prompt: str) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=20.0)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai

    if not GEMINI_MODEL:
        raise RuntimeError("GEMINI_MODEL is not set")
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
    resp = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.2},
        request_options={"timeout": 20},
    )
    return resp.text


def _parse(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    data = json.loads(text)
    for key in ("clinician_report", "patient_report"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing or empty '{key}'")
    return data


def check_citations(text: str, allowed_ids: set[str]) -> None:
    """Raise ValueError if there are no citations or any cited ID wasn't retrieved."""
    cited = []
    for group in BRACKET_RE.findall(text):
        cited.extend(tok for tok in re.split(r"[,\s;]+", group.strip()) if tok)
    if not cited:
        raise ValueError("No citations found")
    bad = [c for c in cited if c not in allowed_ids]
    if bad:
        raise ValueError(f"Invalid citation IDs: {bad}")


def _model_notes(kl_grade: int, confidence: float | None) -> tuple[str, str]:
    clinician, patient = [], []
    if confidence is not None:
        clinician.append(
            f"Model confidence score: {confidence:.2f} (uncalibrated; not the probability that the grade is correct)."
        )
    if kl_grade == 1:
        clinician.append(
            "Grade 1 (Doubtful) is this model's weakest class on the test set (sensitivity about 30%); interpret with extra caution."
        )
        patient.append("Early-stage findings like this are the hardest for the tool to judge, so a doctor's review is especially important.")
    return " ".join(clinician), " ".join(patient)


def _finalize(data: dict, allowed_ids: set[str], kl_grade: int, confidence: float | None) -> dict[str, str]:
    clinician, patient = data["clinician_report"].strip(), data["patient_report"].strip()
    check_citations(clinician, allowed_ids)
    check_citations(patient, allowed_ids)
    if STRIP_CITATIONS_FOR_PATIENT:
        patient = re.sub(r"\s*\[[^\[\]]+\]", "", patient).strip()
    note_c, note_p = _model_notes(kl_grade, confidence)
    clinician = f"{clinician}\n\n{note_c}" if note_c else clinician
    patient = f"{patient}\n\n{note_p}" if note_p else patient
    return {
        "clinician_report": f"{clinician}\n\n{DISCLAIMER}",
        "patient_report": f"{patient}\n\n{DISCLAIMER}",
    }


def generate_reports(kl_grade: int, confidence: float | None, retrieved_chunks: list[dict]) -> dict[str, str]:
    """Return {"clinician_report": str, "patient_report": str}, both ending with DISCLAIMER.
    Raises ReportGenerationError if every provider fails or fails the citation check."""
    allowed_ids = {c["id"] for c in retrieved_chunks}
    if not allowed_ids:
        raise ReportGenerationError("No retrieved snippets")
    prompt = _build_prompt(kl_grade, confidence, retrieved_chunks)
    errors = []
    for name, call in (("groq", _call_groq), ("gemini", _call_gemini)):
        try:
            return _finalize(_parse(call(prompt)), allowed_ids, kl_grade, confidence)
        except Exception as exc:  # any failure -> try next provider
            logger.warning("%s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise ReportGenerationError("; ".join(errors))