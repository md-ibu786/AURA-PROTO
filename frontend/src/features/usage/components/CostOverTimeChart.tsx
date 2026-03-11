// CostOverTimeChart.tsx
// Area chart displaying daily cost trends over a selected time period

// Renders a Recharts AreaChart with Cyber Yellow (#FFD400) theming
// on a dark background. Shows "No data available" when data is empty.
// Uses ResponsiveContainer for automatic width/height adaptation.

// @see: types/usage.ts - DailyCost type definition
// @note: Y-axis formats values as USD currency

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import type { DailyCost } from '@/types/usage';

interface CostOverTimeChartProps {
    data: DailyCost[];
}

export function CostOverTimeChart({ data }: CostOverTimeChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-[300px] text-gray-500 text-sm">
                No data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                    dataKey="date"
                    stroke="#888"
                    tick={{ fill: '#888', fontSize: 12 }}
                />
                <YAxis
                    stroke="#888"
                    tick={{ fill: '#888', fontSize: 12 }}
                    tickFormatter={(value: number) => `$${value.toFixed(2)}`}
                />
                <Tooltip
                    contentStyle={{
                        backgroundColor: '#1A1A1A',
                        border: '1px solid #333',
                        borderRadius: '8px',
                        color: '#fff',
                    }}
                    labelStyle={{ color: '#888' }}
                    formatter={(value) => [`$${Number(value).toFixed(4)}`, 'Cost']}
                />
                <Area
                    type="monotone"
                    dataKey="cost"
                    stroke="#FFD400"
                    fill="#FFD400"
                    fillOpacity={0.2}
                    strokeWidth={2}
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
