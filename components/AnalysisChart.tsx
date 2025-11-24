import React from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { AnalysisResult } from '../types';

interface AnalysisChartProps {
  data: AnalysisResult;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    // We filter payload to find the main lines (buy/rent net worth), avoiding the range areas
    const buyItem = payload.find((p: any) => p.dataKey === 'buy');
    const rentItem = payload.find((p: any) => p.dataKey === 'rent');
    
    if (!buyItem || !rentItem) return null;

    const buyVal = buyItem.value;
    const rentVal = rentItem.value;
    const diff = buyVal - rentVal;
    
    return (
      <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded shadow-lg text-sm">
        <p className="font-bold mb-2">{label > 0 ? `Year ${label}` : 'Start'}</p>
        <p className="text-buy font-semibold">Buy Median: ${Math.round(buyVal).toLocaleString()}</p>
        <p className="text-rent font-semibold">Rent Median: ${Math.round(rentVal).toLocaleString()}</p>
        <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
            <span className={diff > 0 ? "text-buy" : "text-rent"}>
                {diff > 0 ? "Buying" : "Renting"} ahead by ${Math.abs(Math.round(diff)).toLocaleString()}
            </span>
        </div>
      </div>
    );
  }
  return null;
};

export const AnalysisChart: React.FC<AnalysisChartProps> = ({ data }) => {
  const chartData = data.yearly_details.map((detail) => ({
    year: detail.year,
    buy: detail.buy_net_worth,
    rent: detail.rent_net_worth,
    // The Area component in Recharts (v2+) accepts [min, max] for range charts
    buy_range: detail.buy_nw_range,
    rent_range: detail.rent_nw_range
  }));

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={chartData}
          margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
          <XAxis 
            dataKey="year" 
            label={{ value: 'Years', position: 'insideBottomRight', offset: -5 }} 
            tick={{fill: 'currentColor'}}
          />
          <YAxis 
            tickFormatter={(value) => `$${(value / 1000)}k`}
            tick={{fill: 'currentColor'}}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={36}/>
          
          {/* Confidence Intervals (Envelopes) - Hidden from Legend */}
          <Area
            type="monotone"
            dataKey="buy_range"
            name="Buy Confidence (68%)"
            stroke="none"
            fill="#907aa9"
            fillOpacity={0.2}
            legendType="none"
          />
           <Area
            type="monotone"
            dataKey="rent_range"
            name="Rent Confidence (68%)"
            stroke="none"
            fill="#ea9d34"
            fillOpacity={0.2}
            legendType="none"
          />

          {/* Main Trend Lines */}
          <Line
            type="monotone"
            dataKey="buy"
            name="Buying Net Worth"
            stroke="#907aa9"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="rent"
            name="Renting Net Worth"
            stroke="#ea9d34"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
