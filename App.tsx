import React, { useState, useEffect, useRef } from 'react';
import { Moon, Sun, Plus, Trash2, Info, Github, X, HelpCircle, Minus, Activity } from 'lucide-react';
import { DEFAULT_PARAMS } from './constants';
import { AnalysisParams, AnalysisResult } from './types';
import { initPyodide, runAnalysis } from './services/pyodideService';
import { AnalysisChart } from './components/AnalysisChart';

const noSpinnerStyle = `
  input[type=number]::-webkit-inner-spin-button, 
  input[type=number]::-webkit-outer-spin-button { 
    -webkit-appearance: none; 
    margin: 0; 
  }
  input[type=number] {
    -moz-appearance: textfield;
  }
`;

const Section: React.FC<{ title: string; description?: string; children: React.ReactNode }> = ({ title, description, children }) => (
  <div className="h-full bg-paper dark:bg-darkPaper p-4 rounded-lg shadow-sm border border-stone-200 dark:border-gray-700">
    <h3 className="font-serif text-lg font-bold mb-1 text-primary dark:text-white">{title}</h3>
    {description && <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{description}</p>}
    <div className="flex flex-col gap-1">
      {children}
    </div>
  </div>
);


interface SmartInputProps {
  label: string;
  name: keyof AnalysisParams;
  value: number;
  onChange: (name: keyof AnalysisParams, val: number) => void;
  prefix?: string;
  suffix?: string;
  step?: number;
  min?: number;
  max?: number;
  helperText?: string;
  disabled?: boolean;
}

