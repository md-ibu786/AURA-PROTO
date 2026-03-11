// useUsageApi.ts
// TanStack Query hooks for usage tracking API endpoints

// Provides query hooks for fetching usage summaries, session costs,
// daily cost trends, and cost breakdowns by provider and model.
// Uses fetchApi client adapted for AURA-NOTES-MANAGER conventions.

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
    daily: (startDate?: string, endDate?: string) =>
        [...usageKeys.all, 'daily', startDate, endDate] as const,
    byProvider: (startDate?: string, endDate?: string) =>
        [...usageKeys.all, 'byProvider', startDate, endDate] as const,
    byModel: (startDate?: string, endDate?: string) =>
        [...usageKeys.all, 'byModel', startDate, endDate] as const,
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

export const useDailyCosts = (startDate?: string, endDate?: string) => {
    return useQuery({
        queryKey: usageKeys.daily(startDate, endDate),
        queryFn: async () => {
            const params: Record<string, string> = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            const qs = buildQueryString(params);
            return await fetchApi<DailyCost[]>(`/v1/usage/daily${qs}`);
        },
        staleTime: 2 * 60 * 1000,
    });
};

export const useCostByProvider = (startDate?: string, endDate?: string) => {
    return useQuery({
        queryKey: usageKeys.byProvider(startDate, endDate),
        queryFn: async () => {
            const params: Record<string, string> = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            const qs = buildQueryString(params);
            return await fetchApi<ProviderCost[]>(`/v1/usage/by-provider${qs}`);
        },
        staleTime: 2 * 60 * 1000,
    });
};

export const useCostByModel = (startDate?: string, endDate?: string) => {
    return useQuery({
        queryKey: usageKeys.byModel(startDate, endDate),
        queryFn: async () => {
            const params: Record<string, string> = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            const qs = buildQueryString(params);
            return await fetchApi<ModelCost[]>(`/v1/usage/by-model${qs}`);
        },
        staleTime: 2 * 60 * 1000,
    });
};
