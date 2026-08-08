# SteuerHelfer: German Tax Filing Assistant

## Context

ELSTER (elster.de) is Germany's official electronic tax filing portal. While free, it provides **zero guidance** — no tips, no explanations, no suggestions. Users must already know what to declare and where. 87% of German tax filers get money back (average 1,172 EUR), but many miss deductions because the process is intimidating.

Existing tools (WISO 35.99 EUR, Taxfix 39.99 EUR, SteuerBot 39.99 EUR) provide guidance but none combine **AI document analysis + ELSTER field-by-field mapping + export**. This app fills that gap: an AI-powered assistant that analyzes uploaded documents, asks smart questions, suggests missed deductions, and tells users exactly where to enter each value in ELSTER (form name + line number).

**Tech choices**: Python/FastAPI backend, React/TypeScript frontend, Claude API for AI, PostgreSQL, monorepo.

---

## Architecture

### Monorepo Structure

```
steuerhelfer/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py       # Pydantic settings
│   │   │   ├── api/v1/         # Route handlers
│   │   │   ├── domain/         # Models + services + tax rules
│   │   │   │   ├── models/anlagen/   # One model per Anlage
│   │   │   │   ├── services/         # Business logic
│   │   │   │   └── tax_rules/        # German tax law engine per year
│   │   │   ├── elster/         # ELSTER field mapping + export
│   │   │   ├── ai/            # LLM + OCR pipeline
│   │   │   └── db/            # SQLAlchemy + repos
│   │   └── tests/
│   │
│   └── web/                    # React + TypeScript frontend
│       └── src/
│           ├── pages/          # Onboarding, Dashboard, TaxForm, Export
│           ├── components/     # UI kit + ElsterFieldHint, DeductionTip
│           ├── store/          # Zustand state
│           └── i18n/           # German + English
│
├── data/
│   ├── elster_field_catalog.json   # Field ID -> form/line mapping (per year)
│   ├── deduction_rules.json        # Limits and eligibility rules
│   └── tax_brackets_2025.json
│
└── docker-compose.yml
```

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/onboarding/profile` | Submit answers, get required Anlagen list |
| `POST /api/v1/tax-returns` | Create new return for a tax year |
| `PATCH /api/v1/tax-returns/{id}/section/{section}` | Update one Anlage |
| `POST /api/v1/documents/upload` | Upload doc for OCR + AI extraction |
| `GET /api/v1/tax-returns/{id}/deduction-suggestions` | AI recommendations |
| `POST /api/v1/calculator/estimate` | Real-time refund estimate |
| `POST /api/v1/tax-returns/{id}/export/pdf` | ELSTER mapping PDF |
| `GET /api/v1/elster/field/{field_id}` | Look up ELSTER form + line |

### Database Models

Separate table per Anlage (not a JSON blob) for schema validation and type safety:

- **User** + **UserProfile** (tax class, employment type, marital status, Bundesland)
- **TaxReturn** (year, status, required_anlagen, completion %)
- **PersonalData** (Mantelbogen core fields)
- **AnlageN** (employment income, all Werbungskosten fields — one per employer)
- **AnlageV** (rental income — one per property)
- **AnlageKAP** (capital gains)
- **AnlageKind** (one per child)
- **AnlageVorsorge** (insurance/pension)
- **Sonderausgaben**, **HaushaltsnaheAufwendungen**, **AussergewoehnlicheBelastungen**
- **Document** (uploaded file metadata, extracted data, confidence scores)
- **ElsterFieldMapping** (reference table seeded from catalog)

Sensitive fields (Steuernummer, IBAN, Steuer-ID) encrypted with AES-256 at rest.

### Frontend Stack

React 18 + TypeScript, Vite, Tailwind CSS + shadcn/ui, React Hook Form + Zod (validation), Zustand (cross-page state), react-i18next (DE/EN), TanStack Query (API).

---

## Core Feature: ELSTER Field Mapping

The differentiating feature. Every input field shows **exactly** where it goes in ELSTER.

### Field Catalog (`data/elster_field_catalog.json`)

```json
{
  "internal_id": "anlage_n.bruttolohn",
  "elster_form": "Anlage N",
  "elster_line": "Zeile 6",
  "label_de": "Bruttoarbeitslohn (lt. Nr. 3 der Lohnsteuerbescheinigung)",
  "label_en": "Gross salary (per item 3 of your Lohnsteuerbescheinigung)",
  "source_document": "lohnsteuerbescheinigung",
  "source_field_number": "3"
}
```

Built from ELSTER's official Amtliche Vordrucke + ERiC Schnittstellenbeschreibung. Versioned per tax year (forms shift line numbers annually). Consumed by both frontend (ElsterFieldHint component) and backend (export generation).

### ElsterFieldHint Component

For every input field, displays: *"This value goes into: Anlage N, Zeile 31 (Wege zwischen Wohnung und erster Taetigkeitsstatte)"*

---

## AI Pipeline

### Document Processing Flow

```
Upload (image/PDF)
  -> Document Classification (LLM: Lohnsteuerbescheinigung? Receipt? Insurance cert?)
  -> OCR (Google Cloud Vision, fallback Tesseract)
  -> Structured Data Extraction (Claude with document-specific prompt)
  -> Validation + Confidence Scores
  -> User Review & Confirmation
  -> Auto-fill form fields
