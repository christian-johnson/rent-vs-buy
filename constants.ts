import { AnalysisParams } from "./types";

export const DEFAULT_PARAMS: AnalysisParams = {
  home_price: 500000,
  down_payment_amount: 100000,
  initial_rate: 6.5,
  closing_costs_pct: 2.5,
  hoa_fees: 150,
  current_rent: 2500,
  home_price_growth: 3.5,
  rent_growth: 3.0,
  stock_growth: 8.0,
  property_tax_rate: 1.2,
  insurance_rate: 0.5,
  
  // Defaults for MC (Std Dev)
  stock_volatility: 15.0, // Stocks are volatile
  home_volatility: 5.0,   // Real estate less so
  rent_volatility: 5.0,   

  refinance_year: 0,
  refinance_rate: 0,
  refinance_costs: 0,
  move_to_larger_year: 0,
  new_rent_today: 0,
};
