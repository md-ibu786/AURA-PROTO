// useUsageApi.ts
// TanStack Query hooks for usage tracking API endpoints

// Provides query hooks for fetching usage summaries and session costs.
// The summary endpoint returns all breakdowns (daily, by-provider,
// by-model) in a single response — derived hooks select from that
// cached result to avoid redundant Redis scans.

// @see: types/usage.ts - Type definitions for usage API responses
// @see: features/settings/hooks/useSettingsApi.ts - Equivalent pattern for settings
// @note: staleTime is 2 minutes for usage data (more volatile than settings)

import { useQuery } from '@tanstack/react-query';
import { fetchApi } from '@/api/client';
import type {
    UsageSummary,
    SessionUsage,
    DailyCost,
    ProviderCost,
    ModelCost,
} from '@/types/usage';

export const usageKeys = {
    all: ['usage'] as const,
    summary: (startDate?: string, endDate?: string, provider?: string) =>
        [...usageKeys.all, 'summary', startDate, endDate, provider] as const,
    session: (sessionId: string) =>
        [...usageKeys.all, 'session', sessionId] as const,
};

function buildQueryString(params: Record<string, string>): string {
    const entries = Object.entries(params).filter(([, v]) => v);
    if (entries.length === 0) return '';
    return '?' + entries.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
}

export const useUsageSummary = (
    startDate?: string,
    endDate?: string,
    provider?: string,
) => {
    return useQuery({
        queryKey: usageKeys.summary(startDate, endDate, provider),
        queryFn: async () => {
            const params: Record<string, string> = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            if (provider) params.provider = provider;
            const qs = buildQueryString(params);
            return await fetchApi<UsageSummary>(`/v1/usage/summary${qs}`);
        },
        staleTime: 2 * 60 * 1000, // 2 minutes
    });
};

export const useSessionUsage = (sessionId: string) => {
    return useQuery({
        queryKey: usageKeys.session(sessionId),
        queryFn: async () => {
            return await fetchApi<SessionUsage>(
                `/v1/usage/session/${encodeURIComponent(sessionId)}`,
            );
        },
        enabled: !!sessionId,
        staleTime: 2 * 60 * 1000,
    });
};

/** Derive daily costs from the cached summary query. */
export const useDailyCosts = (
    startDate?: string,
    endDate?: string,
): { data: DailyCost[] | undefined; isLoading: boolean } => {
    const { data, isLoading } = useUsageSummary(startDate, endDate);
    return { data: data?.daily, isLoading };
};

/** Derive provider breakdown from the cached summary query. */
export const useCostByProvider = (
    startDate?: string,
    endDate?: string,
): { data: ProviderCost[] | undefined; isLoading: boolean } => {
    const { data, isLoading } = useUsageSummary(startDate, endDate);
    return { data: data?.by_provider, isLoading };
};

/** Derive model breakdown from the cached summary query. */
export const useCostByModel = (
    startDate?: string,
    endDate?: string,
): { data: ModelCost[] | undefined; isLoading: boolean } => {
    const { data, isLoading } = useUsageSummary(startDate, endDate);
    return { data: data?.by_model, isLoading };
};
