from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)


def test_document_upload_lohnsteuer() -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("lohnsteuerbescheinigung_2025.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == "lohnsteuerbescheinigung"
    assert body["confidence"] > 0.8
    assert "bruttolohn" in body["extracted_fields"]


def test_document_upload_receipt() -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("beleg_arbeitsmittel.jpg", b"fake image", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["classification"] == "receipt"


def test_document_upload_insurance() -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("krankenversicherung_nachweis.pdf", b"fake pdf", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["classification"] == "insurance_certificate"


def test_document_upload_unknown() -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("random.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["classification"] == "unknown"
    assert response.json()["confidence"] < 0.5


def test_full_tax_return_flow() -> None:
    create = client.post(
        "/api/v1/tax-returns",
        json={
            "tax_year": 2025,
            "profile": {
                "employment_status": "employee",
                "marital_status": "married",
                "has_children": True,
                "num_children": 1,
                "rental_income": False,
                "capital_gains": True,
                "foreign_income": False,
                "home_office_days": 100,
                "commute_km": 25,
                "donations_eur": 200,
                "church_member": True,
            },
        },
    )
    assert create.status_code == 200
    tax_return_id = create.json()["tax_return_id"]
    assert "Anlage N" in create.json()["required_anlagen"]
    assert "Anlage Kind" in create.json()["required_anlagen"]

    # Get the return
    get = client.get(f"/api/v1/tax-returns/{tax_return_id}")
    assert get.status_code == 200
    assert get.json()["completion"] == 0

    # Update Anlage N
    patch = client.patch(
        f"/api/v1/tax-returns/{tax_return_id}/section/Anlage N",
        json={"values": {"bruttolohn": 55000, "home_office_days": 100, "commute_km": 25}},
    )
    assert patch.status_code == 200
    assert patch.json()["completion"] > 0

    # Update Mantelbogen
    client.patch(
        f"/api/v1/tax-returns/{tax_return_id}/section/Mantelbogen",
        json={"values": {"full_name": "Max Mustermann", "iban": "DE89370400440532013000"}},
    )

    # Get deduction suggestions
    deductions = client.get(f"/api/v1/tax-returns/{tax_return_id}/deduction-suggestions")
    assert deductions.status_code == 200
    titles = [s["title"] for s in deductions.json()["suggestions"]]
    assert any("Entfernungspauschale" in t for t in titles)
    assert any("Homeoffice" in t for t in titles)
    assert any("Spenden" in t or "donat" in t.lower() for t in titles)

    # CSV export
    csv = client.get(f"/api/v1/tax-returns/{tax_return_id}/export/csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert "bruttolohn" in csv.text

    # PDF export
    pdf = client.post(f"/api/v1/tax-returns/{tax_return_id}/export/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")


def test_elster_field_lookup() -> None:
    response = client.get("/api/v1/elster/field/anlage_n.bruttolohn")
    assert response.status_code == 200
    body = response.json()
    assert body["elster_form"] == "Anlage N"
    assert "Zeile" in body["elster_line"]


def test_elster_fields_list() -> None:
    response = client.get("/api/v1/elster/fields")
    assert response.status_code == 200
    fields = response.json()
    assert len(fields) >= 30


def test_elster_field_not_found() -> None:
    response = client.get("/api/v1/elster/field/nonexistent")
    assert response.status_code == 404


def test_list_tax_returns() -> None:
    client.post(
        "/api/v1/tax-returns",
        json={"tax_year": 2025, "profile": {"employment_status": "employee"}},
    )
    response = client.get("/api/v1/tax-returns")
    assert response.status_code == 200
    assert len(response.json()["tax_returns"]) >= 1


def test_tax_return_not_found() -> None:
    response = client.get("/api/v1/tax-returns/nonexistent-id")
    assert response.status_code == 404
