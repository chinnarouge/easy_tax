from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import Response

from apps.api.app.api.v1.schemas import (
    AddExpensePayload,
    CreateTaxReturnPayload,
    LlmSettingsPayload,
    LoginPayload,
    OnboardingProfilePayload,
    RegisterPayload,
    TaxEstimatePayload,
    UpdateSectionPayload,
    UploadDocumentPayload,
)
from apps.api.app.auth import (
    authenticate_user,
    create_token,
    get_current_user,
    register_user,
)
from apps.api.app.config import settings
from apps.api.app.domain.deductions import suggest_deductions
from apps.api.app.domain.documents import upload_document, list_documents
from apps.api.app.domain.expenses import (
    EXPENSE_CATEGORIES,
    add_expense,
    delete_expense,
    get_expense_totals,
    list_expenses,
)
from apps.api.app.domain.exporting import build_csv_export, build_pdf_export
from apps.api.app.domain.field_catalog import get_field_mapping, load_field_catalog
from apps.api.app.domain.onboarding import OnboardingProfile, determine_required_anlagen
from apps.api.app.domain.store import (
    calculate_completion,
    create_tax_return,
    get_tax_return,
    list_tax_returns,
    update_tax_return_section,
)
from apps.api.app.domain.llm_settings import (
    SUPPORTED_PROVIDERS,
    delete_llm_config,
    get_llm_config,
    save_llm_config,
)
from apps.api.app.domain.tax_engine import TaxEstimateInput, estimate_tax

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


# ── Auth ─────────────────────────────────────────────────────────────

@router.post("/auth/register")
def auth_register(payload: RegisterPayload) -> dict[str, object]:
    try:
        user = register_user(payload.email, payload.password, payload.full_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    token = create_token(user.user_id)
    return {"user_id": user.user_id, "email": user.email, "token": token}


@router.post("/auth/login")
def auth_login(payload: LoginPayload) -> dict[str, object]:
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user.user_id)
    return {"user_id": user.user_id, "email": user.email, "token": token}


@router.get("/auth/me")
def auth_me(request: Request) -> dict[str, object]:
    user = get_current_user(request)
    return {"user_id": user.user_id, "email": user.email, "full_name": user.full_name}


# ── LLM settings ─────────────────────────────────────────────────────

@router.get("/llm/providers")
def llm_providers() -> dict[str, object]:
    return {"providers": SUPPORTED_PROVIDERS}


@router.post("/llm/settings")
def llm_save(payload: LlmSettingsPayload, request: Request) -> dict[str, object]:
    user = get_current_user(request)
    config = save_llm_config(user.user_id, payload.provider, payload.api_key, payload.model_name)
    return {
        "provider": config.provider,
        "model_name": config.model_name,
        "active": config.active,
        "key_preview": config.api_key[:4] + "..." + config.api_key[-4:] if len(config.api_key) > 8 else "***",
    }


@router.get("/llm/settings")
def llm_get(request: Request) -> dict[str, object]:
    user = get_current_user(request)
    config = get_llm_config(user.user_id)
    if config is None:
        return {"configured": False}
    return {
        "configured": True,
        "provider": config.provider,
        "model_name": config.model_name,
        "active": config.active,
        "key_preview": config.api_key[:4] + "..." + config.api_key[-4:] if len(config.api_key) > 8 else "***",
    }


@router.delete("/llm/settings")
def llm_delete(request: Request) -> dict[str, object]:
    user = get_current_user(request)
    deleted = delete_llm_config(user.user_id)
    return {"deleted": deleted}


# ── Onboarding ───────────────────────────────────────────────────────

@router.post("/onboarding/profile")
def onboarding_profile(payload: OnboardingProfilePayload) -> dict[str, object]:
    profile = OnboardingProfile(**payload.model_dump())
    result = determine_required_anlagen(profile)
    return {
        "required_anlagen": result.required_anlagen,
        "suggested_next_steps": result.suggested_next_steps,
    }


# ── Tax returns ──────────────────────────────────────────────────────

@router.post("/tax-returns")
def create_return(payload: CreateTaxReturnPayload) -> dict[str, object]:
    profile = OnboardingProfile(**payload.profile.model_dump())
    onboarding_result = determine_required_anlagen(profile)
    record = create_tax_return(payload.tax_year, profile, onboarding_result.required_anlagen)
    return {
        "tax_return_id": record.tax_return_id,
        "tax_year": record.tax_year,
        "status": record.status,
        "required_anlagen": record.required_anlagen,
        "completion": calculate_completion(record),
    }


@router.get("/tax-returns")
def list_returns() -> dict[str, object]:
    records = list_tax_returns()
    return {
        "tax_returns": [
            {
                "tax_return_id": r.tax_return_id,
                "tax_year": r.tax_year,
                "status": r.status,
                "completion": calculate_completion(r),
            }
            for r in records
        ]
    }


@router.get("/tax-returns/{tax_return_id}")
def get_return(tax_return_id: str) -> dict[str, object]:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    return {
        "tax_return_id": record.tax_return_id,
        "tax_year": record.tax_year,
        "status": record.status,
        "required_anlagen": record.required_anlagen,
        "sections": record.sections,
        "completion": calculate_completion(record),
    }


