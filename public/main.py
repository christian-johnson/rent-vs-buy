import json
import numpy as np
from typing import Dict, Any

# --- 1. Financial Math Module (Unit Testable) ---


class Financials:
    @staticmethod
    def calculate_pmt(principal: float, annual_rate: float, years: int) -> float:
        """Calculates fixed monthly mortgage payment."""
        if years <= 0 or principal <= 0:
            return 0.0
        if annual_rate == 0:
            return principal / (years * 12)

        monthly_rate = annual_rate / 12 / 100
        n_payments = years * 12
        return (
            principal
            * (monthly_rate * (1 + monthly_rate) ** n_payments)
            / ((1 + monthly_rate) ** n_payments - 1)
        )

    @staticmethod
    def get_remaining_balance(
        principal: float, annual_rate: float, years: int, months_paid: int
    ) -> float:
        """Calculates remaining principal balance after N months."""
        if months_paid == 0:
            return principal

        # Standard amortization formula
        monthly_rate = annual_rate / 12 / 100
        n_payments = years * 12

        if annual_rate == 0:
            return principal - (principal / n_payments) * months_paid

        numerator = (1 + monthly_rate) ** n_payments - (1 + monthly_rate) ** months_paid
        denominator = (1 + monthly_rate) ** n_payments - 1
        return principal * (numerator / denominator)


# --- 2. Simulation Logic ---


def generate_growth_matrices(
    mean: float, vol: float, months: int, n_sims: int, is_mc: bool
) -> np.ndarray:
    """
    Generates a matrix of monthly growth multipliers.
    Shape: (n_sims, months)
    """
    monthly_mean = mean / 100 / 12

    if not is_mc:
        # Static baseline: just the mean every month
        return np.full((1, months), 1 + monthly_mean)

    # Monte Carlo: Geometric Brownian Motion approx
    monthly_vol = (vol / 100) / np.sqrt(12)
    return 1 + np.random.normal(monthly_mean, monthly_vol, (n_sims, months))


def run_projection(
    params: Dict[str, Any], is_mc: bool = False, n_sims: int = 2000
) -> Dict[str, np.ndarray]:
    """
    Core engine. Takes parameters and growth rates, computes net worth trails.
    """
    # --- A. Setup Parameters ---
    years = 30
    months = years * 12
    dims = n_sims if is_mc else 1

    # Extract basics
    home_price = float(params.get("home_price", 0))
    down_payment = float(params.get("down_payment_amount", 0))
    loan_amount = home_price - down_payment
    initial_rate = float(params.get("initial_rate", 0))

    # Costs & Fees
    prop_tax_rate = float(params.get("property_tax_rate", 0)) / 100
    ins_rate = float(params.get("insurance_rate", 0)) / 100
    hoa_monthly = float(params.get("hoa_fees", 0))
    closing_costs = home_price * (float(params.get("closing_costs_pct", 0)) / 100)

    # --- B. Generate Growth Factors (The Stochastic Part) ---
    stock_factors = generate_growth_matrices(
        float(params.get("stock_growth", 0)),
        float(params.get("stock_volatility", 15)),
        months,
        dims,
        is_mc,
    )
    home_factors = generate_growth_matrices(
        float(params.get("home_price_growth", 0)),
        float(params.get("home_volatility", 5)),
        months,
        dims,
        is_mc,
    )
    rent_factors = generate_growth_matrices(
        float(params.get("rent_growth", 0)),
        float(params.get("rent_volatility", 5)),
        months,
        dims,
        is_mc,
    )

    # --- C. Pre-calculate Deterministic Schedules (Payment & Rent Logic) ---
    # Even in MC, the *obligation* (mortgage payment) is deterministic
    # unless we model adjustable rates. Refinancing makes this piecewise.

    # 1. Mortgage Schedule
    refi_year = int(params.get("refinance_year") or 0)
    refi_month = refi_year * 12

    # Base mortgage payment
    base_pmt = Financials.calculate_pmt(loan_amount, initial_rate, 30)
    monthly_payments = np.full(months, base_pmt)

    # Handle Refinance
    if refi_year > 0 and refi_year < 30:
        refi_rate = float(params.get("refinance_rate", 0))
        # Balance at refi point
        rem_bal = Financials.get_remaining_balance(
            loan_amount, initial_rate, 30, refi_month
        )
        # New payment (resetting to 30 years is standard)
        new_pmt = Financials.calculate_pmt(rem_bal, refi_rate, 30 - refi_year)
        monthly_payments[refi_month:] = new_pmt

    # 2. Rent Obligation Schedule (Base rent before growth/inflation)
    current_rent = float(params.get("current_rent", 0))
    rent_base_schedule = np.full(months, current_rent)

    move_year = int(params.get("move_to_larger_year") or 0)
    if move_year > 0 and move_year < 30:
        move_month = move_year * 12
        new_rent_today_dollars = float(params.get("new_rent_today") or 0)
        # We replace the base rent. Note: This base will still get multiplied
        # by cumulative inflation in the loop below.
        rent_base_schedule[move_month:] = new_rent_today_dollars

    # --- D. Initialize State Arrays ---
    # Shape: (dims, months + 1) to include month 0
    buy_investments = np.zeros((dims, months + 1))
    rent_investments = np.zeros((dims, months + 1))

    # Month 0 Setup
    # Renter keeps the downpayment + closing costs to invest
    rent_investments[:, 0] = down_payment + closing_costs
    buy_investments[:, 0] = 0  # Buyer spent cash

    home_values = np.zeros((dims, months + 1))
    home_values[:, 0] = home_price

    loan_balances = np.zeros((dims, months + 1))
    loan_balances[:, 0] = loan_amount

    # To track rent inflation for the "Move" logic
    cum_rent_inflation = np.ones((dims, months + 1))

    # --- E. Main Simulation Loop ---
    for m in range(1, months + 1):
        prev = m - 1

        # 1. Apply Market Growth
        home_values[:, m] = home_values[:, prev] * home_factors[:, prev]
        cum_rent_inflation[:, m] = cum_rent_inflation[:, prev] * rent_factors[:, prev]

        # 2. Determine Current Obligations
        # Rent: Base schedule * Cumulative Inflation
        # Note: If we moved, the base schedule changed. We assume the 'new rent'
        # was specified in today's dollars, so it also needs inflating.
        monthly_rent = rent_base_schedule[m - 1] * cum_rent_inflation[:, m]

        # Mortgage:
        # Determine current interest rate (Base or Refi)
        if refi_year > 0 and m > refi_month:
            curr_rate = float(params.get("refinance_rate", 0)) / 100
        else:
            curr_rate = initial_rate / 100

        monthly_pmt = monthly_payments[m - 1]
        interest_payment = loan_balances[:, prev] * (curr_rate / 12)
        principal_payment = monthly_pmt - interest_payment

        # Update Loan
        loan_balances[:, m] = loan_balances[:, prev] - principal_payment
        loan_balances[:, m] = np.maximum(loan_balances[:, m], 0)  # Floor at 0

        # 3. Handle Costs (Tax, Ins, HOA)
        monthly_tax = home_values[:, m] * (prop_tax_rate / 12)
        monthly_ins = home_values[:, m] * (ins_rate / 12)
        total_buy_cost = monthly_pmt + monthly_tax + monthly_ins + hoa_monthly

        # 4. Cash Flow Difference Logic
        cost_diff = monthly_rent - total_buy_cost

        # 5. Update Investment Accounts
        # Grow previous balance
        buy_investments[:, m] = buy_investments[:, prev] * stock_factors[:, prev]
        rent_investments[:, m] = rent_investments[:, prev] * stock_factors[:, prev]

        # Add new savings (Opportunity Cost)
        # If Rent > Buy (diff > 0), Buyer invests
        # If Buy > Rent (diff < 0), Renter invests
        buy_investments[:, m] += np.maximum(0, cost_diff)
        rent_investments[:, m] += np.maximum(0, -cost_diff)

        # Handle One-off Refinance Cost (deduct from buyer investments)
        if refi_year > 0 and m == refi_month:
            refi_cost = float(params.get("refinance_costs", 0))
            buy_investments[:, m] -= refi_cost

    # --- F. Final Net Worth Calculation ---
    home_equity = home_values - loan_balances
    # Net worth = Equity + Investments - Selling Costs
    buy_net_worth = home_equity + buy_investments
    rent_net_worth = rent_investments

    return {
        "years": np.arange(0, months + 1) / 12,
        "buy_net_worth": buy_net_worth,
        "rent_net_worth": rent_net_worth,
        "home_values": home_values,
        "loan_balances": loan_balances,
    }


