from fastapi.testclient import TestClient

from apps.api.app.domain.tax_engine import TaxEstimateInput, estimate_tax
from apps.api.app.main import app

client = TestClient(app)


def test_zero_income() -> None:
    result = estimate_tax(TaxEstimateInput(taxable_income=0))
    assert result.income_tax == 0
    assert result.total_tax == 0


def test_below_grundfreibetrag() -> None:
    result = estimate_tax(TaxEstimateInput(taxable_income=12000))
    assert result.income_tax == 0


def test_single_50k() -> None:
    result = estimate_tax(TaxEstimateInput(taxable_income=50000, filing_type="single", church_tax_rate=0.09))
    assert result.income_tax > 0
    assert result.total_tax > result.income_tax
    assert result.effective_rate > 0


def test_joint_filing_lower_tax() -> None:
    """Joint filing with Splittingverfahren should yield lower tax than single for the same income."""
    single = estimate_tax(TaxEstimateInput(taxable_income=80000, filing_type="single"))
    joint = estimate_tax(TaxEstimateInput(taxable_income=80000, filing_type="joint"))
    assert joint.income_tax < single.income_tax
    assert joint.total_tax < single.total_tax


def test_joint_filing_matches_splitting() -> None:
    """Joint tax should be exactly 2 * tax(income/2)."""
    income = 100000
    joint = estimate_tax(TaxEstimateInput(taxable_income=income, filing_type="joint"))
    half = estimate_tax(TaxEstimateInput(taxable_income=income / 2, filing_type="single"))
    assert abs(joint.income_tax - half.income_tax * 2) < 0.02


def test_soli_below_threshold() -> None:
    result = estimate_tax(TaxEstimateInput(taxable_income=30000))
    assert result.solidarity_surcharge == 0


def test_high_income() -> None:
    result = estimate_tax(TaxEstimateInput(taxable_income=300000))
    assert result.income_tax > 100000


def test_estimate_api() -> None:
    response = client.post(
        "/api/v1/calculator/estimate",
        json={"taxable_income": 50000, "filing_type": "single", "church_tax_rate": 0.09},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tax_year"] == 2025
    assert body["total_tax"] >= body["income_tax"]
    assert "effective_rate" in body


def test_estimate_joint_api() -> None:
    response = client.post(
        "/api/v1/calculator/estimate",
        json={"taxable_income": 80000, "filing_type": "joint", "church_tax_rate": 0.0},
    )
    assert response.status_code == 200
    assert response.json()["filing_type"] == "joint"
