from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)


def test_onboarding_employee_with_children() -> None:
    response = client.post(
        "/api/v1/onboarding/profile",
        json={
            "employment_status": "employee",
            "marital_status": "single",
            "has_children": True,
            "num_children": 2,
            "rental_income": False,
            "capital_gains": True,
            "foreign_income": False,
            "home_office_days": 12,
            "commute_km": 18,
            "donations_eur": 50,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Mantelbogen" in body["required_anlagen"]
    assert "Anlage N" in body["required_anlagen"]
    assert "Anlage KAP" in body["required_anlagen"]
    assert "Anlage Kind" in body["required_anlagen"]
    assert "Anlage Vorsorge" in body["required_anlagen"]


def test_onboarding_freelancer() -> None:
    response = client.post(
        "/api/v1/onboarding/profile",
        json={
            "employment_status": "freelancer",
            "marital_status": "single",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Mantelbogen" in body["required_anlagen"]
    assert "Anlage N" not in body["required_anlagen"]


def test_onboarding_all_income_types() -> None:
    response = client.post(
        "/api/v1/onboarding/profile",
        json={
            "employment_status": "both",
            "marital_status": "married",
            "has_children": True,
            "rental_income": True,
            "capital_gains": True,
            "foreign_income": True,
            "home_office_days": 100,
            "commute_km": 50,
            "donations_eur": 500,
            "has_haushaltsnahe": True,
            "has_handwerker": True,
            "church_member": True,
            "bundesland": "Bayern",
            "tax_class": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()
    anlagen = body["required_anlagen"]
    assert "Anlage N" in anlagen
    assert "Anlage V" in anlagen
    assert "Anlage KAP" in anlagen
    assert "Anlage Kind" in anlagen
    assert "Anlage AUS" in anlagen
    assert "Anlage Vorsorge" in anlagen
    assert len(body["suggested_next_steps"]) >= 5


def test_onboarding_student() -> None:
    response = client.post(
        "/api/v1/onboarding/profile",
        json={"employment_status": "student", "marital_status": "single"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Mantelbogen" in body["required_anlagen"]
    assert "Anlage Vorsorge" in body["required_anlagen"]
    assert any("student" in s.lower() or "verlust" in s.lower() for s in body["suggested_next_steps"])


def test_onboarding_unemployed() -> None:
    response = client.post(
        "/api/v1/onboarding/profile",
        json={"employment_status": "unemployed", "marital_status": "single"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Mantelbogen" in body["required_anlagen"]
    assert "Anlage Vorsorge" in body["required_anlagen"]
    assert any("arbeitslosen" in s.lower() or "alg" in s.lower() for s in body["suggested_next_steps"])
