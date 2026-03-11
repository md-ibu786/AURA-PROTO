// CostByProviderChart.tsx
// Bar chart displaying cost breakdown by LLM provider

// Renders a Recharts BarChart with Cyber Yellow (#FFD400) bars
// on a dark background. Shows "No data available" when data is empty.

// @see: types/usage.ts - ProviderCost type definition
// @note: Provider names are displayed on the X-axis

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import type { ProviderCost } from '@/types/usage';

interface CostByProviderChartProps {
    data: ProviderCost[];
}

export function CostByProviderChart({ data }: CostByProviderChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-[250px] text-gray-500 text-sm">
                No data available
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                    dataKey="provider"
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
                <Bar dataKey="cost" fill="#FFD400" radius={[4, 4, 0, 0]} />
            </BarChart>
        </ResponsiveContainer>
    );
}
