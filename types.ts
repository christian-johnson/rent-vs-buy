export interface AnalysisParams {
  // Primary inputs
  home_price: number;
  down_payment_amount: number;
  initial_rate: number;
  current_rent: number;
  home_price_growth: number;
  stock_growth: number;
  property_tax_rate: number;

  // Advanced inputs (have sensible defaults)
  closing_costs_pct: number;
  hoa_fees: number;
  insurance_rate: number;
  maintenance_rate: number;
  selling_costs_pct: number;
  rent_growth: number;
  federal_tax_bracket: number;
  standard_deduction: number;
  capital_gains_rate: number;
  home_cg_exclusion: number;

  // Monte Carlo volatility
  stock_volatility: number;
  home_volatility: number;
  rent_volatility: number;

  // Optional scenario overlays
  refinance_year?: number;
  refinance_rate?: number;
  refinance_costs?: number;
  move_to_larger_year?: number;
  new_rent_today?: number;
}

export interface YearlyDetail {
  year: number;
  home_value: number;
  loan_balance: number;
  home_equity: number;
  buy_net_worth: number;
  rent_net_worth: number;
  buy_nw_range: [number, number];
  rent_nw_range: [number, number];
}

export interface AnalysisResult {
  years: number[];
  buy_net_worth: number[];
  rent_net_worth: number[];
  final_buy_net_worth: number;
  final_rent_net_worth: number;
  buy_wins_pct: number;
  rent_wins_pct: number;
  yearly_details: YearlyDetail[];
  error?: string;
}
