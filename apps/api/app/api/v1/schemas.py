from pydantic import BaseModel, Field


class OnboardingProfilePayload(BaseModel):
    employment_status: str = Field(pattern="^(employee|freelancer|both|retired|student|unemployed)$")
    marital_status: str = Field(default="single", pattern="^(single|married)$")
    has_children: bool = False
    num_children: int = Field(default=0, ge=0, le=20)
    rental_income: bool = False
    capital_gains: bool = False
    foreign_income: bool = False
    home_office_days: int = Field(default=0, ge=0, le=365)
    commute_km: int = Field(default=0, ge=0, le=1000)
    commute_days: int = Field(default=230, ge=0, le=365)
    donations_eur: float = Field(default=0.0, ge=0.0)
    has_insurance_expenses: bool = True
    has_haushaltsnahe: bool = False
    has_handwerker: bool = False
    church_member: bool = False
    bundesland: str = Field(default="Bayern")
    tax_class: int = Field(default=1, ge=1, le=6)


class CreateTaxReturnPayload(BaseModel):
    tax_year: int = Field(default=2025, ge=2000, le=2100)
    profile: OnboardingProfilePayload


class TaxEstimatePayload(BaseModel):
    taxable_income: float = Field(ge=0)
    filing_type: str = Field(default="single", pattern="^(single|joint)$")
    church_tax_rate: float = Field(default=0.0, ge=0.0, le=0.09)


class UploadDocumentPayload(BaseModel):
    file_name: str
    content_type: str = Field(default="application/octet-stream")


class UpdateSectionPayload(BaseModel):
    values: dict[str, object]


class RegisterPayload(BaseModel):
    email: str = Field(min_length=5)
    password: str = Field(min_length=6)
    full_name: str = Field(default="")


class LoginPayload(BaseModel):
    email: str
    password: str


class LlmSettingsPayload(BaseModel):
    provider: str = Field(pattern="^(openai|anthropic|google|mistral|cohere|custom)$")
    api_key: str = Field(min_length=1)
    model_name: str = Field(default="")


class AddExpensePayload(BaseModel):
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    amount_eur: float = Field(gt=0)
    date: str = Field(min_length=8)
    receipt_document_id: str = Field(default="")
