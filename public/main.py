import json
import numpy as np
from typing import Any, Dict


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

        monthly_rate = annual_rate / 12 / 100
        n_payments = years * 12

        if annual_rate == 0:
            return principal - (principal / n_payments) * months_paid

        numerator = (1 + monthly_rate) ** n_payments - (1 + monthly_rate) ** months_paid
        denominator = (1 + monthly_rate) ** n_payments - 1
        return max(0.0, principal * (numerator / denominator))


# --- 2. Simulation Logic ---


def generate_growth_matrices(
    mean: float, vol: float, months: int, n_sims: int, is_mc: bool
) -> np.ndarray:
    """
    Generates a matrix of monthly growth multipliers.
    Shape: (n_sims, months)

    Baseline: exact monthly compound rate (1 + r)^(1/12), so that compounding
    over 12 months yields exactly the stated annual return.

    Monte Carlo: lognormal GBM, ensuring:
      - growth factors are always positive (no negative asset prices)
      - E[annual compound return] = mean% exactly
      - annualized volatility = vol%

    For lognormal GBM with annual arithmetic return r and annual vol sigma:
      monthly log-return ~ N(drift, sigma_m^2)
      where sigma_m = sigma / sqrt(12)
            drift   = log(1+r)/12 - sigma_m^2/2

    This drift adjustment ensures E[exp(12 * log_return)] = 1 + r exactly.
    """
    r = mean / 100

    if not is_mc:
        monthly_factor = (1 + r) ** (1 / 12)
        return np.full((1, months), monthly_factor)

    sigma_m = (vol / 100) / np.sqrt(12)
    drift = np.log(1 + r) / 12 - 0.5 * sigma_m**2
    log_returns = np.random.normal(drift, sigma_m, (n_sims, months))
    return np.exp(log_returns)


