/**
 * ============================================================================
 * FILE: kg-query.types.ts
 * LOCATION: frontend/src/features/kg-query/types/kg-query.types.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TypeScript type definitions for the Knowledge Graph Query feature.
 *    Defines interfaces for search requests, results, graph visualization,
 *    and feedback submission.
 *
 * ROLE IN PROJECT:
 *    Central type definitions for KG query operations. Used by:
 *    - useKGQuery hook for React Query queries/mutations
 *    - KGSearchBar component for search request building
 *    - SearchResultsList component for result display
 *    - EntityGraph component for graph visualization
 *    - KGQueryPage for integrating all components
 *
 * @see: api/kg-query.api.ts - API client using these types
 * @see: hooks/useKGQuery.ts - React hooks using these types
 * @see: components/*.tsx - UI components using these types
 */

// ============================================================================
// SEARCH REQUEST TYPES
// ============================================================================

export interface QueryExpansionConfig {
    enabled: boolean;
    maxExpansionTerms: number;
    minTermWeight: number;
}

export interface GraphExpansionConfig {
    enabled: boolean;
    maxHops: number;
    maxExpandedEntities: number;
}

export interface SearchRequest {
    query: string;
    moduleIds?: string[];
    topK?: number;
    vectorWeight?: number;
    fulltextWeight?: number;
    queryExpansion?: QueryExpansionConfig;
    graphExpansion?: GraphExpansionConfig;
}

export interface MultiDocRequest {
    query: string;
    moduleIds: string[];
    maxDocuments?: number;
    maxChunksPerDocument?: number;
    includeEntityContext?: boolean;
    detectContradictions?: boolean;
    citationStyle?: 'inline' | 'footnote' | 'reference';
}

// ============================================================================
// SEARCH RESPONSE TYPES
// ============================================================================

export interface EntityContext {
    entityId: string;
    entityName: string;
    entityType: string;
    definition?: string;
    relationshipToQuery: string;
    hopsFromResult: number;
    relevanceScore: number;
}

export interface SearchResult {
    id: string;
    nodeType: 'Chunk' | 'ParentChunk' | 'Entity';
    text: string;
    score: number;
    vectorScore?: number;
    fulltextScore?: number;
    documentId: string;
    documentTitle?: string;
    moduleId?: string;
    parentContext?: string;
    entities: string[];
    relatedEntities?: EntityContext[];
}

export interface ExpansionTerm {
    term: string;
    weight: number;
    source: string;
}

export interface ExpansionInfo {
    originalQuery: string;
    expandedQuery: string;
    expansionTerms: ExpansionTerm[];
    entitiesIdentified: string[];
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
    totalCount: number;
    searchTimeMs: number;
    weights: Record<string, number>;
    expansionInfo?: ExpansionInfo;
    graphContext?: Record<string, unknown>;
}

export interface Citation {
    index: number;
    documentId: string;
    documentTitle: string;
    chunkId: string;
    text: string;
}

export interface Contradiction {
    claim1: string;
    claim2: string;
    source1: string;
    source2: string;
    explanation: string;
}

export interface MultiDocResponse {
    answer: string;
    citations: Citation[];
    contradictions: Contradiction[];
    sourcesUsed: number;
    confidence: number;
    processingTimeMs: number;
}

// ============================================================================
// GRAPH VISUALIZATION TYPES
// ============================================================================

export interface GraphNode {
    id: string;
    label: string;
    name: string;
    type: string;
    properties: Record<string, unknown>;
    x?: number;
    y?: number;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    properties: Record<string, unknown>;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
    nodeCount: number;
    edgeCount: number;
    moduleId?: string;
}

export interface NodeTypeSchema {
    name: string;
    properties: string[];
    count: number;
    hasEmbedding: boolean;
}

export interface RelationshipTypeSchema {
    name: string;
    sourceTypes: string[];
    targetTypes: string[];
    properties: string[];
    count: number;
}

