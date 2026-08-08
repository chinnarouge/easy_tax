from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.app.db import get_conn


@dataclass
class DocumentRecord:
    document_id: str
    file_name: str
    content_type: str
    classification: str
    file_size: int = 0
    extracted_fields: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


CLASSIFICATION_KEYWORDS: list[tuple[list[str], str]] = [
    (["lohn", "gehalt", "salary", "lohnsteuer"], "lohnsteuerbescheinigung"),
    (["beleg", "receipt", "quittung", "rechnung"], "receipt"),
    (["versicherung", "insurance", "vorsorge", "kranken", "rente"], "insurance_certificate"),
    (["miet", "rent", "pacht", "nebenkost"], "rental_document"),
    (["spende", "donat", "zuwendung"], "donation_receipt"),
    (["broker", "depot", "capital", "dividende", "kapital"], "broker_statement"),
    (["kind", "child", "betreuung", "kita"], "childcare_document"),
]

EXTRACTION_TEMPLATES: dict[str, tuple[dict[str, object], float]] = {
    "lohnsteuerbescheinigung": (
        {
            "bruttolohn": 52000,
            "einbehaltene_lohnsteuer": 8400,
            "solidaritaetszuschlag": 462,
            "kirchensteuer": 756,
            "rentenversicherung_ag": 4836,
            "krankenversicherung_ag": 3796,
            "pflegeversicherung_ag": 845,
            "arbeitslosenversicherung_ag": 650,
        },
        0.91,
    ),
    "receipt": (
        {"total_amount": 128.50, "category": "work_equipment", "date": "2025-03-15"},
        0.78,
    ),
    "insurance_certificate": (
        {"insurance_type": "health", "annual_contribution": 4800, "employer_share": 3796},
        0.85,
    ),
    "rental_document": (
        {"monthly_rent": 850, "annual_rent": 10200, "property_address": "extracted address"},
        0.72,
    ),
    "donation_receipt": (
        {"recipient": "Organization name", "amount": 250, "date": "2025-06-10"},
        0.88,
    ),
    "broker_statement": (
        {"capital_gains": 1850, "withheld_tax": 462.50, "soli_on_cap": 25.44},
        0.82,
    ),
    "childcare_document": (
        {"provider": "Kita name", "annual_cost": 3600, "child_name": "extracted"},
        0.80,
    ),
}


def classify_document(file_name: str, content_type: str) -> str:
    lowered = f"{file_name} {content_type}".lower()
    for keywords, classification in CLASSIFICATION_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return classification
    return "unknown"


def extract_document_fields(classification: str) -> tuple[dict[str, object], float]:
    template = EXTRACTION_TEMPLATES.get(classification)
    if template:
        return template
    return ({"notes": "Unrecognised document — manual review required"}, 0.35)


def upload_document(file_name: str, content_type: str, file_size: int = 0) -> DocumentRecord:
    conn = get_conn()
    classification = classify_document(file_name, content_type)
    extracted_fields, confidence = extract_document_fields(classification)
    created_at = datetime.now(timezone.utc).isoformat()
    doc_id = str(uuid4())
    conn.execute(
        "INSERT INTO documents (document_id, file_name, content_type, classification, file_size, extracted_fields_json, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, file_name, content_type, classification, file_size, json.dumps(extracted_fields), confidence, created_at),
    )
    conn.commit()
    return DocumentRecord(
        document_id=doc_id,
        file_name=file_name,
        content_type=content_type,
        classification=classification,
        file_size=file_size,
        extracted_fields=extracted_fields,
        confidence=confidence,
        created_at=created_at,
    )


def _row_to_record(row) -> DocumentRecord:
    return DocumentRecord(
        document_id=row["document_id"],
        file_name=row["file_name"],
        content_type=row["content_type"],
        classification=row["classification"],
        file_size=row["file_size"],
        extracted_fields=json.loads(row["extracted_fields_json"]),
        confidence=row["confidence"],
        created_at=row["created_at"],
    )


def get_document(document_id: str) -> DocumentRecord | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_documents() -> list[DocumentRecord]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    return [_row_to_record(r) for r in rows]
