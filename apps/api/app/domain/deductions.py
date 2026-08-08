from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from apps.api.app.domain.onboarding import OnboardingProfile

DATA_DIR = Path(__file__).resolve().parents[4] / "data"


@lru_cache(maxsize=1)
def _load_rules() -> dict:
    with (DATA_DIR / "deduction_rules.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class DeductionSuggestion:
    title: str
    amount_eur: float | None
    form: str
    line: str
    reason: str
    field_id: str


def suggest_deductions(profile: OnboardingProfile) -> list[DeductionSuggestion]:
    rules = _load_rules().get("2025", {})
    suggestions: list[DeductionSuggestion] = []

    daily = rules.get("homeoffice_daily_eur", 6)
    max_days = rules.get("homeoffice_max_days", 210)
    employee_allowance = rules.get("employee_allowance_eur", 1230)
    first_tier = rules.get("commute_first_tier_eur_per_km", 0.30)
    second_tier = rules.get("commute_second_tier_eur_per_km", 0.38)

    if profile.commute_km > 0:
        if profile.commute_km <= 20:
            annual = profile.commute_km * first_tier * profile.commute_days
        else:
            annual = (20 * first_tier + (profile.commute_km - 20) * second_tier) * profile.commute_days
        suggestions.append(
            DeductionSuggestion(
                title="Entfernungspauschale (commuting allowance)",
                amount_eur=round(annual, 2),
                form="Anlage N",
                line="Zeile 31",
                reason=f"{profile.commute_km} km x {profile.commute_days} days at tiered rates.",
                field_id="anlage_n.entfernungspauschale_km",
            )
        )

    if profile.home_office_days > 0:
        capped_days = min(profile.home_office_days, max_days)
        suggestions.append(
            DeductionSuggestion(
                title="Homeoffice-Pauschale",
                amount_eur=capped_days * daily,
                form="Anlage N",
                line="Zeilen 61-62",
                reason=f"{capped_days} days x {daily} EUR/day.",
                field_id="anlage_n.homeoffice",
            )
        )

    suggestions.append(
        DeductionSuggestion(
            title="Kontofuehrungsgebuehren (bank fees)",
            amount_eur=16,
            form="Anlage N",
            line="Zeile 46",
            reason="Flat-rate deduction accepted without receipts.",
            field_id="anlage_n.kontofuehrung",
        )
    )

    if profile.donations_eur > 0:
        suggestions.append(
            DeductionSuggestion(
                title="Spenden (donations)",
                amount_eur=profile.donations_eur,
                form="Mantelbogen",
                line="Zeile 45",
                reason="Donation amount reported in onboarding.",
                field_id="sonderausgaben.spenden",
            )
        )

    if profile.has_children:
        suggestions.append(
            DeductionSuggestion(
                title="Kinderbetreuungskosten (childcare)",
                amount_eur=None,
                form="Anlage Kind",
                line="Zeile 73",
                reason="2/3 of childcare costs deductible, max 4,000 EUR per child.",
                field_id="anlage_kind.betreuungskosten",
            )
        )

    if profile.has_haushaltsnahe:
        suggestions.append(
            DeductionSuggestion(
                title="Haushaltsnahe Dienstleistungen",
                amount_eur=None,
                form="Mantelbogen",
                line="Zeile 72",
                reason="20% tax credit on household services, max 4,000 EUR.",
                field_id="haushaltsnahe.dienstleistungen",
            )
        )

    if profile.has_handwerker:
        suggestions.append(
            DeductionSuggestion(
                title="Handwerkerleistungen (craftsmen)",
                amount_eur=None,
                form="Mantelbogen",
                line="Zeile 73",
                reason="20% tax credit on labour costs, max 1,200 EUR.",
                field_id="haushaltsnahe.handwerker",
            )
        )

    if profile.employment_status in {"employee", "both"}:
        total_werbungskosten = sum(s.amount_eur for s in suggestions if s.amount_eur and "Anlage N" in s.form)
        if total_werbungskosten < employee_allowance:
            suggestions.append(
                DeductionSuggestion(
                    title="Arbeitnehmerpauschbetrag (employee lump sum)",
                    amount_eur=employee_allowance,
                    form="Anlage N",
                    line="Werbungskosten",
                    reason=f"Automatic {employee_allowance} EUR if itemised deductions are lower.",
                    field_id="anlage_n.bruttolohn",
                )
            )

    return suggestions
