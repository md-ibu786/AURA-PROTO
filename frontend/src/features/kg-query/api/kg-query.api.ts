/**
 * ============================================================================
 * FILE: kg-query.api.ts
 * LOCATION: frontend/src/features/kg-query/api/kg-query.api.ts
 * ============================================================================
 *
 * PURPOSE:
 *    HTTP client functions for communicating with the Knowledge Graph Query
 *    backend endpoints. Provides typed API calls for search, multi-document
 *    queries, graph data retrieval, and feedback submission.
 *
 * ROLE IN PROJECT:
 *    API layer for KG query feature. Used by:
 *    - useKGQuery hook for search mutations
 *    - useGraphData hook for graph queries
 *    - Feedback submission from result cards
 *
 * @see: types/kg-query.types.ts - Type definitions
 * @see: hooks/useKGQuery.ts - React Query hooks using this API
 * @note: Base path is /v1/kg matching backend router prefix
 */

import { fetchApi } from '@/api/client';
import {
    AnalysisRequest,
    AnalysisResponse,
    AnswerFeedback,
    FeedbackResponse,
    FeedbackStats,
    GraphData,
    GraphSchema,
    ImplicitFeedback,
    LowQualityResult,
    MultiDocRequest,
    MultiDocResponse,
    ResultFeedback,
    SearchRequest,
    SearchResponse,
} from '../types/kg-query.types';

const BASE_PATH = '/v1/kg';

/**
 * Convert camelCase request to snake_case for backend API.
 */
function toSnakeCase(request: SearchRequest): Record<string, unknown> {
    return {
        query: request.query,
        module_ids: request.moduleIds,
        top_k: request.topK,
        vector_weight: request.vectorWeight,
        fulltext_weight: request.fulltextWeight,
        query_expansion: request.queryExpansion
            ? {
                  enabled: request.queryExpansion.enabled,
                  max_expansion_terms: request.queryExpansion.maxExpansionTerms,
                  min_term_weight: request.queryExpansion.minTermWeight,
              }
            : undefined,
        graph_expansion: request.graphExpansion
            ? {
                  enabled: request.graphExpansion.enabled,
                  max_hops: request.graphExpansion.maxHops,
                  max_expanded_entities: request.graphExpansion.maxExpandedEntities,
              }
            : undefined,
    };
}

/**
 * Convert snake_case response to camelCase for frontend.
 */
function fromSnakeCaseResponse(data: Record<string, unknown>): SearchResponse {
    const results = (data.results as Array<Record<string, unknown>>) || [];
    return {
        query: data.query as string,
        results: results.map((r) => ({
            id: r.id as string,
            nodeType: r.node_type as 'Chunk' | 'ParentChunk' | 'Entity',
            text: r.text as string,
            score: r.score as number,
            vectorScore: r.vector_score as number | undefined,
            fulltextScore: r.fulltext_score as number | undefined,
            documentId: r.document_id as string,
            documentTitle: r.document_title as string | undefined,
            moduleId: r.module_id as string | undefined,
            parentContext: r.parent_context as string | undefined,
            entities: (r.entities as string[]) || [],
            relatedEntities: r.related_entities as undefined,
        })),
        totalCount: data.total_count as number,
        searchTimeMs: data.search_time_ms as number,
        weights: data.weights as Record<string, number>,
        expansionInfo: data.expansion_info as undefined,
        graphContext: data.graph_context as Record<string, unknown> | undefined,
    };
}

/**
 * Knowledge Graph Query API client.
 */
