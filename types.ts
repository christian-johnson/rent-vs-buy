export interface AnalysisParams {
  home_price: number;
  down_payment_amount: number;
  initial_rate: number;
  closing_costs_pct: number;
  hoa_fees: number;
  current_rent: number;
  home_price_growth: number;
  rent_growth: number;
  stock_growth: number;
  property_tax_rate: number;
  insurance_rate: number;
  // Optional scenarios
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
  principal_paid: number;
  interest_paid: number;
  tax_ins_paid: number;
  hoa_paid: number;
  rent_paid: number;
  buy_net_worth: number;
  rent_net_worth: number;
}

export interface AnalysisResult {
  years: number[];
  buy_net_worth: number[];
  rent_net_worth: number[];
  final_buy_net_worth: number;
  final_rent_net_worth: number;
  yearly_details: YearlyDetail[];
  error?: string;
}