```

### Deduction Optimizer

After form completion, Claude analyzes the user's profile against a rules database and suggests commonly missed deductions (Kontoführungsgebühren 16 EUR, Arbeitsmittel, Homeoffice-Pauschale, Gewerkschaftsbeiträge, etc.) with the exact ELSTER form + line to enter them.

### LLM Provider: Claude API (Sonnet)

Best German language understanding for tax documents. ~$0.05-0.15 per document processed.

---

## German Tax Rules Engine (Verified Research)

### Key Deductions & Limits (2025 Tax Year)

| Deduction | Limit | Form Location |
|-----------|-------|---------------|
| Grundfreibetrag | 12,096 EUR (single) / 24,192 EUR (joint) | Automatic |
| Arbeitnehmerpauschbetrag | 1,230 EUR | Anlage N |
| Homeoffice-Pauschale | 6 EUR/day, max 210 days = 1,260 EUR | Anlage N, Zeilen 61-62 |
| Entfernungspauschale | 0.30 EUR/km (first 20 km), 0.38 EUR/km (21st km+) | Anlage N, Zeile 31 |
| Haushaltsnahe Minijob | 20% credit, max 510 EUR | Anlage Haushaltsnahe |
| Haushaltsnahe Dienstleistungen | 20% credit, max 4,000 EUR | Anlage Haushaltsnahe |
| Handwerkerleistungen | 20% credit, max 1,200 EUR | Anlage Haushaltsnahe |
| Kinderbetreuung | 2/3 of costs, max 4,000 EUR/child | Anlage Kind |
| Sparerpauschbetrag | 1,000 EUR (single) / 2,000 EUR (joint) | Anlage KAP |
| Doppelte Haushaltsfuehrung | Rent up to 1,000 EUR/month | Anlage N-DH |

### Tax Calculation (section 32a EStG)

Implement the progressive tax formula: 0% up to Grundfreibetrag, then zones at 14%->42%->45%. Joint filing uses Splittingverfahren (halve income, compute, double). Add Solidaritätszuschlag (5.5% with Freigrenze) and Kirchensteuer (8% or 9% by Bundesland).

### Deadlines

- Standard: July 31 of following year (2025 returns due July 31, 2026)
- With Steuerberater: April 30 of year+2
- Late penalty: 0.25% of tax per month, min 25 EUR, max 25,000 EUR

---

## User Flow

```
Landing -> Register/Login
  -> Onboarding Wizard (5 steps):
     1. Personal Info (name, DOB, address, Steuer-ID)
     2. Employment Status (employee/freelancer/both/retired)
     3. Income Types (rental? capital gains? foreign?)
     4. Family (marital status, children, tax class)
     5. Quick Wins (home office? commute? donations? insurance?)
     => Determines required Anlagen
  -> Dashboard (progress tracker + refund estimate + upload area)
  -> Tax Form Wizard (section by section, each field with ElsterFieldHint)
  -> Document Upload (OCR extracts -> user confirms -> auto-fills)
  -> Review & Optimize (AI deduction suggestions)
  -> Export (PDF mapping guide / CSV / interactive ELSTER walkthrough)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- Monorepo setup (Turborepo), FastAPI scaffold, React + Vite + Tailwind
