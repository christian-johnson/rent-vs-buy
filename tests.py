from main import calculate_monthly_payment, calculate_remaining_balance, rent_vs_buy_analysis


def test_monthly_payment():
    """Test mortgage payment calculation"""
    # Test case: $400k loan at 6% for 30 years
    # Expected payment: ~$2,398
    payment = calculate_monthly_payment(400000, 0.06, 30)
    expected = 2398.20  # approximately
    assert abs(payment - expected) < 1, f"Expected ~{expected}, got {payment}"
    print(f"✓ Monthly payment test passed: ${payment:.2f}")


def test_zero_interest():
    """Test zero interest rate case"""
    payment = calculate_monthly_payment(360000, 0, 30)
    expected = 1000  # 360k / 360 months
    assert abs(
        payment - expected) < 0.01, f"Expected {expected}, got {payment}"
    print(f"✓ Zero interest test passed: ${payment:.2f}")


def test_remaining_balance():
    """Test remaining balance calculation"""
    # $400k loan at 6% for 30 years, after 12 payments
    remaining = calculate_remaining_balance(400000, 0.06, 30, 12)
    # After 1 year, should have paid down some principal
    assert remaining < 400000 and remaining > 390000, f"Unexpected remaining balance: {
        remaining}"
    print(f"✓ Remaining balance test passed: ${remaining:.2f}")


def test_simple_analysis():
    """Test basic rent vs buy analysis"""
    params = {
        'home_price': 400000,
        'down_payment_pct': 20,
        'initial_rate': 6.0,
        'current_rent': 2000,
        'home_price_growth': 3.0,
        'rent_growth': 3.0,
        'stock_growth': 7.0,
        'hoa_fees': 200,
        'property_tax_rate': 1.2,
        'insurance_rate': 0.3,
        'closing_costs': 10000
    }

    result = rent_vs_buy_analysis(params)

    # Basic sanity checks
    assert len(result['years']) == 31, "Should have 31 years of data"
    assert len(result['buy_net_worth']
               ) == 31, "Should have 31 buy net worth values"
    assert len(result['rent_net_worth']
               ) == 31, "Should have 31 rent net worth values"
    assert result['buy_net_worth'][0] < result['buy_net_worth'][-1], "Buy net worth should increase over time"
    assert result['rent_net_worth'][0] < result['rent_net_worth'][-1], "Rent net worth should increase over time"

    print(f"✓ Simple analysis test passed")
    print(f"  Final buy net worth: ${result['final_buy_net_worth']:,.2f}")
    print(f"  Final rent net worth: ${result['final_rent_net_worth']:,.2f}")


def run_all_tests():
    """Run all tests"""
    print("Running calculator tests...")
    try:
        test_monthly_payment()
        test_zero_interest()
        test_remaining_balance()
        test_simple_analysis()
        print("✅ All tests passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == '__main__':
    run_all_tests()
