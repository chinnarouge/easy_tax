from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def _create_tax_return() -> str:
    res = client.post(
        "/api/v1/tax-returns",
        json={"tax_year": 2025, "profile": {"employment_status": "employee"}},
    )
    return res.json()["tax_return_id"]


def test_expense_categories() -> None:
    response = client.get("/api/v1/expense-categories")
    assert response.status_code == 200
    cats = response.json()["categories"]
    assert "work_equipment" in cats
    assert "training" in cats
    assert "medical" in cats
    assert "donations" in cats
    assert cats["work_equipment"]["form"] == "Anlage N"


def test_add_and_list_expenses() -> None:
    tr_id = _create_tax_return()

    add = client.post(
        f"/api/v1/tax-returns/{tr_id}/expenses",
        json={
            "category": "work_equipment",
            "description": "Laptop for work",
            "amount_eur": 1200.0,
            "date": "2025-03-15",
        },
    )
    assert add.status_code == 200
    body = add.json()
    assert body["category"] == "work_equipment"
    assert body["amount_eur"] == 1200.0
    assert body["form"] == "Anlage N"
    expense_id = body["expense_id"]

    add2 = client.post(
        f"/api/v1/tax-returns/{tr_id}/expenses",
        json={
            "category": "training",
            "description": "German language course",
            "amount_eur": 350.0,
            "date": "2025-06-01",
        },
    )
    assert add2.status_code == 200

    listing = client.get(f"/api/v1/tax-returns/{tr_id}/expenses")
    assert listing.status_code == 200
    data = listing.json()
    assert len(data["expenses"]) == 2
    assert data["grand_total"] == 1550.0
    assert data["totals_by_category"]["work_equipment"] == 1200.0
    assert data["totals_by_category"]["training"] == 350.0

    delete = client.delete(f"/api/v1/tax-returns/{tr_id}/expenses/{expense_id}")
    assert delete.status_code == 200

    listing2 = client.get(f"/api/v1/tax-returns/{tr_id}/expenses")
    assert len(listing2.json()["expenses"]) == 1
    assert listing2.json()["grand_total"] == 350.0


def test_expense_invalid_category() -> None:
    tr_id = _create_tax_return()
    response = client.post(
        f"/api/v1/tax-returns/{tr_id}/expenses",
        json={
            "category": "nonexistent_category",
            "description": "test",
            "amount_eur": 100.0,
            "date": "2025-01-01",
        },
    )
    assert response.status_code == 400


def test_expense_tax_return_not_found() -> None:
    response = client.post(
        "/api/v1/tax-returns/nonexistent/expenses",
        json={
            "category": "work_equipment",
            "description": "test",
            "amount_eur": 100.0,
            "date": "2025-01-01",
        },
    )
    assert response.status_code == 404


def test_document_list() -> None:
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_receipt.pdf", b"fake", "application/pdf")},
    )
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert len(response.json()["documents"]) >= 1
