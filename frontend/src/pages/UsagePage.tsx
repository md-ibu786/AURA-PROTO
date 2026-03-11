// UsagePage.tsx
// Admin-only usage and cost dashboard page for AURA-NOTES-MANAGER

// Renders a full-page dashboard with date range filtering, summary cards,
// and three chart sections (cost over time, by provider, by model).
// Uses TanStack Query hooks to fetch data from the usage API endpoints.
// Follows the SettingsPage pattern with back navigation arrow.

// @see: features/usage/hooks/useUsageApi.ts - Data fetching hooks
// @see: features/usage/components/ - Individual chart and filter components
// @note: Default date range is last 30 days

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { DateRangeFilter } from '@/features/usage/components/DateRangeFilter';
import { UsageSummaryCards } from '@/features/usage/components/UsageSummaryCards';
import { CostOverTimeChart } from '@/features/usage/components/CostOverTimeChart';
import { CostByProviderChart } from '@/features/usage/components/CostByProviderChart';
import { CostByModelChart } from '@/features/usage/components/CostByModelChart';
import {
    useUsageSummary,
    useDailyCosts,
    useCostByProvider,
    useCostByModel,
} from '@/features/usage/hooks/useUsageApi';

function getDefaultDateRange(): { start: string; end: string } {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0],
    };
}

export function UsagePage() {
    const navigate = useNavigate();
    const defaults = getDefaultDateRange();
    const [startDate, setStartDate] = useState(defaults.start);
    const [endDate, setEndDate] = useState(defaults.end);

    const { data: summaryData, isLoading: summaryLoading } = useUsageSummary(startDate, endDate);
    const { data: dailyData } = useDailyCosts(startDate, endDate);
    const { data: providerData } = useCostByProvider(startDate, endDate);
    const { data: modelData } = useCostByModel(startDate, endDate);

    const handleDateChange = (start: string, end: string) => {
        setStartDate(start);
        setEndDate(end);
    };

    const hasAnyData = (summaryData?.total_requests ?? 0) > 0;

    return (
        <div className="min-h-screen bg-[#0A0A0A] text-foreground p-4 md:p-8">
            <div className="max-w-6xl mx-auto space-y-6 pb-12">
                {/* Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2 mb-2">
                            <button
                                onClick={() => navigate(-1)}
                                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                                title="Back"
                            >
                                <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                            </button>
                            <h1 className="text-3xl font-bold tracking-tight text-[#FFD400]">
                                Usage & Cost Dashboard
                            </h1>
                        </div>
                        <p className="text-muted-foreground">
                            Track LLM usage and estimated costs across providers.
                        </p>
                    </div>
                </div>

                {/* Date Range Filter */}
                <DateRangeFilter
                    startDate={startDate}
                    endDate={endDate}
                    onChange={handleDateChange}
                />

                {/* Summary Cards */}
                <UsageSummaryCards
                    summary={summaryData}
                    isLoading={summaryLoading}
                />

                {/* Empty State */}
                {!summaryLoading && !hasAnyData && (
                    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                        <svg
                            className="w-16 h-16 mb-4 opacity-30"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                            />
                        </svg>
                        <p className="text-lg font-medium">No usage data yet</p>
                        <p className="text-sm mt-1">
                            Usage data will appear here after you start using LLM models
                        </p>
                    </div>
                )}

                {/* Charts Grid */}
                {hasAnyData && (
                    <>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <section className="bg-[#1A1A1A] rounded-lg p-4 border border-gray-800">
                                <h2 className="text-lg font-semibold text-white mb-4">
                                    Cost Over Time
                                </h2>
                                <CostOverTimeChart data={dailyData ?? []} />
                            </section>
                            <section className="bg-[#1A1A1A] rounded-lg p-4 border border-gray-800">
                                <h2 className="text-lg font-semibold text-white mb-4">
                                    Cost by Provider
                                </h2>
                                <CostByProviderChart data={providerData ?? []} />
                            </section>
                        </div>
                        <section className="bg-[#1A1A1A] rounded-lg p-4 border border-gray-800">
                            <h2 className="text-lg font-semibold text-white mb-4">
                                Cost by Model
                            </h2>
                            <CostByModelChart data={modelData ?? []} />
                        </section>
                    </>
                )}

                {/* Footer Disclaimer */}
                <p className="text-xs text-gray-500 text-center pb-4">
                    All costs are estimates based on published provider pricing and
                    approximate token counts. Actual billing may differ.
                </p>
            </div>
        </div>
    );
}
