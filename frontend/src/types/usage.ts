/**
 * ============================================================================
 * FILE: usage.ts
 * LOCATION: frontend/src/types/usage.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TypeScript types for usage tracking and cost dashboard API responses
 *
 * ROLE IN PROJECT:
 *    Defines interfaces for daily costs, provider/model breakdowns, session
 *    usage summaries, and SSE completion usage payloads. All types match the
 *    backend API response shapes to ensure type safety in API communication
 *
 * KEY COMPONENTS:
 *    - DailyCost: Daily aggregated costs and request counts
 *    - ProviderCost: Cost breakdown by AI provider
 *    - ModelCost: Cost breakdown by specific model
 *    - SessionUsage: Per-session cost and token usage
 *    - UsageSummary: Aggregated view of all cost breakdowns
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None
 *
 * USAGE:
 *    import type { UsageSummary, SessionUsage, DailyCost } from '@/types/usage';
 * ============================================================================
 */
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