def run_projection(
    params: Dict[str, Any], is_mc: bool = False, n_sims: int = 2000
) -> Dict[str, np.ndarray]:
    """
    Core engine. Takes parameters and growth rates, computes net worth trails.

    Net worth figures are after-tax and after-sale-costs at every snapshot year,
    i.e. "what would you net if you sold everything today?"
    """
    # --- A. Setup Parameters ---
    years = 30
    months = years * 12
    dims = n_sims if is_mc else 1

    home_price = float(params.get("home_price", 0))
    down_payment = float(params.get("down_payment_amount", 0))
    loan_amount = home_price - down_payment
    initial_rate = float(params.get("initial_rate", 0))

    # Ongoing costs
    prop_tax_rate = float(params.get("property_tax_rate", 0)) / 100  # annual decimal
    ins_rate = float(params.get("insurance_rate", 0)) / 100
    hoa_monthly = float(params.get("hoa_fees", 0))
    maintenance_rate = float(params.get("maintenance_rate", 1.0)) / 100  # annual %
    closing_costs = home_price * (float(params.get("closing_costs_pct", 0)) / 100)

    # Tax & sale parameters
    tax_bracket = float(params.get("federal_tax_bracket", 22.0)) / 100
    standard_deduction = float(params.get("standard_deduction", 29200.0))
    capital_gains_rate = float(params.get("capital_gains_rate", 15.0)) / 100
    home_cg_exclusion = float(params.get("home_cg_exclusion", 500000.0))
    selling_costs_pct = float(params.get("selling_costs_pct", 6.0)) / 100

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

    # --- C. Pre-calculate Deterministic Schedules ---

    # Mortgage payment schedule (piecewise if refinancing)
    refi_year = int(params.get("refinance_year") or 0)
    refi_month = refi_year * 12
    base_pmt = Financials.calculate_pmt(loan_amount, initial_rate, 30)
    monthly_payments = np.full(months, base_pmt)

    refi_rate = 0.0
    if refi_year > 0 and refi_year < 30:
        refi_rate = float(params.get("refinance_rate", 0))
        rem_bal = Financials.get_remaining_balance(
            loan_amount, initial_rate, 30, refi_month
        )
        # New payment over remaining term (not a 30-year reset)
        new_pmt = Financials.calculate_pmt(rem_bal, refi_rate, 30 - refi_year)
        monthly_payments[refi_month:] = new_pmt

    # Rent base schedule (today's dollars; multiplied by cumulative inflation in loop)
    current_rent = float(params.get("current_rent", 0))
    rent_base_schedule = np.full(months, current_rent)

    move_year = int(params.get("move_to_larger_year") or 0)
    if move_year > 0 and move_year < 30:
        move_month = move_year * 12
        new_rent_today_dollars = float(params.get("new_rent_today") or 0)
        rent_base_schedule[move_month:] = new_rent_today_dollars

    # --- D. Initialize State Arrays ---
    # Shape: (dims, months + 1) to include month 0
    buy_investments = np.zeros((dims, months + 1))
    rent_investments = np.zeros((dims, months + 1))

    # Cost basis for capital gains tax calculation at each snapshot
    buy_basis = np.zeros((dims, months + 1))
    rent_basis = np.zeros((dims, months + 1))

    # Month 0: renter keeps the down payment + closing costs and invests them
    rent_investments[:, 0] = down_payment + closing_costs
    rent_basis[:, 0] = down_payment + closing_costs
    # Buyer spent that cash; starts with zero investments

    home_values = np.zeros((dims, months + 1))
    home_values[:, 0] = home_price

    loan_balances = np.zeros((dims, months + 1))
    loan_balances[:, 0] = loan_amount

    cum_rent_inflation = np.ones((dims, months + 1))

    # --- E. Main Simulation Loop ---
    for m in range(1, months + 1):
        prev = m - 1

        # 1. Apply market growth
        home_values[:, m] = home_values[:, prev] * home_factors[:, prev]
        cum_rent_inflation[:, m] = cum_rent_inflation[:, prev] * rent_factors[:, prev]

        # 2. Rent obligation
        monthly_rent = rent_base_schedule[m - 1] * cum_rent_inflation[:, m]

        # 3. Mortgage amortization
        if refi_year > 0 and m > refi_month:
            curr_rate_dec = refi_rate / 100
        else:
            curr_rate_dec = initial_rate / 100

        monthly_pmt = monthly_payments[m - 1]
        interest_payment = loan_balances[:, prev] * (curr_rate_dec / 12)
        principal_payment = monthly_pmt - interest_payment
        loan_balances[:, m] = np.maximum(0, loan_balances[:, prev] - principal_payment)

        # 4. Buyer's monthly costs
        monthly_tax = home_values[:, m] * (prop_tax_rate / 12)
        monthly_ins = home_values[:, m] * (ins_rate / 12)
        monthly_maintenance = home_values[:, m] * (maintenance_rate / 12)
        total_buy_cost = (
            monthly_pmt + monthly_tax + monthly_ins + hoa_monthly + monthly_maintenance
        )

        # 5. Mortgage interest deduction
        # Benefit = max(0, itemized - standard_deduction) * tax_bracket / 12
        # Itemized = annualized interest + property tax (SALT capped at $10k/yr)
        annualized_interest = interest_payment * 12
        annualized_prop_tax = monthly_tax * 12  # tracks growing home value
        salt = np.minimum(annualized_prop_tax, 10000.0)
        monthly_mid_benefit = (
            np.maximum(0.0, annualized_interest + salt - standard_deduction)
            * tax_bracket
            / 12
        )
        # Tax savings reduce the effective cost of buying
        total_buy_cost = total_buy_cost - monthly_mid_benefit

        # 6. Opportunity cost: invest the monthly surplus
        cost_diff = monthly_rent - total_buy_cost

        # 7. Grow investment accounts
        buy_investments[:, m] = buy_investments[:, prev] * stock_factors[:, prev]
        rent_investments[:, m] = rent_investments[:, prev] * stock_factors[:, prev]

        # 8. Deposit monthly surplus into the cheaper scenario's investment account
        buy_contribution = np.maximum(0.0, cost_diff)
        rent_contribution = np.maximum(0.0, -cost_diff)
        buy_investments[:, m] += buy_contribution
        rent_investments[:, m] += rent_contribution

        # Track cost basis (contributions, not gains)
        buy_basis[:, m] = buy_basis[:, prev] + buy_contribution
        rent_basis[:, m] = rent_basis[:, prev] + rent_contribution

        # 9. Refinance closing cost (one-time, deducted from buyer's investments)
        if refi_year > 0 and m == refi_month:
            refi_cost = float(params.get("refinance_costs", 0))
            buy_investments[:, m] -= refi_cost
            # Cost basis not adjusted (conservative: slightly overstates CGT on remainder)

    # --- F. After-Tax, After-Sale Net Worth ---

    # Home: apply selling costs and capital gains tax as if selling at each snapshot
    home_gain = np.maximum(0.0, home_values - home_price)  # gain over purchase price
    home_cg_taxable = np.maximum(0.0, home_gain - home_cg_exclusion)
    home_cg_tax = home_cg_taxable * capital_gains_rate
    home_selling_costs = home_values * selling_costs_pct

    home_equity = home_values - loan_balances
    after_tax_equity = home_equity - home_selling_costs - home_cg_tax

    # Investment accounts: apply CGT on gains above cost basis
    buy_inv_gains = np.maximum(0.0, buy_investments - buy_basis)
    buy_investments_after_tax = buy_investments - buy_inv_gains * capital_gains_rate

    rent_inv_gains = np.maximum(0.0, rent_investments - rent_basis)
    rent_investments_after_tax = rent_investments - rent_inv_gains * capital_gains_rate

    buy_net_worth = after_tax_equity + buy_investments_after_tax
    rent_net_worth = rent_investments_after_tax

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

    # 1. Run baseline (single path, mean values)
    baseline = run_projection(params, is_mc=False)

    # 2. Run Monte Carlo (2000 paths)
    mc_results = run_projection(params, is_mc=True, n_sims=2000)

    # 3. Aggregate annual snapshots
    indices = np.arange(0, 361, 12)
    years = indices // 12

    b_nw = baseline["buy_net_worth"][0, indices]
    r_nw = baseline["rent_net_worth"][0, indices]
    h_val = baseline["home_values"][0, indices]
    l_bal = baseline["loan_balances"][0, indices]

    # MC percentiles (16th–84th ≈ ±1 std dev ≈ 68% confidence interval)
    mc_buy = mc_results["buy_net_worth"][:, indices]
    mc_rent = mc_results["rent_net_worth"][:, indices]
    buy_range = np.percentile(mc_buy, [16, 84], axis=0)
    rent_range = np.percentile(mc_rent, [16, 84], axis=0)

    # Win rates
    final_buy = mc_results["buy_net_worth"][:, -1]
    final_rent = mc_results["rent_net_worth"][:, -1]
    buy_win_pct = float(np.mean(final_buy > final_rent) * 100)

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
            "buy_wins_pct": buy_win_pct,
            "rent_wins_pct": 100.0 - buy_win_pct,
            "yearly_details": yearly_data,
        }
    )