const SmartInput: React.FC<SmartInputProps> = ({
  label,
  name,
  value,
  onChange,
  prefix,
  suffix,
  step = 1,
  min = 0,
  max,
  helperText,
  disabled = false,
}) => {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // We need a ref to track the current value inside the setInterval closure
  // otherwise the interval will always use the stale value from when the click started
  const valueRef = useRef(value);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => stopContinuousChange();
  }, []);

  const handleStep = (direction: 1 | -1) => {
    if (disabled) return;
    
    // Use valueRef.current to get the latest value inside intervals
    const currentVal = valueRef.current;
    
    const stepString = step.toString();
    const precision = stepString.includes('.') ? stepString.split('.')[1].length : 0;
    
    let nextVal = currentVal + step * direction;
    nextVal = parseFloat(nextVal.toFixed(precision));

    // Bounds checking
    if (min !== undefined && nextVal < min) nextVal = min;
    if (max !== undefined && nextVal > max) nextVal = max;

    onChange(name, nextVal);
  };

  const startContinuousChange = (direction: 1 | -1) => {
    if (disabled) return;
    handleStep(direction);
    // Initial delay before rapid fire
    timeoutRef.current = setTimeout(() => {
      intervalRef.current = setInterval(() => {
        handleStep(direction);
      }, 80); // Speed of rapid fire
    }, 400); // Delay before rapid fire starts
  };

  const stopContinuousChange = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  // Handle direct typing
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    
    // Allow empty string for better typing UX, but don't fire onChange with it
    if (inputValue === '') {
      onChange(name, 0); // Or handle empty state differently depending on requirements
      return;
    }

    const val = parseFloat(inputValue);
    if (!isNaN(val)) {
      onChange(name, val);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-0 py-0.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-1">
        
        {/* Label Section */}
        <label 
          htmlFor={`input-${name as string}`}
          className="text-sm font-semibold text-gray-700 dark:text-gray-200 select-none cursor-pointer"
        >
          {label}
        </label>

        <div className="flex flex-col items-end gap-1">
          {/* Main Control Wrapper */}
          <div 
            className={`
              relative flex items-center bg-white dark:bg-gray-800 
              border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm 
              transition-all duration-200 overflow-hidden w-[200px] h-10
              ${disabled ? 'opacity-60 cursor-not-allowed bg-gray-50 dark:bg-gray-900' : 'hover:border-gray-400 dark:hover:border-gray-500 focus-within:ring-2 focus-within:ring-blue-500/50 focus-within:border-blue-500'}
            `}
          >
            
            {/* Decrease Button */}
            <button
              type="button"
              disabled={disabled}
              onMouseDown={() => startContinuousChange(-1)}
              onMouseUp={stopContinuousChange}
              onMouseLeave={stopContinuousChange}
              onTouchStart={() => startContinuousChange(-1)}
              onTouchEnd={stopContinuousChange}
              className="
                group flex items-center justify-center w-10 h-full
                bg-gray-50 dark:bg-gray-700/50 border-r border-gray-200 dark:border-gray-700 
                hover:bg-gray-100 dark:hover:bg-gray-600 active:bg-gray-200 dark:active:bg-gray-500
                focus:outline-none focus:bg-gray-200 transition-colors cursor-pointer
              "
              aria-label="Decrease value"
            >
              <Minus size={16} className="text-gray-500 group-hover:text-gray-800 dark:text-gray-400 dark:group-hover:text-gray-200 transition-colors" strokeWidth={2.5} />
            </button>

            {/* Input Area */}
            <div 
              className="flex-1 flex items-center justify-center relative px-2 h-full cursor-text"
              onClick={() => inputRef.current?.focus()}
            >
              {/* Prefix */}
              {prefix && (
                <span className="text-gray-400 dark:text-gray-500 text-sm font-medium select-none pointer-events-none mr-1">
                  {prefix}
                </span>
              )}
              
              <input
                ref={inputRef}
                id={`input-${name as string}`}
                type="number"
                value={value}
                onChange={handleInputChange}
                step={step}
                disabled={disabled}
                className="
                  w-full bg-transparent border-none outline-none p-0
                  text-center text-base font-bold text-gray-800 dark:text-gray-100 font-mono
                  placeholder-gray-300
                  [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none
                "
              />

              {/* Suffix */}
              {suffix && (
                <span className="text-gray-400 dark:text-gray-500 text-sm font-medium select-none pointer-events-none ml-1">
                  {suffix}
                </span>
              )}
            </div>

            {/* Increase Button */}
            <button
              type="button"
              disabled={disabled}
              onMouseDown={() => startContinuousChange(1)}
              onMouseUp={stopContinuousChange}
              onMouseLeave={stopContinuousChange}
              onTouchStart={() => startContinuousChange(1)}
              onTouchEnd={stopContinuousChange}
              className="
                group flex items-center justify-center w-10 h-full
                bg-gray-50 dark:bg-gray-700/50 border-l border-gray-200 dark:border-gray-700 
                hover:bg-gray-100 dark:hover:bg-gray-600 active:bg-gray-200 dark:active:bg-gray-500
                focus:outline-none focus:bg-gray-200 transition-colors cursor-pointer
              "
              aria-label="Increase value"
            >
              <Plus size={16} className="text-gray-500 group-hover:text-gray-800 dark:text-gray-400 dark:group-hover:text-gray-200 transition-colors" strokeWidth={2.5} />
            </button>
          </div>

          {/* Helper Text */}
          {helperText && (
            <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium tracking-wide">
              {helperText}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode }> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-[#1f1f2e] rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-gray-700">
        <div className="sticky top-0 bg-white/95 dark:bg-[#1f1f2e]/95 backdrop-blur p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <h2 className="text-2xl font-serif font-bold text-primary dark:text-white">{title}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors">
            <X size={24} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
};

const FaqItem: React.FC<{ question: string; children: React.ReactNode }> = ({ question, children }) => (
  <div className="mb-6 last:mb-0">
    <h4 className="font-bold text-lg mb-2 text-primary dark:text-gray-200">{question}</h4>
    <div className="text-gray-600 dark:text-gray-400 leading-relaxed text-sm space-y-2 border-l-4 border-buy pl-4">
      {children}
    </div>
  </div>
);

export default function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [params, setParams] = useState<AnalysisParams>(DEFAULT_PARAMS);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [showRefinance, setShowRefinance] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  
  const resultsRef = useRef<HTMLDivElement>(null);

  // Toggle Dark Mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Initialize Pyodide
  useEffect(() => {
    initPyodide()
      .then(() => {
        setLoading(false);
        handleRunAnalysis(false);
      })
      .catch(err => console.error(err));
      // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (name: keyof AnalysisParams, value: number) => {
    setParams(prev => ({ ...prev, [name]: value }));
  };

  const handleRunAnalysis = async (shouldScroll = true) => {
    setCalculating(true);
    try {
      const currentParams = { ...params };
      if (!showRefinance) currentParams.refinance_year = 0;
      if (!showUpgrade) currentParams.move_to_larger_year = 0;
      
      const res = await runAnalysis(currentParams);
      setResult(res);
      
      if (shouldScroll) {
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setCalculating(false);
    }
  };

  const getDownPaymentPercent = () => {
     if(params.home_price === 0) return 0;
     return ((params.down_payment_amount / params.home_price) * 100).toFixed(1);
  };

  return (
    <div className="min-h-screen font-sans pb-20 selection:bg-buy/20">
      <style>{noSpinnerStyle}</style>
      <nav className="sticky top-0 z-50 bg-[#f2e9e1]/90 dark:bg-[#191724]/90 backdrop-blur-md border-b border-stone-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center transition-colors duration-300">
        <div className="flex items-center gap-3">
            <span className="text-2xl">🏠</span>
            <h1 className="text-2xl font-bold font-serif text-primary dark:text-white tracking-tight hidden sm:block">Rent vs. Buy</h1>
        </div>
        <div className="flex items-center gap-2">
           <button 
            onClick={() => setIsAboutOpen(true)}
            className="px-3 py-2 text-sm font-medium text-primary dark:text-gray-200 hover:bg-black/5 dark:hover:bg-white/10 rounded-md transition-colors flex items-center gap-2"
          >
            <HelpCircle size={18} /> <span className="hidden sm:inline">About</span>
          </button>
          <div className="w-px h-6 bg-gray-300 dark:bg-gray-700 mx-1"></div>
          <a 
            href="https://github.com/christian-johnson/rent-vs-buy" 
            target="_blank" 
            rel="noopener noreferrer"
            className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-primary dark:text-gray-200"
            aria-label="GitHub Repository"
          >
            <Github className="w-5 h-5" />
          </a>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            aria-label="Toggle Dark Mode"
          >
            {darkMode ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-primary" />}
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 mt-8">
        {/* Header Title Section */}
        <div className="text-center mb-10 max-w-3xl mx-auto">
            <h2 className="text-4xl font-serif font-bold text-primary dark:text-white mb-4">
                Rent vs. Buy Simulator
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-300 leading-relaxed">
                 A sophisticated tool to simulate financial outcomes of renting versus buying. Explore the impact of market volatility and refinancing on your long-term net worth.
            </p>
        </div>

        {loading ? (
            <div className="flex flex-col items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-buy mb-4"></div>
                <p className="text-lg font-serif animate-pulse">Initializing Calculation Engine...</p>
            </div>
        ) : (
          <div className="flex flex-col gap-8">
            {/* Top Section: Form */}
            <div>
              <form onSubmit={(e) => { e.preventDefault(); handleRunAnalysis(); }}>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Property & Loan Column */}
                    <Section title="Property & Loan" description="Purchase details and financing.">
                        <SmartInput label="Home Price" name="home_price" value={params.home_price} onChange={handleChange} prefix="$" step={1000} />
                        <SmartInput 
                            label="Down Payment" 
                            name="down_payment_amount" 
                            value={params.down_payment_amount} 
                            onChange={handleChange} 
                            prefix="$"
                            step={1000}
                            helperText={`${getDownPaymentPercent()}% of price`} 
                        />
                        <SmartInput label="Interest Rate" name="initial_rate" value={params.initial_rate} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="Closing Costs" name="closing_costs_pct" value={params.closing_costs_pct} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="HOA Fees" name="hoa_fees" value={params.hoa_fees} onChange={handleChange} prefix="$" suffix="/mo" step={10} />
                    </Section>

                    {/* Market Assumptions Column */}
                    <Section title="Market Assumptions" description="Growth projections and costs.">
                        <SmartInput label="Current Rent" name="current_rent" value={params.current_rent} onChange={handleChange} prefix="$" suffix="/mo" step={50} />
                        <SmartInput label="Home Growth" name="home_price_growth" value={params.home_price_growth} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="Rent Growth" name="rent_growth" value={params.rent_growth} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="Stock Growth" name="stock_growth" value={params.stock_growth} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="Property Tax" name="property_tax_rate" value={params.property_tax_rate} onChange={handleChange} suffix="%" step={0.1} />
                        <SmartInput label="Insurance" name="insurance_rate" value={params.insurance_rate} onChange={handleChange} suffix="%" step={0.1} />
                    </Section>
                </div>

                {/* Optional Scenarios */}
                <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {showRefinance && (
                    <div className="relative group animate-in fade-in slide-in-from-top-4 duration-300">
                        <button 
                            type="button"
                            onClick={() => setShowRefinance(false)} 
                            className="absolute top-6 right-6 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 p-1.5 rounded-full transition-colors z-10"
                            title="Remove Refinancing"
                        >
                            <Trash2 size={18} />
                        </button>
                        <Section title="Refinancing" description="Simulate a future rate drop.">
                            <SmartInput label="Year to Refinance" name="refinance_year" value={params.refinance_year || 5} onChange={handleChange} suffix="yrs" />
                            <SmartInput label="New Rate" name="refinance_rate" value={params.refinance_rate || 5.0} onChange={handleChange} suffix="%" step={0.1} />
                            <SmartInput label="Refinance Cost" name="refinance_costs" value={params.refinance_costs || 3000} onChange={handleChange} prefix="$" step={500} />
                        </Section>
                    </div>
                    )}

                    {showUpgrade && (
                        <div className="relative group animate-in fade-in slide-in-from-top-4 duration-300">
                        <button 
                            type="button"
                            onClick={() => setShowUpgrade(false)} 
                            className="absolute top-6 right-6 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 p-1.5 rounded-full transition-colors z-10"
                            title="Remove Upgrade"
                        >
                            <Trash2 size={18} />
                        </button>
                        <Section title="Rental Upgrade" description="Simulate moving to a pricier rental later.">
                            <SmartInput label="Year of Move" name="move_to_larger_year" value={params.move_to_larger_year || 7} onChange={handleChange} suffix="yrs" />
                            <SmartInput label="New Rent (Today's $)" name="new_rent_today" value={params.new_rent_today || 3500} onChange={handleChange} prefix="$" suffix="/mo" step={100} />
                        </Section>
                    </div>
                    )}
                </div>

                {/* Simulation Parameters (Collapsed) */}
                <div className="mt-4">
                    <details className="group bg-paper dark:bg-darkPaper rounded-lg border border-stone-200 dark:border-gray-700">
                        <summary className="flex items-center justify-between p-4 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors select-none">
                            <div className="flex items-center gap-3">
                                <Activity className="text-primary dark:text-gray-200" size={20} />
                                <div>
                                    <h3 className="font-serif text-lg font-bold text-primary dark:text-white">Simulation Uncertainty</h3>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">Adjust the volatility of markets for Monte Carlo simulation.</p>
                                </div>
                            </div>
                            <span className="text-2xl text-gray-400 group-open:rotate-180 transition-transform">⌄</span>
                        </summary>
                        <div className="p-4 pt-0 border-t border-gray-100 dark:border-gray-700 mt-2">
                             <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-2">
                                <SmartInput label="Stock Volatility" name="stock_volatility" value={params.stock_volatility} onChange={handleChange} suffix="%" step={0.5} helperText="Std. Deviation" />
                                <SmartInput label="Home Volatility" name="home_volatility" value={params.home_volatility} onChange={handleChange} suffix="%" step={0.5} helperText="Std. Deviation" />
                                <SmartInput label="Rent Volatility" name="rent_volatility" value={params.rent_volatility} onChange={handleChange} suffix="%" step={0.5} helperText="Std. Deviation" />
                             </div>
                        </div>
                    </details>
                </div>

                {/* Action Buttons */}
                <div className="mt-8 flex flex-col items-center">
                    <div className="flex flex-wrap justify-center gap-4 mb-8">
                        {!showRefinance && (
                            <button
                            type="button"
                            onClick={() => { handleChange('refinance_year', 5); setShowRefinance(true); }}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-primary dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm transition-all transform hover:-translate-y-0.5"
                            >
                            <Plus size={16} /> Add Refinancing
                            </button>
                        )}
                        {!showUpgrade && (
                            <button
                            type="button"
                            onClick={() => { handleChange('move_to_larger_year', 7); setShowUpgrade(true); }}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-primary dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm transition-all transform hover:-translate-y-0.5"
                            >
                            <Plus size={16} /> Add Rental Upgrade
                            </button>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={calculating}
                        className="w-full md:w-auto min-w-[300px] py-4 px-8 bg-primary hover:bg-[#4a4568] dark:bg-primary dark:hover:bg-[#686385] text-white text-xl font-bold rounded-xl shadow-xl hover:shadow-2xl transform hover:-translate-y-1 transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                    >
                        {calculating ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Running 2,000 Simulations...
                        </>
                        ) : 'Run Analysis'}
                    </button>
                </div>
              </form>
            </div>

            {/* Bottom Section: Results */}
            <div className="scroll-mt-24 space-y-8 border-t-2 border-stone-200 dark:border-gray-700 pt-10" ref={resultsRef}>
              {result && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="md:col-span-3 bg-paper dark:bg-darkPaper rounded-xl shadow-sm border border-stone-200 dark:border-gray-700 p-8 text-center">
                        <h2 className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-6">Net Worth After 30 Years (Median)</h2>
                        <div className="flex flex-col md:flex-row justify-center items-center gap-8 md:gap-16">
                            <div className="flex flex-col items-center">
                                <p className="text-sm font-medium text-gray-500 mb-1">Buying Scenario</p>
                                <p className="text-4xl md:text-5xl font-bold font-serif text-buy">
                                    ${Math.round(result.final_buy_net_worth).toLocaleString()}
                                </p>
                            </div>
                            <div className="hidden md:block w-px h-16 bg-gray-300 dark:bg-gray-700"></div>
                            <div className="flex flex-col items-center">
                                <p className="text-sm font-medium text-gray-500 mb-1">Renting Scenario</p>
                                <p className="text-4xl md:text-5xl font-bold font-serif text-rent">
                                    ${Math.round(result.final_rent_net_worth).toLocaleString()}
                                </p>
                            </div>
                        </div>

                        {/* Monte Carlo Results */}
                        <div className="mt-8 flex flex-col items-center gap-4">
                            <div className="inline-block bg-white dark:bg-gray-800/50 px-6 py-3 rounded-full border border-gray-100 dark:border-gray-700 shadow-sm">
                                <span className="text-gray-600 dark:text-gray-300">Median Advantage: </span>
                                <span className={`font-bold text-lg ${result.final_buy_net_worth > result.final_rent_net_worth ? 'text-buy' : 'text-rent'}`}>
                                    {result.final_buy_net_worth > result.final_rent_net_worth ? 'Buying' : 'Renting'}
                                </span>
                                <span className="mx-2 text-gray-400">by</span>
                                <span className="font-bold text-lg text-primary dark:text-white">
                                    ${Math.abs(Math.round(result.final_buy_net_worth - result.final_rent_net_worth)).toLocaleString()}
                                </span>
                            </div>

                            <div className="text-sm md:text-base font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-lg">
                                Based on 2,000 simulations, 
                                <span className={result.buy_wins_pct > 50 ? "text-buy font-bold mx-1" : "text-rent font-bold mx-1"}>
                                    {result.buy_wins_pct > 50 ? "Buying" : "Renting"}
                                </span>
                                wins in 
                                <span className="font-bold text-primary dark:text-white mx-1">
                                    {result.buy_wins_pct > 50 ? result.buy_wins_pct.toFixed(1) : result.rent_wins_pct.toFixed(1)}%
                                </span>
                                of market scenarios.
                            </div>
                        </div>
                      </div>
                  </div>

                  <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 min-h-[450px]">
                    <div className="flex justify-between items-center mb-6 px-2">
                        <h3 className="text-lg font-bold text-primary dark:text-white">Equity Projection (with 68% Confidence)</h3>
                    </div>
                    <AnalysisChart data={result} />
                  </div>

                  <div className="bg-paper dark:bg-darkPaper rounded-xl shadow-sm border border-stone-200 dark:border-gray-700 overflow-hidden">
                    <details className="group">
                        <summary className="flex items-center justify-between p-6 cursor-pointer bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors select-none">
                            <span className="font-serif font-bold text-lg text-primary dark:text-white">View Detailed Yearly Breakdown</span>
                            <span className="text-2xl text-gray-400 group-open:rotate-180 transition-transform">⌄</span>
                        </summary>
                        <div className="overflow-x-auto max-h-96">
                            <table className="w-full text-sm text-right whitespace-nowrap">
                                <thead className="bg-gray-100 dark:bg-gray-800 text-xs uppercase text-gray-500 sticky top-0 z-10">
                                    <tr>
                                        <th className="px-6 py-4 text-left font-semibold">Year</th>
                                        <th className="px-6 py-4 font-semibold">Home Value</th>
                                        <th className="px-6 py-4 font-semibold">Loan Balance</th>
                                        <th className="px-6 py-4 font-semibold">Home Equity</th>
                                        <th className="px-6 py-4 bg-buy/10 font-bold text-buy">Buy Net Worth</th>
                                        <th className="px-6 py-4 bg-rent/10 font-bold text-rent">Rent Net Worth</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                    {result.yearly_details.map((row) => (
                                        <tr key={row.year} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                                            <td className="px-6 py-3 text-left font-medium">{row.year}</td>
                                            <td className="px-6 py-3 text-gray-600 dark:text-gray-400">${Math.round(row.home_value).toLocaleString()}</td>
                                            <td className="px-6 py-3 text-gray-600 dark:text-gray-400">${Math.round(row.loan_balance).toLocaleString()}</td>
                                            <td className="px-6 py-3 text-gray-600 dark:text-gray-400">${Math.round(row.home_equity).toLocaleString()}</td>
                                            <td className="px-6 py-3 font-bold text-buy bg-buy/5">${Math.round(row.buy_net_worth).toLocaleString()}</td>
                                            <td className="px-6 py-3 font-bold text-rent bg-rent/5">${Math.round(row.rent_net_worth).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </details>
                  </div>
                </>
              )}

              <div className="bg-blue-50 dark:bg-blue-900/10 p-6 rounded-xl border border-blue-100 dark:border-blue-800/30 flex gap-4">
                 <Info className="flex-shrink-0 text-blue-600 dark:text-blue-400 mt-1" size={24} />
                 <div>
                    <h3 className="font-bold text-blue-800 dark:text-blue-300 mb-2">Understanding Opportunity Cost</h3>
                    <p className="text-sm text-blue-800/80 dark:text-blue-300/80 leading-relaxed max-w-4xl">
                        The most important factor in this calculator is how you treat savings. It assumes that if renting is cheaper than buying (monthly), you invest the difference. Conversely, if buying is cheaper, it assumes the buyer invests the difference. Without this disciplined investing, the math changes significantly.
                    </p>
                 </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* About Modal */}
      <Modal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} title="About & FAQ">
        <FaqItem question="How does this calculator work?">
          <p>This tool compares the long-term financial outcomes of buying a home versus renting. It projects your net worth over 30 years in both scenarios by considering factors like home appreciation, rent increases, and investments.</p>
        </FaqItem>

        <FaqItem question="What is the Simulation Uncertainty feature?">
          <p>Standard calculators assume a fixed growth rate (e.g., 8% every single year). In reality, markets fluctuate. We run 2,000 scenarios using the volatilities you provide to generate a 'cloud' of possibilities. The shaded areas on the chart represent the likely range of outcomes (68% confidence interval).</p>
        </FaqItem>

        <FaqItem question="I increased my rent - and my buying equity increased. What gives?">
          <p>The calculator invests any difference in the monthly payments between renting and buying into the stock market. So, if your rent is $1500 per month, and your total mortgage/insurance/taxes are $2000 per month, the rental scenario invests $500 per month into stocks.</p>
          <p className="mt-2">If you increase your rent to $2500 per month, that extra $500 now is invested in the buying scenario instead (the idea being, you indicated that you are able to afford a total $2500 per month outlay).</p>
        </FaqItem>

        <FaqItem question="How does this differ from the New York Times calculator?">
           <p>This one is better in some ways and worse in others. The main feature here is the ability to add refinancing and moves to a more expensive apartment, instead of a single point-in-time comparison.</p>
           <p className="mt-2">However, this calculator is missing some other (perhaps minor) components, such as taking into account the mortgage interest tax deduction that the New York Times calculator does.</p>
        </FaqItem>

        <FaqItem question="What about inflation?">
            <p>This calculator uses current dollars for everything - no assumptions are made about inflation. So the returns from the stock market and home price/rental price growth should use pre-inflation numbers.</p> 
            <p className="mt-2">For instance, you might typically assume that the stock market averages a real return of 7%, with average inflation 3% and 10% average unadjusted returns. For this calculator, you should use the 10% returns as your assumption, and then interpret the outputs in current dollars.</p>
        </FaqItem>
        
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
           <p className="text-sm text-gray-500 dark:text-gray-400">
             I think there's a bug, or I'd like to contribute to this calculator? 
             <a href="https://github.com/christian-johnson/rent-vs-buy" className="text-buy hover:underline ml-1">
                Head to the GitHub repo.
             </a>
           </p>
        </div>
      </Modal>
    </div>
  );
}