export const kgQueryApi = {
    /**
     * Perform hybrid search with graph expansion.
     */
    search: async (request: SearchRequest): Promise<SearchResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/query`, {
            method: 'POST',
            body: JSON.stringify(toSnakeCase(request)),
        });
        return fromSnakeCaseResponse(data);
    },

    /**
     * Perform multi-document query with answer synthesis.
     */
    multiDocQuery: async (request: MultiDocRequest): Promise<MultiDocResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/query/multi-doc`, {
            method: 'POST',
            body: JSON.stringify({
                query: request.query,
                module_ids: request.moduleIds,
                max_documents: request.maxDocuments,
                max_chunks_per_document: request.maxChunksPerDocument,
                include_entity_context: request.includeEntityContext,
                detect_contradictions: request.detectContradictions,
                citation_style: request.citationStyle,
            }),
        });
        return {
            answer: data.answer as string,
            citations: ((data.citations as Array<Record<string, unknown>>) || []).map((c) => ({
                index: c.index as number,
                documentId: c.document_id as string,
                documentTitle: c.document_title as string,
                chunkId: c.chunk_id as string,
                text: c.text as string,
            })),
            contradictions: ((data.contradictions as Array<Record<string, unknown>>) || []).map(
                (c) => ({
                    claim1: c.claim1 as string,
                    claim2: c.claim2 as string,
                    source1: c.source1 as string,
                    source2: c.source2 as string,
                    explanation: c.explanation as string,
                })
            ),
            sourcesUsed: data.sources_used as number,
            confidence: data.confidence as number,
            processingTimeMs: data.processing_time_ms as number,
        };
    },

    /**
     * Analyze documents or chunks.
     */
    analyze: async (request: AnalysisRequest): Promise<AnalysisResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/analyze`, {
            method: 'POST',
            body: JSON.stringify({
                operation: request.operation,
                target_ids: request.targetIds,
                options: request.options,
            }),
        });
        return {
            operation: data.operation as AnalysisResponse['operation'],
            result: data.result,
            processingTimeMs: data.processing_time_ms as number,
            modelUsed: data.model_used as string,
        };
    },

    /**
     * Get graph schema information.
     */
    getGraphSchema: async (): Promise<GraphSchema> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/graph/schema`);
        return {
            nodeTypes: ((data.node_types as Array<Record<string, unknown>>) || []).map((nt) => ({
                name: nt.name as string,
                properties: nt.properties as string[],
                count: nt.count as number,
                hasEmbedding: nt.has_embedding as boolean,
            })),
            relationshipTypes: ((data.relationship_types as Array<Record<string, unknown>>) || []).map(
                (rt) => ({
                    name: rt.name as string,
                    sourceTypes: rt.source_types as string[],
                    targetTypes: rt.target_types as string[],
                    properties: rt.properties as string[],
                    count: rt.count as number,
                })
            ),
            totalNodes: data.total_nodes as number,
            totalRelationships: data.total_relationships as number,
            lastUpdated: data.last_updated as string,
        };
    },

    /**
     * Get graph data for visualization.
     */
    getGraphData: async (
        moduleId?: string,
        entityTypes?: string[],
        limit: number = 100
    ): Promise<GraphData> => {
        const params = new URLSearchParams();
        if (moduleId) params.append('module_id', moduleId);
        if (entityTypes) entityTypes.forEach((t) => params.append('entity_types', t));
        params.append('limit', limit.toString());

        const data = await fetchApi<Record<string, unknown>>(
            `${BASE_PATH}/graph/data?${params.toString()}`
        );
        return {
            nodes: ((data.nodes as Array<Record<string, unknown>>) || []).map((n) => ({
                id: n.id as string,
                label: n.label as string,
                name: n.name as string,
                type: n.label as string,
                properties: n.properties as Record<string, unknown>,
            })),
            edges: ((data.edges as Array<Record<string, unknown>>) || []).map((e) => ({
                id: e.id as string,
                source: e.source as string,
                target: e.target as string,
                type: e.type as string,
                properties: e.properties as Record<string, unknown>,
            })),
            nodeCount: data.node_count as number,
            edgeCount: data.edge_count as number,
            moduleId: data.module_id as string | undefined,
        };
    },

    /**
     * Submit result relevance feedback.
     */
    submitResultFeedback: async (feedback: ResultFeedback): Promise<FeedbackResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/feedback/result`, {
            method: 'POST',
            body: JSON.stringify({
                query: feedback.query,
                result_id: feedback.resultId,
                result_rank: feedback.resultRank,
                relevance_score: feedback.relevanceScore,
                session_id: feedback.sessionId,
                module_ids: feedback.moduleIds,
                comment: feedback.comment,
            }),
        });
        return {
            feedbackId: data.feedback_id as string,
            status: data.status as string,
            message: data.message as string,
        };
    },

    /**
     * Submit answer quality feedback.
     */
    submitAnswerFeedback: async (feedback: AnswerFeedback): Promise<FeedbackResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/feedback/answer`, {
            method: 'POST',
            body: JSON.stringify({
                query: feedback.query,
                answer_hash: feedback.answerHash,
                helpful: feedback.helpful,
                accuracy_score: feedback.accuracyScore,
                session_id: feedback.sessionId,
                module_ids: feedback.moduleIds,
                comment: feedback.comment,
            }),
        });
        return {
            feedbackId: data.feedback_id as string,
            status: data.status as string,
            message: data.message as string,
        };
    },

    /**
     * Submit implicit feedback (clicks, dwell time).
     */
    submitImplicitFeedback: async (feedback: ImplicitFeedback): Promise<FeedbackResponse> => {
        const data = await fetchApi<Record<string, unknown>>(`${BASE_PATH}/feedback/implicit`, {
            method: 'POST',
            body: JSON.stringify({
                query: feedback.query,
                result_id: feedback.resultId,
                result_rank: feedback.resultRank,
                feedback_type: feedback.feedbackType,
                dwell_time_ms: feedback.dwellTimeMs,
                session_id: feedback.sessionId,
            }),
        });
        return {
            feedbackId: data.feedback_id as string,
            status: data.status as string,
            message: data.message as string,
        };
    },

    /**
     * Get feedback statistics.
     */
    getFeedbackStats: async (moduleId?: string): Promise<FeedbackStats> => {
        const params = new URLSearchParams();
        if (moduleId) params.append('module_id', moduleId);

        const data = await fetchApi<Record<string, unknown>>(
            `${BASE_PATH}/feedback/stats?${params.toString()}`
        );
        return {
            totalFeedbackCount: data.total_feedback_count as number,
            positiveFeedbackRatio: data.positive_feedback_ratio as number,
            averageRelevanceScore: data.average_relevance_score as number,
            feedbackByType: data.feedback_by_type as Record<string, number>,
            feedbackByModule: data.feedback_by_module as Record<string, number>,
            timeRangeStart: data.time_range_start as string | undefined,
            timeRangeEnd: data.time_range_end as string | undefined,
        };
    },

    /**
     * Get low-quality results for review.
     */
    getLowQualityResults: async (threshold = 0.3, limit = 50): Promise<LowQualityResult[]> => {
        const params = new URLSearchParams();
        params.append('threshold', threshold.toString());
        params.append('limit', limit.toString());

        const data = await fetchApi<Array<Record<string, unknown>>>(
            `${BASE_PATH}/feedback/low-quality?${params.toString()}`
        );
        return data.map((r) => ({
            resultId: r.result_id as string,
            resultType: r.result_type as string,
            averageRelevance: r.average_relevance as number,
            feedbackCount: r.feedback_count as number,
            sampleQueries: r.sample_queries as string[],
        }));
    },
};
