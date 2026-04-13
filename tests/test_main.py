import json

import pytest
from pytest import approx

from public.main import (
    Financials,
    analyze_scenarios,
)


def test_calculate_monthly_payment():
    """Test standard mortgage payment calculation."""
    # $400,000 loan, 30 years, 6.5% rate
    # Google Sheets: =PMT(0.065/12, 360, 400000)
    assert Financials.calculate_pmt(400000, 6.5, 30) == approx(2528.27, abs=1e-2)


def test_calculate_remaining_balance():
    """Test remaining balance after a set number of payments."""
    # $400,000 loan, 30 years, 6.5% rate, after 5 years (60 months)
    # Google Sheets: =400000+CUMPRINC(0.065/12, 360, 400000, 1, 60, 0)
    balance = Financials.get_remaining_balance(400000, 6.5, 30, 60)
    assert balance == approx(374443.91, abs=1e-2)


def test_calculate_remaining_balance_at_end():
    """Balance at the end of the term should be zero."""
    balance = Financials.get_remaining_balance(400000, 6.5, 30, 360)
    assert balance == approx(0, abs=1)


@pytest.fixture
def baseline_params():
    """
    Default parameters for scenario tests.

    New cost/tax params are zeroed so that existing directional tests remain
    valid without recalibrating thresholds. Tests that specifically exercise
    the new features use their own copies with real values.
    """
    home_price = 500000
    down_payment_pct = 20

    return {
        "home_price": home_price,
        "down_payment_amount": home_price * (down_payment_pct / 100),
        "initial_rate": 6.5,
        "closing_costs_pct": 2.5,
        "current_rent": 1000,
        "home_price_growth": 3.5,
        "rent_growth": 3.0,
        "stock_growth": 8.0,
        "hoa_fees": 150,
        "property_tax_rate": 1.2,
        "insurance_rate": 0.5,
        # New cost/tax params — zeroed for directional tests
        "maintenance_rate": 0.0,
        "selling_costs_pct": 0.0,
        "federal_tax_bracket": 0.0,
        "standard_deduction": 29200,
        "capital_gains_rate": 0.0,
        "home_cg_exclusion": 500000,
        # Monte Carlo volatility
        "stock_volatility": 15,
        "home_volatility": 5,
        "rent_volatility": 5,
    }


def _run_analysis(params):
    """Helper to bridge dictionary params with the JSON API of main.py."""
    json_input = json.dumps(params)
    json_output = analyze_scenarios(json_input)
    return json.loads(json_output)


def test_buy_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor buying."""
    params = baseline_params.copy()
    params["home_price_growth"] = 6.0  # High appreciation
    params["rent_growth"] = 5.0        # High rent increases
    params["stock_growth"] = 4.0       # Lower stock returns

    result = _run_analysis(params)
    assert result["final_buy_net_worth"] > result["final_rent_net_worth"]


def test_rent_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor renting."""
    params = baseline_params.copy()
    params["home_price_growth"] = 1.0   # Very low appreciation
    params["property_tax_rate"] = 2.5   # High property taxes
    params["stock_growth"] = 10.0       # High stock returns

    result = _run_analysis(params)
    assert result["final_rent_net_worth"] > result["final_buy_net_worth"]


def test_edge_case(baseline_params):
    """
    With all growth and costs zeroed, buyer ends with exactly the home price
    and renter ends with exactly the down payment.
    """
    params = baseline_params.copy()
    params["home_price_growth"] = 0.0
    params["property_tax_rate"] = 0.0
    params["stock_growth"] = 0.0
    params["hoa_fees"] = 0.0
    params["insurance_rate"] = 0.0
    params["initial_rate"] = 0.0
    params["rent_growth"] = 0.0
    params["closing_costs_pct"] = 0.0
    # Zero out all new cost/tax params
    params["maintenance_rate"] = 0.0
    params["selling_costs_pct"] = 0.0
    params["federal_tax_bracket"] = 0.0
    params["capital_gains_rate"] = 0.0

    # Rent == mortgage payment so there is no monthly surplus to invest
    params["current_rent"] = 400000 / 360

    result = _run_analysis(params)
    assert result["final_buy_net_worth"] == approx(500000, abs=1e-2)
    assert result["final_rent_net_worth"] == approx(
        params["down_payment_amount"], abs=1e-2
    )


