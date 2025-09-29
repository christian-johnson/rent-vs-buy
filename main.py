# main.py

def calculate_monthly_payment(principal, rate, years):
    """Calculates the monthly mortgage payment."""
    if years <= 0:
        return principal  # Should be paid off
    if rate == 0:
        return principal / (years * 12)
    monthly_rate = rate / 12
    num_payments = years * 12
    if num_payments == 0:
        return principal
    payment = principal * (monthly_rate * (1 + monthly_rate)
                           ** num_payments) / ((1 + monthly_rate)**num_payments - 1)
    return payment


def calculate_remaining_balance(original_principal, rate, years, months_paid):
    """Calculates remaining mortgage balance after a number of months."""
    if rate == 0:
        return original_principal * (1 - (months_paid / (years * 12)))
    monthly_rate = rate / 12
    monthly_payment = calculate_monthly_payment(
        original_principal, rate, years)
    balance = original_principal * ((1 + monthly_rate)**months_paid) - \
        monthly_payment * \
        (((1 + monthly_rate)**months_paid - 1) / monthly_rate)
    return max(0, balance)


def rent_vs_buy_analysis(params):
    """
    Analyzes renting vs. buying, now with optional refinancing and rental upgrade scenarios.
    """
    # --- 1. SETUP AND PARAMETER EXTRACTION ---
    years_to_simulate = 30
    months = years_to_simulate * 12

    # Core parameters
    home_price = params.get('home_price', 0)
    down_payment_pct = params.get('down_payment_pct', 0) / 100
    initial_rate = params.get('initial_rate', 0) / 100
    current_rent = params.get('current_rent', 0)
    home_price_growth = params.get('home_price_growth', 0) / 100
    rent_growth = params.get('rent_growth', 0) / 100
    stock_growth = params.get('stock_growth', 0) / 100
    hoa_fees = params.get('hoa_fees', 0)
    property_tax_rate = params.get('property_tax_rate', 0) / 100
    insurance_rate = params.get('insurance_rate', 0) / 100
    closing_costs = params.get('closing_costs', 0)

    # Optional Scenario Parameters
    refinance_year = int(params.get('refinance_year', 0))
    refinance_rate = params.get('refinance_rate', 0) / 100
    refinance_costs = params.get('refinance_costs', 0)
    move_to_larger_year = int(params.get('move_to_larger_year', 0))
    larger_rent_multiplier = params.get('larger_rent_multiplier', 1.0)

    # --- 2. INITIALIZE FINANCIAL STATE (YEAR 0) ---
    down_payment = home_price * down_payment_pct
    initial_loan_amount = home_price - down_payment
    current_loan_balance = initial_loan_amount
    current_rate = initial_rate
    loan_term_years = 30
    current_monthly_payment = calculate_monthly_payment(
        initial_loan_amount, initial_rate, loan_term_years)

    buy_investments = 0
    rent_investments = down_payment + closing_costs

    buy_net_worth_yearly = [home_price -
                            current_loan_balance + buy_investments]
    rent_net_worth_yearly = [rent_investments]

    # --- 3. MONTH-BY-MONTH SIMULATION ---
    refinanced = False
    moved_to_larger = False

    for month in range(1, months + 1):
        year = month // 12

        # --- Handle Optional Scenarios ---
        if refinance_year > 0 and year >= refinance_year and not refinanced:
            refinanced = True
            # Calculate balance at the point of refinancing
            remaining_balance = calculate_remaining_balance(
                initial_loan_amount, initial_rate, 30, month)
            # Subtract refinance costs from buyer's investments
            buy_investments -= refinance_costs
            # Set new loan terms
            current_loan_balance = remaining_balance
            current_rate = refinance_rate
            # Typically a new 30 or 15 year loan, simplifying to remaining term
            loan_term_years = 30 - year
            current_monthly_payment = calculate_monthly_payment(
                current_loan_balance, current_rate, loan_term_years)

        current_home_value = home_price * (1 + home_price_growth)**(month / 12)

        if move_to_larger_year > 0 and year >= move_to_larger_year and not moved_to_larger:
            moved_to_larger = True
            # Calculate the rent at the time of the move and apply the multiplier
            current_rent = (current_rent * (1 + rent_growth) **
                            (month / 12)) * larger_rent_multiplier
            # Reset rent growth from this new, higher base
            rent_growth_start_month = month
            base_rent_after_move = current_rent

        if moved_to_larger:
            months_since_move = month - rent_growth_start_month
            current_monthly_rent = base_rent_after_move * \
                (1 + rent_growth)**(months_since_move / 12)
        else:
            current_monthly_rent = current_rent * \
                (1 + rent_growth)**(month / 12)

        # --- Standard Monthly Calculations ---
        monthly_interest = current_loan_balance * (current_rate / 12)
        monthly_property_tax = (current_home_value * property_tax_rate) / 12
        monthly_insurance = (current_home_value * insurance_rate) / 12

        if current_loan_balance <= 0:
            current_monthly_payment = 0
            monthly_interest = 0
            monthly_principal = 0
        else:
            monthly_principal = current_monthly_payment - monthly_interest

        total_monthly_buy_cost = current_monthly_payment + \
            monthly_property_tax + monthly_insurance + hoa_fees
        current_loan_balance -= monthly_principal

        rent_investments *= (1 + stock_growth / 12)
        buy_investments *= (1 + stock_growth / 12)

        cost_difference = total_monthly_buy_cost - current_monthly_rent
        if cost_difference > 0:
            rent_investments += cost_difference
        else:
            buy_investments += abs(cost_difference)

        if month % 12 == 0:
            home_equity = current_home_value - current_loan_balance
            buy_net_worth_yearly.append(home_equity + buy_investments)
            rent_net_worth_yearly.append(rent_investments)

    # --- 4. FINALIZE FOR RETURN ---
    return {
        'years': list(range(years_to_simulate + 1)),
        'buy_net_worth': buy_net_worth_yearly,
        'rent_net_worth': rent_net_worth_yearly,
        'final_buy_net_worth': buy_net_worth_yearly[-1],
        'final_rent_net_worth': rent_net_worth_yearly[-1]
    }
    # Run the analysis
    results_df = rent_vs_buy_analysis(parameters)
