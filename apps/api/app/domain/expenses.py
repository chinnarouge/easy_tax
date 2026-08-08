from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.app.db import get_conn

EXPENSE_CATEGORIES = {
    "work_equipment": {
        "label_de": "Arbeitsmittel",
        "label_en": "Work equipment (laptop, phone, desk, chair, monitor)",
        "form": "Anlage N",
        "line": "Zeile 42",
        "hint": "Items over 800 EUR net must be depreciated over useful life.",
    },
    "training": {
        "label_de": "Fortbildungskosten",
        "label_en": "Training, courses, certifications, conferences",
        "form": "Anlage N",
        "line": "Zeile 44",
        "hint": "Fully deductible including travel, accommodation, and materials.",
    },
    "professional_books": {
        "label_de": "Fachliteratur",
        "label_en": "Professional books, journals, subscriptions",
        "form": "Anlage N",
        "line": "Zeile 42",
        "hint": "Must be related to your profession. Keep receipts.",
    },
    "software": {
        "label_de": "Software und Lizenzen",
        "label_en": "Software, apps, cloud subscriptions for work",
        "form": "Anlage N",
        "line": "Zeile 42",
        "hint": "Office, antivirus, VPN, IDE, design tools — if used for work.",
    },
    "phone_internet": {
        "label_de": "Telefon und Internet",
        "label_en": "Phone and internet (work share)",
        "form": "Anlage N",
        "line": "Zeile 46",
        "hint": "20% flat rate (max 20 EUR/month) accepted without proof, or actual work share.",
    },
    "work_clothing": {
        "label_de": "Berufskleidung",
        "label_en": "Work clothing and cleaning",
        "form": "Anlage N",
        "line": "Zeile 42",
        "hint": "Only typical work clothing (safety shoes, uniform). Not everyday clothes.",
    },
    "union_dues": {
        "label_de": "Gewerkschaftsbeitraege",
        "label_en": "Trade union membership fees",
        "form": "Anlage N",
        "line": "Zeile 40",
        "hint": "Fully deductible. Usually confirmed by your union's annual statement.",
    },
    "job_search": {
        "label_de": "Bewerbungskosten",
        "label_en": "Job application costs (photos, travel, printing, coaching)",
        "form": "Anlage N",
        "line": "Zeile 46",
        "hint": "Flat 8.50 EUR per written application, 15 EUR per folder application, or actual costs.",
    },
    "business_travel": {
        "label_de": "Reisekosten (Dienstreise)",
        "label_en": "Business travel (transport, hotel, meals)",
        "form": "Anlage N",
        "line": "Zeile 49",
        "hint": "Meal allowances: 14 EUR (8-24h) or 28 EUR (24h+). Keep all receipts.",
    },
    "relocation": {
        "label_de": "Umzugskosten",
        "label_en": "Work-related relocation costs",
        "form": "Anlage N",
        "line": "Zeile 46",
        "hint": "If you moved for work. Flat rate 886 EUR (single) or 1,773 EUR (married) plus transport.",
    },
    "double_household": {
        "label_de": "Doppelte Haushaltsfuehrung",
        "label_en": "Double household (rent at work location)",
        "form": "Anlage N-DH",
        "line": "Zeile 1",
        "hint": "Rent up to 1,000 EUR/month plus weekly home travel. Must maintain primary household.",
    },
    "donations": {
        "label_de": "Spenden",
        "label_en": "Donations to charities and political parties",
        "form": "Mantelbogen",
        "line": "Zeile 45",
        "hint": "Up to 20% of income. Political parties: 50% direct credit up to 825 EUR (single).",
    },
    "childcare": {
        "label_de": "Kinderbetreuungskosten",
        "label_en": "Childcare costs (Kita, nanny, after-school care)",
        "form": "Anlage Kind",
        "line": "Zeile 73",
        "hint": "2/3 of costs, max 4,000 EUR per child. Child must be under 14.",
    },
    "school_fees": {
        "label_de": "Schulgeld",
        "label_en": "Private school fees",
        "form": "Anlage Kind",
        "line": "Zeile 65",
        "hint": "30% of school fees deductible, max 5,000 EUR per child. State-approved schools only.",
    },
    "medical": {
        "label_de": "Krankheitskosten",
        "label_en": "Medical expenses (glasses, dental, prescriptions, therapy)",
        "form": "Mantelbogen",
        "line": "Zeile 67",
        "hint": "Only above your personal threshold (1-7% of income depending on family status).",
    },
    "disability": {
        "label_de": "Behindertenpauschbetrag",
        "label_en": "Disability allowance",
        "form": "Mantelbogen",
        "line": "Zeile 61",
        "hint": "384 EUR (GdB 20) up to 7,400 EUR (GdB 100). No receipts needed.",
    },
    "care_costs": {
        "label_de": "Pflegekosten",
        "label_en": "Care costs (for yourself or dependents)",
        "form": "Mantelbogen",
        "line": "Zeile 67",
        "hint": "Home care, nursing home, care for elderly parents.",
    },
    "alimony": {
        "label_de": "Unterhaltszahlungen",
        "label_en": "Alimony / maintenance payments",
        "form": "Anlage U",
        "line": "Zeile 4",
        "hint": "Up to 13,805 EUR as Sonderausgaben (with recipient's consent) or up to Grundfreibetrag.",
    },
    "household_cleaning": {
        "label_de": "Reinigung / Haushaltshilfe",
        "label_en": "Cleaning, household help, gardening",
        "form": "Mantelbogen",
        "line": "Zeile 72",
        "hint": "20% tax credit on labour costs, max 4,000 EUR credit. Minijob: max 510 EUR credit.",
    },
    "craftsmen": {
        "label_de": "Handwerkerleistungen",
        "label_en": "Craftsmen, repairs, renovations (labour only)",
        "form": "Mantelbogen",
        "line": "Zeile 73",
        "hint": "20% tax credit on labour costs only, max 1,200 EUR credit. Must be paid by bank transfer.",
    },
    "chimney_sweep": {
        "label_de": "Schornsteinfeger",
        "label_en": "Chimney sweep / heating maintenance",
        "form": "Mantelbogen",
        "line": "Zeile 73",
        "hint": "Counts as Handwerkerleistung. Keep the invoice.",
    },
    "student_tuition": {
        "label_de": "Studiengebuehren / Semesterbeitraege",
        "label_en": "Tuition and semester fees",
        "form": "Mantelbogen",
        "line": "Zeile 43 (Sonderausgaben) or Anlage N",
        "hint": "First degree: up to 6,000 EUR as Sonderausgaben. Second degree/Master: unlimited as Werbungskosten.",
    },
    "commute_public_transport": {
        "label_de": "OEPNV-Ticket / Deutschlandticket",
        "label_en": "Public transport pass / Deutschlandticket",
        "form": "Anlage N",
        "line": "Zeile 35",
        "hint": "Can claim actual cost if higher than Entfernungspauschale. Deutschlandticket: 588 EUR/year.",
    },
    "insurance_private": {
        "label_de": "Private Versicherungen",
        "label_en": "Private insurance (liability, accident, legal protection)",
        "form": "Anlage Vorsorge",
        "line": "Zeile 46",
        "hint": "Haftpflicht, Unfall, Rechtsschutz (work-related share only for legal).",
    },
    "misc_werbungskosten": {
        "label_de": "Sonstige Werbungskosten",
        "label_en": "Other work-related expenses",
        "form": "Anlage N",
        "line": "Zeile 46",
        "hint": "Any expense that serves your job: parking at work, tolls, locker fees, etc.",
    },
}


