// usage.ts
// TypeScript types for usage tracking and cost dashboard API responses

// Defines interfaces for daily costs, provider/model breakdowns,
// session usage summaries, and SSE completion usage payloads.
// All types match the backend API response shapes from Plan 12-02.

// @see: features/usage/hooks/useUsageApi.ts - TanStack Query hooks consuming these types
// @note: All cost values are in USD. Token counts may be estimated.

export interface DailyCost {
    date: string;
    cost: number;
    requests: number;
}

export interface ProviderCost {
    provider: string;
    cost: number;
    requests: number;
}

export interface ModelCost {
    model: string;
    provider: string;
    cost: number;
    requests: number;
}

export interface SessionUsage {
    total_cost: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_thinking_tokens: number;
    request_count: number;
}

export interface UsageSummary {
    total_cost: number;
    total_requests: number;
    by_provider: ProviderCost[];
    by_model: ModelCost[];
    daily: DailyCost[];
}

export interface UsageCompletionData {
    input_tokens: number;
    output_tokens: number;
    thinking_tokens: number;
    estimated_cost_usd: number;
    is_estimated: boolean;
}
