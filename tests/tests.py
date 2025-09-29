import pytest
from main import calculate_monthly_payment, calculate_remaining_balance, rent_vs_buy_analysis

# Use pytest.approx for floating point comparisons
from pytest import approx

# --- 1. Tests for Helper Functions ---


def test_calculate_monthly_payment():
    """Test standard mortgage payment calculation."""
    # $400,000 loan, 30 years, 6.5% rate
    # can confirm this number with the Google Sheets command:
    # =PMT(0.065/12, 360, 400000)
    assert calculate_monthly_payment(
        400000, 0.065, 30) == approx(2528.27, abs=1e-2)


def test_calculate_remaining_balance():
    """Test remaining balance after a set number of payments."""
    # $400,000 loan, 30 years, 6.5% rate, after 5 years (60 months)
    # confirm with Google Sheets command:
    # =400000+CUMPRINC(0.065/12, 360, 400000, 1, 60, 0)
    balance = calculate_remaining_balance(400000, 0.065, 30, 60)
    assert balance == approx(374443.91, abs=1e-2)


def test_calculate_remaining_balance_at_end():
    """Test balance at the end of the term should be 0."""
    # 30 years * 12 months = 360 payments
    balance = calculate_remaining_balance(400000, 0.065, 30, 360)
    assert balance == approx(0, abs=1)


# --- 2. Tests for Main Analysis Function ---

@pytest.fixture
def baseline_params():
    """A pytest fixture to provide a default set of parameters for tests."""
    return {
        'home_price': 500000,
        'down_payment_pct': 20,
        'initial_rate': 6.5,
        'closing_costs': 12500,
        'current_rent': 1000,
        'home_price_growth': 3.5,
        'rent_growth': 3.0,
        'stock_growth': 8.0,
        'hoa_fees': 150,
        'property_tax_rate': 1.2,
        'insurance_rate': 0.5,
    }


def test_baseline_scenario(baseline_params):
    """Test the main function with a standard, neutral set of inputs."""
    result = rent_vs_buy_analysis(baseline_params)

    # Data integrity checks
    assert len(result['years']) == 31  # Years 0 through 30
    assert len(result['buy_net_worth']) == 31
    assert len(result['rent_net_worth']) == 31
    assert result['final_buy_net_worth'] == approx(3_276_849, abs=1)
    assert result['final_rent_net_worth'] == approx(2_530_314, abs=1)


def test_buy_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor buying."""
    params = baseline_params.copy()
    params['home_price_growth'] = 6.0  # High appreciation
    params['rent_growth'] = 5.0        # High rent increases
    params['stock_growth'] = 4.0       # Lower stock returns

    result = rent_vs_buy_analysis(params)
    assert result['final_buy_net_worth'] > result['final_rent_net_worth']


def test_rent_is_better_scenario(baseline_params):
    """Test a scenario designed to strongly favor renting."""
    params = baseline_params.copy()
    params['home_price_growth'] = 1.0  # Very low appreciation
    params['property_tax_rate'] = 2.5  # High property taxes
    params['stock_growth'] = 10.0      # High stock returns

    result = rent_vs_buy_analysis(params)
    assert result['final_rent_net_worth'] > result['final_buy_net_worth']

    
def test_edge_case(baseline_params):
    """Test a scenario designed to strongly favor renting."""
    params = baseline_params.copy()
    params['home_price_growth'] = 0.
    params['property_tax_rate'] = 0.
    params['stock_growth'] = 0.
    params['hoa_fees'] = 0.
    params['insurance_rate'] = 0.
    params['initial_rate'] = 0.
    params['home_price_growth'] = 0.
    params['rent_growth'] = 0.

    result = rent_vs_buy_analysis(params)
    print('result = ', result)
    assert result['final_buy_net_worth'] == approx(500000, abs = 1e-2)
    assert result['yearly_details'][-1]['rent_paid'] == params['current_rent']*12


def test_refinancing_scenario(baseline_params):
    """Test that adding a beneficial refinance improves the buyer's outcome."""
    # Run baseline first
    baseline_result = rent_vs_buy_analysis(baseline_params)

    # Now run with refinancing
    refi_params = baseline_params.copy()
    refi_params.update({
        'refinance_year': 5,
        'refinance_rate': 1.5,
        'refinance_costs': 5000,
    })
    refi_result = rent_vs_buy_analysis(refi_params)

    # A good refinance should increase the buyer's final net worth
    assert refi_result['final_buy_net_worth'] > baseline_result['final_buy_net_worth']
    # Rent net worth should be different as the monthly cost comparison changes
    assert refi_result['final_rent_net_worth'] != baseline_result['final_rent_net_worth']


def test_rental_upgrade_scenario(baseline_params):
    """Test that upgrading to a larger rental harms the renter's outcome."""
    # Run baseline first
    baseline_result = rent_vs_buy_analysis(baseline_params)

    # Now run with the rental upgrade
    upgrade_params = baseline_params.copy()
    upgrade_params.update({
        'move_to_larger_year': 7,
        'larger_rent_multiplier': 1.5,  # 50% more expensive
    })
    upgrade_result = rent_vs_buy_analysis(upgrade_params)

    # A rental upgrade should decrease the renter's final net worth
    assert upgrade_result['final_rent_net_worth'] < baseline_result['final_rent_net_worth']
    # Buyer's net worth should improve as the cost comparison becomes more favorable
    assert upgrade_result['final_buy_net_worth'] > baseline_result['final_buy_net_worth']