# --- 3. Orchestrator / API Handler ---


def analyze_scenarios(params_json: str) -> str:
    params = json.loads(params_json)

    # 1. Run Baseline (Single path, mean values)
    baseline = run_projection(params, is_mc=False)

    # 2. Run Monte Carlo (2000 paths, random walk)
    mc_results = run_projection(params, is_mc=True, n_sims=2000)

    # 3. Aggregate Data for Charts (Subsample annual data points)
    indices = np.arange(0, 361, 12)  # Yearly indices
    years = indices // 12

    # Baseline vectors
    b_nw = baseline["buy_net_worth"][0, indices]
    r_nw = baseline["rent_net_worth"][0, indices]
    h_val = baseline["home_values"][0, indices]
    l_bal = baseline["loan_balances"][0, indices]

    # MC Percentiles
    mc_buy = mc_results["buy_net_worth"][:, indices]
    mc_rent = mc_results["rent_net_worth"][:, indices]

    buy_range = np.percentile(mc_buy, [16, 84], axis=0)  # ~1 std dev
    rent_range = np.percentile(mc_rent, [16, 84], axis=0)

    # Win Rates
    final_buy = mc_results["buy_net_worth"][:, -1]
    final_rent = mc_results["rent_net_worth"][:, -1]
    buy_win_pct = np.mean(final_buy > final_rent) * 100

    # Format Output
    yearly_data = []
    for i in range(len(years)):
        yearly_data.append(
            {
                "year": int(years[i]),
                "buy_net_worth": float(b_nw[i]),
                "rent_net_worth": float(r_nw[i]),
                "home_value": float(h_val[i]),
                "loan_balance": float(l_bal[i]),
                "home_equity": float(h_val[i] - l_bal[i]),
                "buy_nw_range": [float(buy_range[0][i]), float(buy_range[1][i])],
                "rent_nw_range": [float(rent_range[0][i]), float(rent_range[1][i])],
            }
        )

    return json.dumps(
        {
            "years": years.tolist(),
            "buy_net_worth": b_nw.tolist(),
            "rent_net_worth": r_nw.tolist(),
            "final_buy_net_worth": float(b_nw[-1]),
            "final_rent_net_worth": float(r_nw[-1]),
            "buy_wins_pct": float(buy_win_pct),
            "rent_wins_pct": 100.0 - float(buy_win_pct),
            "yearly_details": yearly_data,
        }
    )