export interface GraphSchema {
    nodeTypes: NodeTypeSchema[];
    relationshipTypes: RelationshipTypeSchema[];
    totalNodes: number;
    totalRelationships: number;
    lastUpdated: string;
}

// ============================================================================
// FEEDBACK TYPES
// ============================================================================

export interface ResultFeedback {
    query: string;
    resultId: string;
    resultRank: number;
    relevanceScore: number;
    sessionId?: string;
    moduleIds?: string[];
    comment?: string;
}

export interface AnswerFeedback {
    query: string;
    answerHash: string;
    helpful: boolean;
    accuracyScore?: number;
    sessionId?: string;
    moduleIds?: string[];
    comment?: string;
}

export interface ImplicitFeedback {
    query: string;
    resultId: string;
    resultRank: number;
    feedbackType: 'click' | 'dwell_time';
    dwellTimeMs?: number;
    sessionId?: string;
}

export interface FeedbackResponse {
    feedbackId: string;
    status: string;
    message: string;
}

export interface FeedbackStats {
    totalFeedbackCount: number;
    positiveFeedbackRatio: number;
    averageRelevanceScore: number;
    feedbackByType: Record<string, number>;
    feedbackByModule: Record<string, number>;
    timeRangeStart?: string;
    timeRangeEnd?: string;
}

export interface LowQualityResult {
    resultId: string;
    resultType: string;
    averageRelevance: number;
    feedbackCount: number;
    sampleQueries: string[];
}

// ============================================================================
// ANALYSIS TYPES
// ============================================================================

export type AnalysisOperation = 'summarize' | 'compare' | 'extract' | 'explain';

export interface AnalysisRequest {
    operation: AnalysisOperation;
    targetIds: string[];
    options?: Record<string, unknown>;
}

export interface AnalysisResponse {
    operation: AnalysisOperation;
    result: unknown;
    processingTimeMs: number;
    modelUsed: string;
}

// ============================================================================
// MODULE TYPES (for dropdowns)
// ============================================================================

export interface Module {
    id: string;
    name: string;
    documentCount?: number;
}

// ============================================================================
// UNIFIED GRAPH VISUALIZATION TYPES (Phase 11-05)
// ============================================================================

export type LayoutType = 'force_directed' | 'hierarchical' | 'radial' | 'circular';

export type ExportFormat = 'json' | 'graphml' | 'gexf' | 'csv';

export interface GraphOptions {
    includeEntityTypes?: string[];
    excludeEntityTypes?: string[];
    includeRelationshipTypes?: string[];
    excludeRelationshipTypes?: string[];
    maxNodes?: number;
    includeChunks?: boolean;
    includeDocuments?: boolean;
    layout?: LayoutType;
    groupBy?: 'type' | 'module' | 'document';
}

export interface VisualizationNode {
    id: string;
    label: string;
    type: string;
    group?: string;
    size: number;
    color?: string;
    x?: number;
    y?: number;
    properties: Record<string, unknown>;
}

export interface VisualizationEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    weight: number;
    color?: string;
    properties: Record<string, unknown>;
}

export interface GraphMetadata {
    moduleIds: string[];
    documentIds: string[];
    nodeCount: number;
    edgeCount: number;
    entityTypeCounts: Record<string, number>;
    relationshipTypeCounts: Record<string, number>;
    generatedAt: string;
    optionsUsed?: GraphOptions;
}

export interface VisualizationGraph {
    nodes: VisualizationNode[];
    edges: VisualizationEdge[];
    metadata: GraphMetadata;
    layoutApplied: boolean;
}

export interface GraphViewOptions {
    showLabels: boolean;
    labelSize: number;
    nodeSize: 'fixed' | 'by_connections' | 'by_property';
    nodeSizeProperty?: string;
    edgeWidth: 'fixed' | 'by_weight';
    enableZoom: boolean;
    enablePan: boolean;
    highlightOnHover: boolean;
}
