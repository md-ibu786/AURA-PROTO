/**
 * ============================================================================
 * FILE: useKGQuery.ts
 * LOCATION: frontend/src/features/kg-query/hooks/useKGQuery.ts
 * ============================================================================
 *
 * PURPOSE:
 *    React hooks for Knowledge Graph query operations. Provides state
 *    management, caching, and error handling for search, multi-document
 *    queries, graph data retrieval, and feedback submission.
 *
 * ROLE IN PROJECT:
 *    Data fetching layer for KG query feature. Used by:
 *    - KGQueryPage for search and result display
 *    - EntityGraph component for graph visualization
 *    - SearchResultsList for feedback submission
 *
 * @see: api/kg-query.api.ts - API client functions
 * @see: types/kg-query.types.ts - Type definitions
 * @note: Uses @tanstack/react-query for caching and state management
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { kgQueryApi } from '../api/kg-query.api';
import {
    AnswerFeedback,
    GraphData,
    GraphSchema,
    MultiDocRequest,
    MultiDocResponse,
    ResultFeedback,
    SearchRequest,
    SearchResponse,
} from '../types/kg-query.types';

// ============================================================================
// QUERY KEYS
// ============================================================================

export const kgQueryKeys = {
    all: ['kg-query'] as const,
    search: (query: string) => [...kgQueryKeys.all, 'search', query] as const,
    graphData: (moduleId?: string, entityTypes?: string[]) =>
        [...kgQueryKeys.all, 'graph-data', moduleId, entityTypes] as const,
    graphSchema: () => [...kgQueryKeys.all, 'graph-schema'] as const,
    feedbackStats: (moduleId?: string) => [...kgQueryKeys.all, 'feedback-stats', moduleId] as const,
};

// ============================================================================
// SEARCH HOOKS
// ============================================================================

/**
 * Hook for performing KG searches and multi-document queries.
 *
 * Provides:
 * - search mutation for hybrid search
 * - multiDocQuery mutation for cross-document reasoning
 * - Loading and error states
 * - Result caching
 *
 * @example
 * ```tsx
 * const { search, isSearching, searchResults } = useKGQuery();
 * search({ query: 'machine learning', moduleIds: ['CS101'] });
 * ```
 */
export function useKGQuery() {
    const queryClient = useQueryClient();

    const searchMutation = useMutation({
        mutationFn: (request: SearchRequest) => kgQueryApi.search(request),
        onSuccess: (data, variables) => {
            // Cache the search results
            queryClient.setQueryData(kgQueryKeys.search(variables.query), data);
        },
        onError: (error) => {
            console.error('Search failed:', error);
        },
    });

    const multiDocMutation = useMutation({
        mutationFn: (request: MultiDocRequest) => kgQueryApi.multiDocQuery(request),
        onError: (error) => {
            console.error('Multi-doc query failed:', error);
        },
    });

    return {
        // Search operations
        search: searchMutation.mutate,
        searchAsync: searchMutation.mutateAsync,
        isSearching: searchMutation.isPending,
        searchResults: searchMutation.data as SearchResponse | undefined,
        searchError: searchMutation.error,
        resetSearch: searchMutation.reset,

        // Multi-document query operations
        multiDocQuery: multiDocMutation.mutate,
        multiDocQueryAsync: multiDocMutation.mutateAsync,
        isMultiDocQuerying: multiDocMutation.isPending,
        multiDocResults: multiDocMutation.data as MultiDocResponse | undefined,
        multiDocError: multiDocMutation.error,
        resetMultiDoc: multiDocMutation.reset,
    };
}

// ============================================================================
// GRAPH DATA HOOKS
// ============================================================================

/**
 * Hook for fetching graph data for visualization.
 *
 * @param moduleId - Optional module ID to filter graph data
 * @param entityTypes - Optional entity types to include
 * @param limit - Maximum nodes to return (default 100)
 * @param enabled - Whether to fetch data (default true when moduleId provided)
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useGraphData('CS101', ['Topic', 'Concept']);
 * ```
 */
export function useGraphData(
    moduleId?: string,
    entityTypes?: string[],
    limit: number = 100,
    enabled: boolean = true
) {
    return useQuery<GraphData>({
        queryKey: kgQueryKeys.graphData(moduleId, entityTypes),
        queryFn: () => kgQueryApi.getGraphData(moduleId, entityTypes, limit),
        enabled: enabled && !!moduleId,
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes
    });
}

/**
 * Hook for fetching graph schema information.
 *
 * @example
 * ```tsx
 * const { data: schema, isLoading } = useGraphSchema();
 * console.log(schema?.nodeTypes);
 * ```
 */
export function useGraphSchema() {
    return useQuery<GraphSchema>({
        queryKey: kgQueryKeys.graphSchema(),
        queryFn: () => kgQueryApi.getGraphSchema(),
        staleTime: 30 * 60 * 1000, // 30 minutes
        gcTime: 60 * 60 * 1000, // 1 hour
    });
}

// ============================================================================
// FEEDBACK HOOKS
// ============================================================================

/**
 * Hook for submitting result and answer feedback.
 *
 * @example
 * ```tsx
 * const { submitResultFeedback, submitAnswerFeedback } = useFeedback();
 * submitResultFeedback({ query: '...', resultId: '...', relevanceScore: 0.8 });
 * ```
 */
export function useFeedback() {
    const queryClient = useQueryClient();

    const resultFeedbackMutation = useMutation({
        mutationFn: (feedback: ResultFeedback) => kgQueryApi.submitResultFeedback(feedback),
        onSuccess: () => {
            // Invalidate feedback stats cache
            queryClient.invalidateQueries({ queryKey: kgQueryKeys.feedbackStats() });
        },
        onError: (error) => {
            console.error('Failed to submit result feedback:', error);
        },
    });

    const answerFeedbackMutation = useMutation({
        mutationFn: (feedback: AnswerFeedback) => kgQueryApi.submitAnswerFeedback(feedback),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: kgQueryKeys.feedbackStats() });
        },
        onError: (error) => {
            console.error('Failed to submit answer feedback:', error);
        },
    });

    return {
        submitResultFeedback: resultFeedbackMutation.mutate,
        submitResultFeedbackAsync: resultFeedbackMutation.mutateAsync,
        isSubmittingResultFeedback: resultFeedbackMutation.isPending,
        resultFeedbackError: resultFeedbackMutation.error,

        submitAnswerFeedback: answerFeedbackMutation.mutate,
        submitAnswerFeedbackAsync: answerFeedbackMutation.mutateAsync,
        isSubmittingAnswerFeedback: answerFeedbackMutation.isPending,
        answerFeedbackError: answerFeedbackMutation.error,
    };
}

/**
 * Hook for fetching feedback statistics.
 *
 * @param moduleId - Optional module ID to filter stats
 *
 * @example
 * ```tsx
 * const { data: stats } = useFeedbackStats('CS101');
 * console.log(stats?.positiveFeedbackRatio);
 * ```
 */
export function useFeedbackStats(moduleId?: string) {
    return useQuery({
        queryKey: kgQueryKeys.feedbackStats(moduleId),
        queryFn: () => kgQueryApi.getFeedbackStats(moduleId),
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