@dataclass
class ExpenseRecord:
    expense_id: str
    tax_return_id: str
    category: str
    description: str
    amount_eur: float
    date: str
    receipt_document_id: str | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def add_expense(
    tax_return_id: str,
    category: str,
    description: str,
    amount_eur: float,
    date: str,
    receipt_document_id: str | None = None,
) -> ExpenseRecord:
    conn = get_conn()
    expense_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO expenses (expense_id, tax_return_id, category, description, amount_eur, date, receipt_document_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (expense_id, tax_return_id, category, description, amount_eur, date, receipt_document_id, created_at),
    )
    conn.commit()
    return ExpenseRecord(
        expense_id=expense_id,
        tax_return_id=tax_return_id,
        category=category,
        description=description,
        amount_eur=amount_eur,
        date=date,
        receipt_document_id=receipt_document_id,
        created_at=created_at,
    )


def _row_to_record(row) -> ExpenseRecord:
    return ExpenseRecord(
        expense_id=row["expense_id"],
        tax_return_id=row["tax_return_id"],
        category=row["category"],
        description=row["description"],
        amount_eur=row["amount_eur"],
        date=row["date"],
        receipt_document_id=row["receipt_document_id"],
        created_at=row["created_at"],
    )


def list_expenses(tax_return_id: str) -> list[ExpenseRecord]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM expenses WHERE tax_return_id = ? ORDER BY created_at DESC", (tax_return_id,)).fetchall()
    return [_row_to_record(r) for r in rows]


def delete_expense(tax_return_id: str, expense_id: str) -> bool:
    conn = get_conn()
    cursor = conn.execute(
        "DELETE FROM expenses WHERE expense_id = ? AND tax_return_id = ?",
        (expense_id, tax_return_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_expense_totals(tax_return_id: str) -> dict[str, float]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT category, SUM(amount_eur) AS total FROM expenses WHERE tax_return_id = ? GROUP BY category",
        (tax_return_id,),
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}
