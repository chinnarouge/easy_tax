from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OnboardingProfile:
    employment_status: str
    marital_status: str = "single"
    has_children: bool = False
    num_children: int = 0
    rental_income: bool = False
    capital_gains: bool = False
    foreign_income: bool = False
    home_office_days: int = 0
    commute_km: int = 0
    commute_days: int = 230
    donations_eur: float = 0.0
    has_insurance_expenses: bool = True
    has_haushaltsnahe: bool = False
    has_handwerker: bool = False
    church_member: bool = False
    bundesland: str = "Bayern"
    tax_class: int = 1


@dataclass(frozen=True)
class OnboardingResult:
    required_anlagen: list[str] = field(default_factory=list)
    suggested_next_steps: list[str] = field(default_factory=list)


def determine_required_anlagen(profile: OnboardingProfile) -> OnboardingResult:
    required_anlagen = ["Mantelbogen"]
    next_steps = ["Confirm personal data", "Review income sources"]

    if profile.employment_status in {"employee", "both", "retired"}:
        required_anlagen.append("Anlage N")
        next_steps.append("Prepare your Lohnsteuerbescheinigung")

    if profile.employment_status == "student":
        next_steps.append("Check if you had taxable income (Minijob, Werkstudent, internship)")
        next_steps.append("Students can carry forward losses (Verlustvortrag) for future use")

    if profile.employment_status == "unemployed":
        next_steps.append("Gather Arbeitslosengeld / ALG-I or ALG-II statements")
        next_steps.append("ALG is tax-free but subject to Progressionsvorbehalt")

    if profile.rental_income:
        required_anlagen.append("Anlage V")
        next_steps.append("Prepare rental expense documents")

    if profile.capital_gains:
        required_anlagen.append("Anlage KAP")
        next_steps.append("Collect broker statements")

    if profile.has_children:
        required_anlagen.append("Anlage Kind")
        next_steps.append("Gather child care cost receipts")

    if profile.foreign_income:
        required_anlagen.append("Anlage AUS")
        next_steps.append("Check foreign income disclosures")

    if profile.has_insurance_expenses or profile.employment_status in {"employee", "both", "retired", "student", "unemployed"}:
        required_anlagen.append("Anlage Vorsorge")
        next_steps.append("Collect insurance certificates")

    if profile.donations_eur > 0:
        next_steps.append("Add donations under Sonderausgaben")

    if profile.has_haushaltsnahe or profile.has_handwerker:
        next_steps.append("Enter household-related expenses (Haushaltsnahe)")

    if profile.home_office_days > 0:
        next_steps.append("Enter home office days for deduction")

    if profile.commute_km > 0:
        next_steps.append("Enter commute details for Entfernungspauschale")

    return OnboardingResult(required_anlagen=required_anlagen, suggested_next_steps=next_steps)