def test_refinancing_scenario(baseline_params):
    """A beneficial refinance should improve the buyer's outcome."""
    refi_params = baseline_params.copy()
    refi_params["current_rent"] = 2500  # ensure buyer has surplus cash to invest

    baseline_result = _run_analysis(refi_params)

    refi_params.update(
        {
            "refinance_year": 5,
            "refinance_rate": 3.0,
            "refinance_costs": 5000,
        }
    )
    refi_result = _run_analysis(refi_params)
    assert refi_result["final_buy_net_worth"] > baseline_result["final_buy_net_worth"]


def test_rental_upgrade_scenario(baseline_params):
    """Moving to a pricier rental should harm the renter's outcome."""
    baseline_result = _run_analysis(baseline_params)

    upgrade_params = baseline_params.copy()
    upgrade_params.update(
        {
            "move_to_larger_year": 7,
            "new_rent_today": 1.5 * baseline_params["current_rent"],  # 50% more
        }
    )
    upgrade_result = _run_analysis(upgrade_params)

    assert upgrade_result["final_rent_net_worth"] < baseline_result["final_rent_net_worth"]


def test_maintenance_costs_reduce_buyer_net_worth(baseline_params):
    """Higher maintenance rate should reduce the buyer's net worth."""
    params = baseline_params.copy()
    params["current_rent"] = 2500  # realistic rent so results are meaningful

    no_maint = params.copy()
    no_maint["maintenance_rate"] = 0.0

    with_maint = params.copy()
    with_maint["maintenance_rate"] = 2.0  # 2% of home value per year

    result_no = _run_analysis(no_maint)
    result_with = _run_analysis(with_maint)

    assert result_with["final_buy_net_worth"] < result_no["final_buy_net_worth"]


def test_selling_costs_reduce_buyer_net_worth(baseline_params):
    """Selling costs should be deducted from the buyer's reported net worth."""
    params = baseline_params.copy()
    params["current_rent"] = 2500

    no_sell = params.copy()
    no_sell["selling_costs_pct"] = 0.0

    with_sell = params.copy()
    with_sell["selling_costs_pct"] = 6.0

    result_no = _run_analysis(no_sell)
    result_with = _run_analysis(with_sell)

    assert result_with["final_buy_net_worth"] < result_no["final_buy_net_worth"]


def test_capital_gains_tax_reduces_both_scenarios(baseline_params):
    """Capital gains tax should reduce final net worth for both buyer and renter."""
    params = baseline_params.copy()
    params["current_rent"] = 2500

    no_cgt = params.copy()
    no_cgt["capital_gains_rate"] = 0.0
    no_cgt["selling_costs_pct"] = 0.0

    with_cgt = params.copy()
    with_cgt["capital_gains_rate"] = 15.0
    with_cgt["selling_costs_pct"] = 6.0

    result_no = _run_analysis(no_cgt)
    result_with = _run_analysis(with_cgt)

    assert result_with["final_buy_net_worth"] < result_no["final_buy_net_worth"]
    assert result_with["final_rent_net_worth"] < result_no["final_rent_net_worth"]


def test_mortgage_interest_deduction_benefits_buyer(baseline_params):
    """Mortgage interest deduction should improve the buyer's relative position.

    When buying costs exceed rent, MID reduces the effective buy cost, which means
    the renter invests a smaller monthly surplus. In a scenario where the buyer's
    cost already exceeds rent, the MID benefit shrinks the renter's investment
    advantage rather than directly boosting the buyer's investment account.
    In a scenario where rent exceeds buy cost, MID increases the buyer's monthly
    surplus to invest.
    """
    params = baseline_params.copy()
    # Use a high rent so the buyer has monthly surplus to invest
    # Buyer cost: ~$3386/mo (pmt + tax + insurance + HOA). Rent $4500 → buyer surplus.
    params["current_rent"] = 4500

    no_mid = params.copy()
    no_mid["federal_tax_bracket"] = 0.0

    with_mid = params.copy()
    with_mid["federal_tax_bracket"] = 32.0  # high bracket → meaningful deduction

    result_no = _run_analysis(no_mid)
    result_with = _run_analysis(with_mid)

    # MID reduces buyer's effective cost → larger monthly surplus to invest → higher NW
    assert result_with["final_buy_net_worth"] > result_no["final_buy_net_worth"]