@router.patch("/tax-returns/{tax_return_id}/section/{section}")
def update_section(tax_return_id: str, section: str, payload: UpdateSectionPayload) -> dict[str, object]:
    record = update_tax_return_section(tax_return_id, section, payload.values)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    return {
        "tax_return_id": record.tax_return_id,
        "section": section,
        "completion": calculate_completion(record),
        "sections": record.sections,
    }


# ── Deductions ───────────────────────────────────────────────────────

@router.get("/tax-returns/{tax_return_id}/deduction-suggestions")
def deduction_suggestions(tax_return_id: str) -> dict[str, object]:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    suggestions = suggest_deductions(record.profile)
    return {
        "tax_return_id": tax_return_id,
        "suggestions": [
            {
                "title": s.title,
                "amount_eur": s.amount_eur,
                "form": s.form,
                "line": s.line,
                "reason": s.reason,
                "field_id": s.field_id,
            }
            for s in suggestions
        ],
    }


# ── ELSTER catalog ───────────────────────────────────────────────────

@router.get("/elster/fields")
def elster_fields() -> list[dict[str, object]]:
    return load_field_catalog()


@router.get("/elster/field/{field_id}")
def elster_field(field_id: str) -> dict[str, object]:
    mapping = get_field_mapping(field_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    return mapping


# ── Documents ────────────────────────────────────────────────────────

@router.post("/documents/upload")
async def document_upload(file: UploadFile = File(...)) -> dict[str, object]:
    contents = await file.read()
    record = upload_document(
        file_name=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
    )
    return {
        "document_id": record.document_id,
        "file_name": record.file_name,
        "content_type": record.content_type,
        "classification": record.classification,
        "extracted_fields": record.extracted_fields,
        "confidence": record.confidence,
        "created_at": record.created_at,
    }


@router.get("/documents")
def documents_list() -> dict[str, object]:
    docs = list_documents()
    return {
        "documents": [
            {
                "document_id": d.document_id,
                "file_name": d.file_name,
                "content_type": d.content_type,
                "classification": d.classification,
                "extracted_fields": d.extracted_fields,
                "confidence": d.confidence,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }


# ── Expenses ─────────────────────────────────────────────────────────

@router.get("/expense-categories")
def expense_categories_list() -> dict[str, object]:
    return {"categories": EXPENSE_CATEGORIES}


@router.post("/tax-returns/{tax_return_id}/expenses")
def expense_add(tax_return_id: str, payload: AddExpensePayload) -> dict[str, object]:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    if payload.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown category: {payload.category}")
    expense = add_expense(
        tax_return_id=tax_return_id,
        category=payload.category,
        description=payload.description,
        amount_eur=payload.amount_eur,
        date=payload.date,
        receipt_document_id=payload.receipt_document_id or None,
    )
    cat = EXPENSE_CATEGORIES[payload.category]
    return {
        "expense_id": expense.expense_id,
        "category": expense.category,
        "category_label": cat["label_de"],
        "description": expense.description,
        "amount_eur": expense.amount_eur,
        "date": expense.date,
        "form": cat["form"],
        "line": cat["line"],
        "receipt_document_id": expense.receipt_document_id,
    }


@router.get("/tax-returns/{tax_return_id}/expenses")
def expense_list(tax_return_id: str) -> dict[str, object]:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    items = list_expenses(tax_return_id)
    totals = get_expense_totals(tax_return_id)
    grand_total = sum(totals.values())
    return {
        "expenses": [
            {
                "expense_id": e.expense_id,
                "category": e.category,
                "category_label": EXPENSE_CATEGORIES.get(e.category, {}).get("label_de", e.category),
                "description": e.description,
                "amount_eur": e.amount_eur,
                "date": e.date,
                "form": EXPENSE_CATEGORIES.get(e.category, {}).get("form", ""),
                "line": EXPENSE_CATEGORIES.get(e.category, {}).get("line", ""),
                "receipt_document_id": e.receipt_document_id,
            }
            for e in items
        ],
        "totals_by_category": totals,
        "grand_total": grand_total,
    }


@router.delete("/tax-returns/{tax_return_id}/expenses/{expense_id}")
def expense_delete(tax_return_id: str, expense_id: str) -> dict[str, object]:
    deleted = delete_expense(tax_return_id, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"deleted": True}


# ── Calculator ───────────────────────────────────────────────────────

@router.post("/calculator/estimate")
def calculator_estimate(payload: TaxEstimatePayload) -> dict[str, object]:
    result = estimate_tax(
        TaxEstimateInput(
            taxable_income=payload.taxable_income,
            filing_type=payload.filing_type,
            church_tax_rate=payload.church_tax_rate,
        )
    )
    return {
        "taxable_income": payload.taxable_income,
        "filing_type": payload.filing_type,
        "income_tax": result.income_tax,
        "solidarity_surcharge": result.solidarity_surcharge,
        "church_tax": result.church_tax,
        "total_tax": result.total_tax,
        "effective_rate": result.effective_rate,
        "tax_year": settings.tax_year,
    }


# ── Export ────────────────────────────────────────────────────────────

@router.get("/tax-returns/{tax_return_id}/export/csv")
def export_csv(tax_return_id: str) -> Response:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    content = build_csv_export(record)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="steuerhelfer-{tax_return_id}.csv"'},
    )


@router.post("/tax-returns/{tax_return_id}/export/pdf")
def export_pdf(tax_return_id: str) -> Response:
    record = get_tax_return(tax_return_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tax return not found")
    content = build_pdf_export(record)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="steuerhelfer-{tax_return_id}.pdf"'},
    )