- Auth (JWT), User + UserProfile models, Alembic migrations, PostgreSQL
- Onboarding wizard (5 steps) with Anlagen determination logic
- i18n setup (German + English)
- Dashboard skeleton

### Phase 2: Core Tax Forms (Weeks 5-10)
- **Mantelbogen + Anlage N** first (most common case — covers 80% of users)
- ELSTER field catalog JSON for these forms
- ElsterFieldHint component
- Additional Anlagen: V (rental), KAP (capital), Kind, Vorsorge, Sonderausgaben, Haushaltsnahe
- Auto-save every 30 seconds + on section change
- Tax calculation engine (section 32a formula + Soli + Kirchensteuer)
- Real-time refund estimate on dashboard

### Phase 3: AI Features (Weeks 11-14)
- Document upload with Google Cloud Vision OCR
- LLM document classification + structured extraction
- Lohnsteuerbescheinigung extraction (map fields 3-28 to form fields)
- Receipt + insurance certificate extraction
- Extracted data review UI with confidence scores
- AI deduction optimizer (profile analysis + missed deduction suggestions)

### Phase 4: Export + Polish (Weeks 15-18)
- PDF export: professional document with ELSTER form/line mapping per field
- CSV export: field-by-field for manual ELSTER entry
- Interactive ELSTER entry guide (step-by-step walkthrough)
- End-to-end testing with sample tax scenarios
- Accessibility (WCAG 2.1 AA), performance, error handling polish

### Phase 5: ERiC Integration (Weeks 19-24, optional)
- Register as ELSTER Hersteller (developer) at elster.de
- Obtain Hersteller-ID + test certificates
- Integrate ERiC C library via Python ctypes
- Generate validated ELSTER XML from field catalog
- Test with ELSTER test environment

---

## Key Technical Decisions

1. **No ERiC in MVP** — Registration takes weeks, C library adds complexity. PDF/CSV export delivers value immediately.
2. **Claude API for LLM** — Superior German tax document understanding vs. smaller models. Cost: ~$0.05-0.15/document.
3. **Google Cloud Vision for OCR** — Best accuracy on German government documents. Tesseract fallback for dev.
4. **Separate DB tables per Anlage** — Schema validation + type safety over a JSON blob.
5. **JSON field catalog** — Versioned per tax year, consumed by both frontend and backend. Single source of truth.
6. **Zustand + React Hook Form** — Best performance for 50+ field forms; Zustand for cross-page state.

## Verification Plan

1. **Unit tests**: Tax calculation engine against known scenarios (single employee, married with children, freelancer)
2. **Integration tests**: Full onboarding -> form fill -> export flow
3. **AI accuracy tests**: Process 10+ real Lohnsteuerbescheinigungen, measure field extraction accuracy
4. **ELSTER mapping validation**: Cross-check catalog against official Amtliche Vordrucke PDFs
5. **Manual QA**: Complete a real tax filing using the app's PDF guide + actual ELSTER portal
6. **Run dev servers**: `uvicorn app.main:app --reload` (backend) + `npm run dev` (frontend), test the full user flow in browser
