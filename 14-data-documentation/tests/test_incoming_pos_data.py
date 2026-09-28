"""Consumer-side tests: run them on every new batch of POS data before training."""

import pandas as pd
import pytest

import inventory_data as d
from pos_checks import DailySales, distribution_problems

UNITS = d.products().set_index("id").unit


def month(sales: pd.DataFrame, start: str) -> pd.DataFrame:
    end = pd.Timestamp(start) + pd.offsets.MonthEnd(0)
    return sales[sales.date.between(start, end) & (sales.store_id <= 8)].reset_index(drop=True)


@pytest.fixture(scope="module")
def drift_sales() -> pd.DataFrame:
    return d.drift_sales()


def test_clean_batch_has_the_expected_structure():
    DailySales.validate(month(d.sales(), "2025-09-01"), lazy=True)


def test_clean_batch_has_the_expected_distribution():
    sales = d.sales()
    assert (
        distribution_problems(month(sales, "2025-09-01"), month(sales, "2024-09-01"), UNITS) == []
    )


def test_lb_switch_passes_the_schema_but_not_the_distribution_check(drift_sales):
    batch = month(drift_sales, "2025-09-01")
    DailySales.validate(batch, lazy=True)  # the schema does not see the unit change
    problems = distribution_problems(batch, month(drift_sales, "2024-09-01"), UNITS)
    assert any(p.startswith("store 7: mean kg") for p in problems)
    assert any(p.startswith("store 8: mean kg") for p in problems)


def test_missing_store_days_are_found():
    sales = d.sales(dirty=True)
    batch = month(sales, "2025-02-01")
    problems = distribution_problems(batch, month(sales, "2024-02-01"), UNITS)
    assert any(p.startswith("store 6: only") for p in problems)


def test_duplicate_upload_breaks_the_structure():
    batch = month(d.sales(dirty=True), "2025-05-01")
    with pytest.raises(Exception, match="unique|duplicate"):
        DailySales.validate(batch, lazy=True)
