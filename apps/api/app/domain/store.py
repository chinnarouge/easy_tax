from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from apps.api.app.db import get_conn
from apps.api.app.domain.onboarding import OnboardingProfile


@dataclass
class TaxReturnRecord:
    tax_return_id: str
    tax_year: int
    profile: OnboardingProfile
    status: str = "draft"
    required_anlagen: list[str] = field(default_factory=list)
    sections: dict[str, dict[str, object]] = field(default_factory=dict)


def _row_to_record(row) -> TaxReturnRecord:
    profile_data = json.loads(row["profile_json"])
    return TaxReturnRecord(
        tax_return_id=row["tax_return_id"],
        tax_year=row["tax_year"],
        status=row["status"],
        profile=OnboardingProfile(**profile_data),
        required_anlagen=json.loads(row["required_anlagen_json"]),
        sections=json.loads(row["sections_json"]),
    )


def _profile_to_dict(profile: OnboardingProfile) -> dict:
    return {
        "employment_status": profile.employment_status,
        "marital_status": profile.marital_status,
        "has_children": profile.has_children,
        "num_children": profile.num_children,
        "rental_income": profile.rental_income,
        "capital_gains": profile.capital_gains,
        "foreign_income": profile.foreign_income,
        "home_office_days": profile.home_office_days,
        "commute_km": profile.commute_km,
        "commute_days": profile.commute_days,
        "donations_eur": profile.donations_eur,
        "has_insurance_expenses": profile.has_insurance_expenses,
        "has_haushaltsnahe": profile.has_haushaltsnahe,
        "has_handwerker": profile.has_handwerker,
        "church_member": profile.church_member,
        "bundesland": profile.bundesland,
        "tax_class": profile.tax_class,
    }


def create_tax_return(tax_year: int, profile: OnboardingProfile, required_anlagen: list[str]) -> TaxReturnRecord:
    conn = get_conn()
    tax_return_id = str(uuid4())
    conn.execute(
        "INSERT INTO tax_returns (tax_return_id, tax_year, status, profile_json, required_anlagen_json, sections_json) VALUES (?, ?, ?, ?, ?, ?)",
        (tax_return_id, tax_year, "draft", json.dumps(_profile_to_dict(profile)), json.dumps(required_anlagen), "{}"),
    )
    conn.commit()
    return TaxReturnRecord(
        tax_return_id=tax_return_id,
        tax_year=tax_year,
        profile=profile,
        required_anlagen=required_anlagen,
    )


def get_tax_return(tax_return_id: str) -> TaxReturnRecord | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tax_returns WHERE tax_return_id = ?", (tax_return_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_tax_returns() -> list[TaxReturnRecord]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tax_returns").fetchall()
    return [_row_to_record(r) for r in rows]


def update_tax_return_section(tax_return_id: str, section: str, values: dict[str, object]) -> TaxReturnRecord | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tax_returns WHERE tax_return_id = ?", (tax_return_id,)).fetchone()
    if row is None:
        return None
    sections = json.loads(row["sections_json"])
    if section not in sections:
        sections[section] = {}
    sections[section].update(values)
    conn.execute(
        "UPDATE tax_returns SET sections_json = ? WHERE tax_return_id = ?",
        (json.dumps(sections), tax_return_id),
    )
    conn.commit()
    return _row_to_record(conn.execute("SELECT * FROM tax_returns WHERE tax_return_id = ?", (tax_return_id,)).fetchone())


def calculate_completion(record: TaxReturnRecord) -> int:
    completed_sections = len(record.sections)
    required_sections = max(len(record.required_anlagen), 1)
    return min(100, round((completed_sections / required_sections) * 100))
