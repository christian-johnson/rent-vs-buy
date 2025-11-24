import pytest
import json
from pytest import approx

# Import from the provided main.py structure
from public.main import (
    Financials,
    analyze_scenarios,
)


def test_calculate_monthly_payment():
    """Test standard mortgage payment calculation."""
    # $400,000 loan, 30 years, 6.5% rate
    # Note: Financials.calculate_pmt expects rate as a percentage (6.5), not decimal (0.065)
    # because it performs /100 internally.

    # Google Sheets command confirmation:
    # =PMT(0.065/12, 360, 400000)
    assert Financials.calculate_pmt(400000, 6.5, 30) == approx(2528.27, abs=1e-2)


def test_calculate_remaining_balance():
    """Test remaining balance after a set number of payments."""
    # $400,000 loan, 30 years, 6.5% rate, after 5 years (60 months)
    # Google Sheets command confirmation:
    # =400000+CUMPRINC(0.065/12, 360, 400000, 1, 60, 0)
    balance = Financials.get_remaining_balance(400000, 6.5, 30, 60)
    assert balance == approx(374443.91, abs=1e-2)


def test_calculate_remaining_balance_at_end():
    """Test balance at the end of the term should be 0."""
    # 30 years * 12 months = 360 payments
    balance = Financials.get_remaining_balance(400000, 6.5, 30, 360)
    assert balance == approx(0, abs=1)


@pytest.fixture
def baseline_params():
    """
    A pytest fixture to provide a default set of parameters for tests.
    Updated to match keys expected by main.py run_projection.
    """
    home_price = 500000
    down_payment_pct = 20

    return {
        "home_price": home_price,
        # main.py expects amount, not percentage
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
        # Defaults required for stochastic parts
        "stock_volatility": 15,
        "home_volatility": 5,
        "rent_volatility": 5,
    }


def _run_analysis(params):
    """Helper to bridge dictionary params with the JSON API of main.py"""
    json_input = json.dumps(params)
    json_output = analyze_scenarios(json_input)
    return json.loads(json_output)


def test_buy_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor buying."""
    params = baseline_params.copy()
    params["home_price_growth"] = 6.0  # High appreciation
    params["rent_growth"] = 5.0  # High rent increases
    params["stock_growth"] = 4.0  # Lower stock returns

    result = _run_analysis(params)
    assert result["final_buy_net_worth"] > result["final_rent_net_worth"]


def test_rent_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor renting."""
    params = baseline_params.copy()
    params["home_price_growth"] = 1.0  # Very low appreciation
    params["property_tax_rate"] = 2.5  # High property taxes
    params["stock_growth"] = 10.0  # High stock returns

    result = _run_analysis(params)
    assert result["final_rent_net_worth"] > result["final_buy_net_worth"]


def test_edge_case(baseline_params):
    """
    Test a scenario where growth and costs are zeroed out.
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

    # Ensure we pass 0 down payment amount if we want pure comparison,
    # or keep it to test equity. Let's keep standard fixture down payment.
    # Note: main.py has hardcoded selling_cost_pct = 0.06 (6%)

    result = _run_analysis(params)

    # The home value remains 500,000.
    # The loan is paid off (remaining 0).
    # Selling costs are 6% of 500,000 = 30,000.
    # Expected Net Worth = 500,000 - 30,000 = 470,000.
    expected_nw = 500000 * (1 - 0.06)

    assert result["final_buy_net_worth"] == approx(expected_nw, abs=1e-2)

    # Note: The new main.py yearly_details does not output 'rent_paid' explicitly.
    # We verify correct flow by ensuring rent net worth calculated correctly:
    # Rent net worth should consist of the initial downpayment (100k) sitting in cash
    # (0% growth) minus rent paid?
    # Actually, logic is:
    # 1. Rent NW starts with Downpayment (100k).
    # 2. Cost Diff = Rent (1000) - Buy Cost (P&I only, since tax/ins/hoa/rate=0).
    #    Buy Cost = 400k / 360 months = 1111.11
    #    Diff = 1000 - 1111.11 = -111.11
    #    Since Buy > Rent, Renter adds 0 to savings. Buyer adds 0 to savings.
    #    The renter actually LOSES the difference? The current logic is:
    #    buy_investments += max(0, diff); rent_investments += max(0, -diff)
    #    So investments never decrease due to monthly flow, they just grow or stay flat.
    #    Rent NW = 100k.
    assert result["final_rent_net_worth"] == approx(
        params["down_payment_amount"], abs=1e-2
    )


def test_refinancing_scenario(baseline_params):
    """Test that adding a beneficial refinance improves the buyer's outcome."""
    # Run baseline first
    baseline_result = _run_analysis(baseline_params)

    # Now run with refinancing
    refi_params = baseline_params.copy()
    refi_params.update(
        {
            "refinance_year": 5,
            "refinance_rate": 0.1,
            "refinance_costs": 500,
        }
    )
    refi_result = _run_analysis(refi_params)

    # A good refinance should increase the buyer's final net worth
    assert refi_result["final_buy_net_worth"] > baseline_result["final_buy_net_worth"]

    # Rent net worth should be same or different?
    # Renter net worth is affected by 'opportunity cost'.
    # If mortgage drops, Buyer cost drops. Rent - Buy Diff increases.
    # Buyer saves more. Renter logic is unaffected directly,
    # UNLESS Rent < Buy initially.
    assert refi_result["final_buy_net_worth"] != baseline_result["final_buy_net_worth"]


def test_rental_upgrade_scenario(baseline_params):
    """Test that upgrading to a larger rental harms the renter's outcome."""
    # Run baseline first
    baseline_result = _run_analysis(baseline_params)

    # Now run with the rental upgrade
    upgrade_params = baseline_params.copy()
    upgrade_params.update(
        {
            "move_to_larger_year": 7,
            # 50% more expensive
            "new_rent_today": 1.5 * baseline_params["current_rent"],
        }
    )
    upgrade_result = _run_analysis(upgrade_params)

    # A rental upgrade should decrease the renter's final net worth
    # because they are spending more on rent, leaving less (or none) to invest.
    assert (
        upgrade_result["final_rent_net_worth"] < baseline_result["final_rent_net_worth"]
    )
