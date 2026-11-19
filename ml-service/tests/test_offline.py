"""Offline test: report generator with fake LLM replies. Run: python -m tests.test_offline"""
import json

from rag import report_generator as rg
from rag.report_generator import DISCLAIMER, ReportGenerationError, check_citations, generate_reports
from rag.retriever import retrieve


def expect_error(fn, exc):
    try:
        fn()
    except exc:
        return
    raise AssertionError("expected an error but none was raised")


chunks = retrieve(2, 3)
cid = chunks[0]["id"]
good = json.dumps({"clinician_report": f"Mild OA. [{cid}]", "patient_report": f"This is mild. [{cid}]"})
bad = json.dumps({"clinician_report": "No citation here.", "patient_report": "None here either."})

# 1. citation checker
check_citations("Text [g2-1, g2-2].", {"g2-1", "g2-2"})
expect_error(lambda: check_citations("No tags", {"g2-1"}), ValueError)
expect_error(lambda: check_citations("Bad [g9-9].", {"g2-1"}), ValueError)
print("1 ok: citation checker")

# 2. good Groq reply
rg._call_groq, rg._call_gemini = (lambda p: good), (lambda p: bad)
out = generate_reports(2, None, chunks)
assert out["clinician_report"].endswith(DISCLAIMER) and out["patient_report"].endswith(DISCLAIMER)
assert "[" not in out["patient_report"], "patient text should have no citation tags"
assert "confidence" not in out["clinician_report"].lower()
print("2 ok: disclaimer, stripped patient tags, no confidence when None")

# 3. Groq bad -> Gemini good
rg._call_groq, rg._call_gemini = (lambda p: bad), (lambda p: good)
generate_reports(2, 0.4, chunks)
print("3 ok: fallback to Gemini")

# 4. both bad -> error (app.py will serve cache)
rg._call_groq, rg._call_gemini = (lambda p: bad), (lambda p: bad)
expect_error(lambda: generate_reports(2, 0.4, chunks), ReportGenerationError)
print("4 ok: raises ReportGenerationError when both fail")

# 5. grade 1 gets the extra notes, confidence note shown when given
c1 = retrieve(1, 3)
good1 = json.dumps({"clinician_report": f"Note. [{c1[0]['id']}]", "patient_report": f"Info. [{c1[0]['id']}]"})
rg._call_groq = lambda p: good1
out1 = generate_reports(1, 0.35, c1)
assert "weakest class" in out1["clinician_report"]
assert "0.35" in out1["clinician_report"]
assert "doctor's review" in out1["patient_report"]
print("5 ok: grade 1 notes and confidence note")

print("\nALL OFFLINE TESTS PASSED")