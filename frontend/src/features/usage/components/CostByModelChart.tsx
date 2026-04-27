/**
 * ============================================================================
 * FILE: CostByModelChart.tsx
 * LOCATION: frontend/src/features/usage/components/CostByModelChart.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Horizontal bar chart displaying cost breakdown by LLM model.
 *
 * ROLE IN PROJECT:
 *    Renders a Recharts horizontal BarChart with Cyber Yellow (#FFD400) bars.
 *    Shows top 10 models sorted by cost descending. Dynamic height scales
 *    with the number of models displayed. Model names are truncated on
 *    Y-axis to prevent overflow in the usage dashboard.
 *
 * KEY COMPONENTS:
 *    - CostByModelChart: Horizontal bar chart for model cost comparison
 *    - CostByModelChartProps: Interface for component props
 *
 * DEPENDENCIES:
 *    - External: recharts
 *    - Internal: @/types/usage
 *
 * USAGE:
 *    <CostByModelChart data={modelCosts} />
 * ============================================================================
 */

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import type { ModelCost } from '@/types/usage';

interface CostByModelChartProps {
    data: ModelCost[];
}

export function CostByModelChart({ data }: CostByModelChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-[250px] text-gray-500 text-sm">
                No data available
            </div>
        );
    }

    // Sort by cost descending, take top 10
    const sortedData = [...data]
        .sort((a, b) => b.cost - a.cost)
        .slice(0, 10);

    const chartHeight = Math.max(250, sortedData.length * 40);

    return (
        <ResponsiveContainer width="100%" height={chartHeight}>
            <BarChart
                data={sortedData}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                    type="number"
                    stroke="#888"
                    tick={{ fill: '#888', fontSize: 12 }}
                    tickFormatter={(value: number) => `$${value.toFixed(2)}`}
                />
                <YAxis
                    type="category"
                    dataKey="model"
                    stroke="#888"
                    tick={{ fill: '#888', fontSize: 11 }}
                    width={160}
                    tickFormatter={(value: string) =>
                        value.length > 24 ? `${value.slice(0, 24)}...` : value
                    }
                />
                <Tooltip
                    contentStyle={{
                        backgroundColor: '#0d0d0d',
                        border: '1px solid #333',
                        borderRadius: '8px',
                        color: '#fff',
                    }}
                    labelStyle={{ color: '#888' }}
                    formatter={(value, _name, entry) => [
                        `$${Number(value).toFixed(4)} (${(entry?.payload as ModelCost)?.provider ?? ''})`,
                        'Cost',
                    ]}
                />
                <Bar dataKey="cost" fill="#FFD400" radius={[0, 4, 4, 0]} />
            </BarChart>
        </ResponsiveContainer>
    );
}
