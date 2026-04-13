import { AnalysisParams } from "./types";

export const DEFAULT_PARAMS: AnalysisParams = {
  // Primary inputs
  home_price: 500000,
  down_payment_amount: 100000,
  initial_rate: 6.5,
  current_rent: 2500,
  home_price_growth: 3.5,
  stock_growth: 8.0,
  property_tax_rate: 1.2,

  // Advanced inputs
  closing_costs_pct: 2.5,
  hoa_fees: 0,
  insurance_rate: 0.5,
  maintenance_rate: 1.0,    // 1% of home value per year
  selling_costs_pct: 6.0,   // realtor fees + closing costs at sale
  rent_growth: 3.0,
  federal_tax_bracket: 22.0,
  standard_deduction: 29200, // 2024 married filing jointly
  capital_gains_rate: 15.0,
  home_cg_exclusion: 500000, // primary residence exclusion (married)

  // Monte Carlo volatility (std. dev.)
  stock_volatility: 15.0,
  home_volatility: 5.0,
  rent_volatility: 5.0,

  // Optional scenario defaults
  refinance_year: 0,
  refinance_rate: 0,
  refinance_costs: 0,
  move_to_larger_year: 0,
  new_rent_today: 0,
};
