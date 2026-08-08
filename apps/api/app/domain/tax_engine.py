from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data"


@lru_cache(maxsize=1)
def load_tax_brackets() -> dict:
    with (DATA_DIR / "tax_brackets_2025.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_deduction_rules() -> dict:
    with (DATA_DIR / "deduction_rules.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class TaxEstimateInput:
    taxable_income: float
    filing_type: str = "single"
    church_tax_rate: float = 0.0


@dataclass(frozen=True)
class TaxEstimateResult:
    income_tax: float
    solidarity_surcharge: float
    church_tax: float
    total_tax: float
    effective_rate: float
    filing_type: str


def _compute_income_tax(taxable_income: float) -> float:
    """Section 32a EStG progressive formula for 2025."""
    brackets = load_tax_brackets()
    grundfreibetrag = brackets["grundfreibetrag_single"]

    if taxable_income <= 0:
        return 0.0
    if taxable_income <= grundfreibetrag:
        return 0.0
    if taxable_income <= 17443:
        y = (taxable_income - grundfreibetrag) / 10000
        return (922.98 * y + 1400) * y
    if taxable_income <= 68480:
        z = (taxable_income - 17443) / 10000
        return (181.19 * z + 2397) * z + 1016.37
    if taxable_income <= 277825:
        return 0.42 * taxable_income - 10693.32
    return 0.45 * taxable_income - 18956.63


def _compute_soli(income_tax: float) -> float:
    if income_tax <= 18130:
        return 0.0
    if income_tax <= 33100:
        return round((income_tax - 18130) * 0.119, 2)
    return round(income_tax * 0.055, 2)


def _compute_church_tax(income_tax: float, rate: float) -> float:
    if rate <= 0:
        return 0.0
    return round(income_tax * rate, 2)


def estimate_tax(payload: TaxEstimateInput) -> TaxEstimateResult:
    if payload.filing_type == "joint":
        half_income = payload.taxable_income / 2
        income_tax = round(_compute_income_tax(half_income) * 2, 2)
    else:
        income_tax = round(_compute_income_tax(payload.taxable_income), 2)

    solidarity_surcharge = _compute_soli(income_tax)
    church_tax = _compute_church_tax(income_tax, payload.church_tax_rate)
    total_tax = round(income_tax + solidarity_surcharge + church_tax, 2)
    effective_rate = round((total_tax / payload.taxable_income) * 100, 2) if payload.taxable_income > 0 else 0.0

    return TaxEstimateResult(
        income_tax=income_tax,
        solidarity_surcharge=solidarity_surcharge,
        church_tax=church_tax,
        total_tax=total_tax,
        effective_rate=effective_rate,
        filing_type=payload.filing_type,
    )
