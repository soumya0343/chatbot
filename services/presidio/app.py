from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PII Redaction Sidecar")

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "PERSON",
    "US_SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "LOCATION",
    "US_BANK_NUMBER",
    "IBAN_CODE",
    "MEDICAL_LICENSE",
    "URL",
]

OPERATORS = {
    entity: OperatorConfig("replace", {"new_value": f"<REDACTED:{entity}>"})
    for entity in ENTITIES
}


class RedactRequest(BaseModel):
    text: str
    language: str = "en"


class RedactResponse(BaseModel):
    anonymized_text: str
    entity_count: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze_and_anonymize", response_model=RedactResponse)
def analyze_and_anonymize(req: RedactRequest):
    if not req.text or not req.text.strip():
        return RedactResponse(anonymized_text=req.text, entity_count=0)

    try:
        results = analyzer.analyze(
            text=req.text,
            entities=ENTITIES,
            language=req.language,
        )

        if not results:
            return RedactResponse(anonymized_text=req.text, entity_count=0)

        anonymized = anonymizer.anonymize(
            text=req.text,
            analyzer_results=results,
            operators=OPERATORS,
        )
        return RedactResponse(
            anonymized_text=anonymized.text,
            entity_count=len(results),
        )
    except Exception as e:
        logger.error(f"PII redaction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
