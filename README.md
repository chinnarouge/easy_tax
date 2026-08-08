# Easy Tax

AI-powered German income tax filing assistant with ELSTER field mapping. Guides you through creating a complete Einkommensteuererklarung — from onboarding to export.

## Features

- **Onboarding wizard** — 5-step profile setup that determines which tax forms (Anlagen) you need based on employment, income types, family status, and deductions
- **Tax return management** — create and edit returns with sections mapped to official German forms (Mantelbogen, Anlage N, V, KAP, Kind, Vorsorge, AUS)
- **Tax calculator** — 2025 German income tax formula (§32a EStG) with Splittingverfahren, solidarity surcharge, and church tax
- **Deduction suggestions** — rule-based engine for Entfernungspauschale, Homeoffice-Pauschale, donations, childcare, household services, and more
- **Expense tracking** — 24 categories (work equipment, training, software, medical, etc.), each mapped to a specific ELSTER form and line number
- **Document upload** — keyword-based classification for Lohnsteuerbescheinigung, receipts, insurance, rental, donation, and broker documents
- **ELSTER field catalog** — lookup internal field IDs mapped to official form/line numbers
- **Export** — download your return as CSV or PDF
- **LLM integration (BYOK)** — bring-your-own-key config for OpenAI, Anthropic, Google, Mistral, Cohere, or custom providers
- **Bilingual UI** — German / English toggle

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, FastAPI, SQLite, Pydantic |
| Frontend | React 18, TypeScript, Vite |
| Infra | Docker Compose |

## Run Locally

**Backend:**

```bash
uvicorn apps.api.app.main:app --reload
```

**Frontend:**

```bash
cd apps/web
npm install
npm run dev
```

**Docker:**

```bash
docker-compose up
```

API runs on `http://localhost:8000`, frontend on `http://localhost:5173`.

## API Endpoints

All under `/api/v1`:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login |
| GET | `/auth/me` | Current user |
| POST | `/onboarding/profile` | Determine required Anlagen |
| POST | `/tax-returns` | Create tax return |
| GET | `/tax-returns` | List returns |
| GET | `/tax-returns/{id}` | Get return |
| PATCH | `/tax-returns/{id}/section/{section}` | Update form section |
| GET | `/tax-returns/{id}/deduction-suggestions` | Deduction suggestions |
| POST | `/tax-returns/{id}/expenses` | Add expense |
| GET | `/tax-returns/{id}/expenses` | List expenses |
| DELETE | `/tax-returns/{id}/expenses/{eid}` | Delete expense |
| POST | `/calculator/estimate` | Estimate tax liability |
| GET | `/tax-returns/{id}/export/csv` | CSV export |
| POST | `/tax-returns/{id}/export/pdf` | PDF export |
| POST | `/documents/upload` | Upload document |
| GET | `/documents` | List documents |
| GET | `/elster/fields` | ELSTER field catalog |
| GET | `/elster/field/{field_id}` | Single field lookup |
| POST | `/llm/settings` | Save LLM config |
| GET | `/llm/settings` | Get LLM config |
| DELETE | `/llm/settings` | Remove LLM config |
| GET | `/health` | Health check |

## Project Structure

```
apps/
  api/          # FastAPI backend
    app/
      api/v1/   # Routes and schemas
      domain/   # Business logic (tax engine, expenses, deductions, onboarding, export)
    tests/      # API tests
  web/          # React frontend
    src/
data/           # Tax brackets, deduction rules, ELSTER field catalog (JSON)
```
