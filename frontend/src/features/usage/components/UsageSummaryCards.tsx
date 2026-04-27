/**
 * ============================================================================
 * FILE: UsageSummaryCards.tsx
 * LOCATION: frontend/src/features/usage/components/UsageSummaryCards.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Summary stat cards showing key usage metrics at a glance.
 *
 * ROLE IN PROJECT:
 *    Renders a grid of metric cards: Total Cost, Total Requests,
 *    Top Provider, and Average Cost per Request. Includes loading
 *    skeleton state for smooth data transitions on the usage dashboard.
 *
 * KEY COMPONENTS:
 *    - UsageSummaryCards: Grid of metric summary cards
 *    - UsageSummaryCardsProps: Interface for component props
 *    - SkeletonCard: Loading placeholder animation
 *    - StatCard: Individual metric display component
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: @/types/usage
 *
 * USAGE:
 *    <UsageSummaryCards
 *        summary={usageSummary}
 *        isLoading={isLoading}
 *    />
 * ============================================================================
 */

import type { UsageSummary } from '@/types/usage';

interface UsageSummaryCardsProps {
    summary: UsageSummary | undefined;
    isLoading: boolean;
}

function SkeletonCard() {
    return (
        <div className="bg-card rounded-lg p-4 border border-border animate-pulse">
            <div className="h-3 w-20 bg-gray-700 rounded mb-3" />
            <div className="h-6 w-24 bg-gray-700 rounded" />
        </div>
    );
}

interface StatCardProps {
    label: string;
    value: string;
    subtext?: string;
}

function StatCard({ label, value, subtext }: StatCardProps) {
    return (
        <div className="bg-card rounded-lg p-3 sm:p-4 border border-border">
            <p className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wide mb-1 truncate" title={label}>
                {label}
            </p>
            <p className="text-lg sm:text-xl font-semibold text-white truncate" title={value}>{value}</p>
            {subtext && (
                <p className="text-[10px] sm:text-xs text-gray-500 mt-1 truncate">{subtext}</p>
            )}
        </div>
    );
}

export function UsageSummaryCards({ summary, isLoading }: UsageSummaryCardsProps) {
    if (isLoading) {
        return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
            </div>
        );
    }

    const totalCost = summary?.total_cost ?? 0;
    const totalRequests = summary?.total_requests ?? 0;

    const topProvider = summary?.by_provider && summary.by_provider.length > 0
        ? [...summary.by_provider].sort((a, b) => b.cost - a.cost)[0]
        : undefined;

    const avgCost = totalRequests > 0
        ? totalCost / totalRequests
        : 0;

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <StatCard
                label="Total Cost"
                value={`$${totalCost.toFixed(4)}`}
            />
            <StatCard
                label="Total Requests"
                value={totalRequests.toLocaleString()}
            />
            <StatCard
                label="Top Provider"
                value={topProvider?.provider ?? 'N/A'}
                subtext={topProvider ? `$${topProvider.cost.toFixed(4)}` : undefined}
            />
            <StatCard
                label="Avg Cost/Request"
                value={`$${avgCost.toFixed(6)}`}
            />
        </div>
    );
}
