/**
 * ============================================================================
 * FILE: useUsageApi.ts
 * LOCATION: frontend/src/features/usage/hooks/useUsageApi.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TanStack Query hooks for usage tracking API endpoints
 *
 * ROLE IN PROJECT:
 *    Provides query hooks for fetching AI usage summaries and session costs.
 *    The summary endpoint returns all breakdowns (daily, by-provider, by-model)
 *    in a single response - derived hooks select from cached result to avoid
 *    redundant Redis scans on the backend
 *
 * KEY COMPONENTS:
 *    - usageKeys: Query key factory for cache invalidation
 *    - useUsageSummary: Hook for complete usage breakdowns
 *    - useSessionUsage: Hook for specific session cost details
 *    - useDailyUsage, useProviderUsage, useModelUsage: Derived selectors
 *
 * DEPENDENCIES:
 *    - External: @tanstack/react-query
 *    - Internal: @/api/client, @/types/usage
 *
 * USAGE:
 *    const { data: summary } = useUsageSummary();
 *    const { data: session } = useSessionUsage(sessionId);
 * ============================================================================
 */
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
