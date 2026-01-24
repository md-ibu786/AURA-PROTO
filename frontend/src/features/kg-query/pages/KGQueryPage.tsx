/**
 * ============================================================================
 * FILE: KGQueryPage.tsx
 * LOCATION: frontend/src/features/kg-query/pages/KGQueryPage.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Main page for Knowledge Graph query and exploration. Combines search bar,
 *    results list, and entity graph visualization into a complete interface.
 *
 * ROLE IN PROJECT:
 *    Entry point for the KG query feature. Integrates all KG query components
 *    and manages state across search, results, and graph panels.
 *
 * @see: components/KGSearchBar.tsx - Search input component
 * @see: components/SearchResultsList.tsx - Results display component
 * @see: components/EntityGraph.tsx - Graph visualization component
 * @see: hooks/useKGQuery.ts - Data fetching hooks
 */

import { useState, useCallback, useEffect } from 'react';
import { ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { KGSearchBar } from '../components/KGSearchBar';
import { SearchResultsList } from '../components/SearchResultsList';
import { EntityGraph } from '../components/EntityGraph';
import { useKGQuery, useGraphData, useFeedback } from '../hooks/useKGQuery';
import { Module, ResultFeedback, SearchResult, GraphNode } from '../types/kg-query.types';

// Mock modules for now - in production, fetch from API
const MOCK_MODULES: Module[] = [
    { id: 'CS101', name: 'Introduction to CS', documentCount: 15 },
    { id: 'CS201', name: 'Data Structures', documentCount: 23 },
    { id: 'CS301', name: 'Algorithms', documentCount: 18 },
    { id: 'ML101', name: 'Machine Learning', documentCount: 12 },
];

export function KGQueryPage() {
    const navigate = useNavigate();
    const [selectedModuleId, setSelectedModuleId] = useState<string | undefined>();
    const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

    // Search hook
    const {
        search,
        isSearching,
        searchResults,
        searchError,
        resetSearch,
    } = useKGQuery();

    // Graph data hook
    const {
        data: graphData,
        isLoading: isGraphLoading,
        error: graphError,
    } = useGraphData(selectedModuleId);

    // Feedback hook
    const { submitResultFeedback } = useFeedback();

    // Handle feedback submission
    const handleFeedback = useCallback(
        (feedback: ResultFeedback) => {
            submitResultFeedback(feedback, {
                onSuccess: () => {
                    toast.success('Feedback submitted');
                },
                onError: (error) => {
                    toast.error(`Failed to submit feedback: ${error.message}`);
                },
            });
        },
        [submitResultFeedback]
    );

    // Handle result click - could show details or highlight in graph
    const handleResultClick = useCallback((result: SearchResult) => {
        setSelectedResult(result);
        // If result has a moduleId, update graph to show that module
        if (result.moduleId) {
            setSelectedModuleId(result.moduleId);
        }
    }, []);

    // Handle graph node click
    const handleNodeClick = useCallback((node: GraphNode) => {
        toast.info(`Selected: ${node.name} (${node.type})`);
    }, []);

    // Update module selection when search results come in
    useEffect(() => {
        if (searchResults?.results[0]?.moduleId) {
            setSelectedModuleId(searchResults.results[0].moduleId);
        }
    }, [searchResults]);

    return (
        <div className="kg-query-page">
            {/* Header */}
            <header className="page-header">
                <button className="back-button" onClick={() => navigate('/')}>
                    <ArrowLeft size={20} />
                </button>
                <h1>Knowledge Graph Query</h1>
            </header>

            {/* Search bar */}
            <KGSearchBar
                onSearch={search}
                isSearching={isSearching}
                modules={MOCK_MODULES}
            />

            {/* Error display */}
            {searchError && (
                <div className="error-banner">
                    <AlertCircle size={20} />
                    <span>Search failed: {searchError.message}</span>
                    <button onClick={resetSearch}>Dismiss</button>
                </div>
            )}

            {/* Main content area */}
            <div className="query-content">
                {/* Results panel */}
                <div className="results-panel">
                    {isSearching && (
                        <div className="loading-state">
                            <Loader2 className="spinner" size={32} />
                            <p>Searching the knowledge graph...</p>
                        </div>
                    )}

                    {!isSearching && searchResults && (
                        <SearchResultsList
                            response={searchResults}
                            onFeedback={handleFeedback}
                            onResultClick={handleResultClick}
                        />
                    )}

                    {!isSearching && !searchResults && (
                        <div className="empty-state">
                            <h3>Search the Knowledge Graph</h3>
                            <p>
                                Enter a query above to search across documents using
                                hybrid vector + fulltext search with graph expansion.
                            </p>
                            <ul>
                                <li>Semantic search finds conceptually related content</li>
                                <li>Query expansion adds related terms automatically</li>
                                <li>Graph traversal enriches results with entity context</li>
                            </ul>
                        </div>
                    )}
                </div>

                {/* Graph panel */}
                <div className="graph-panel">
                    <div className="graph-header">
                        <h3>Entity Graph</h3>
                        {selectedModuleId && (
                            <span className="module-indicator">{selectedModuleId}</span>
                        )}
                    </div>

                    {isGraphLoading && (
                        <div className="loading-state">
                            <Loader2 className="spinner" size={24} />
                            <p>Loading graph...</p>
                        </div>
                    )}

                    {graphError && (
                        <div className="graph-error">
                            <AlertCircle size={20} />
                            <p>Failed to load graph data</p>
                        </div>
                    )}

                    {!isGraphLoading && graphData && (
                        <EntityGraph
                            data={graphData}
                            onNodeClick={handleNodeClick}
                            selectedNodeId={selectedResult?.id}
                            width={500}
                            height={400}
                        />
                    )}

                    {!isGraphLoading && !graphData && !selectedModuleId && (
                        <div className="graph-placeholder">
                            <p>Select a module to view its entity graph</p>
                        </div>
                    )}
                </div>
            </div>

            <style>{`
                .kg-query-page {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    background: var(--background);
                    padding: 16px;
                }

                .page-header {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    margin-bottom: 16px;
                }

                .back-button {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 40px;
                    height: 40px;
                    background: var(--surface-1);
                    border: 1px solid var(--border-1);
                    border-radius: 8px;
                    cursor: pointer;
                    color: var(--text-2);
                }

                .back-button:hover {
                    background: var(--surface-2);
                    color: var(--text-1);
                }

                .page-header h1 {
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                    color: var(--text-1);
                }

                .error-banner {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    background: var(--error-light);
                    color: var(--error);
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin-bottom: 16px;
                }

                .error-banner button {
                    margin-left: auto;
                    background: none;
                    border: none;
                    color: var(--error);
                    cursor: pointer;
                    text-decoration: underline;
                }

                .query-content {
                    display: grid;
                    grid-template-columns: 1fr 500px;
                    gap: 16px;
                    flex: 1;
                    min-height: 0;
                }

                @media (max-width: 1200px) {
                    .query-content {
                        grid-template-columns: 1fr;
                    }

                    .graph-panel {
                        max-height: 450px;
                    }
                }

                .results-panel {
                    background: var(--surface-1);
                    border: 1px solid var(--border-1);
                    border-radius: 8px;
                    padding: 16px;
                    overflow: hidden;
                }

                .graph-panel {
                    display: flex;
                    flex-direction: column;
                    background: var(--surface-1);
                    border: 1px solid var(--border-1);
                    border-radius: 8px;
                    overflow: hidden;
                }

                .graph-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    border-bottom: 1px solid var(--border-1);
                }

                .graph-header h3 {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 500;
                }

                .module-indicator {
                    background: var(--primary-light);
                    color: var(--primary);
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }

                .loading-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 200px;
                    color: var(--text-2);
                }

                .spinner {
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 48px;
                    color: var(--text-2);
                }

                .empty-state h3 {
                    margin: 0 0 12px 0;
                    color: var(--text-1);
                }

                .empty-state ul {
                    text-align: left;
                    margin-top: 16px;
                    padding-left: 20px;
                }

                .empty-state li {
                    margin: 8px 0;
                }

                .graph-error {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 200px;
                    color: var(--error);
                    gap: 8px;
                }

                .graph-placeholder {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 200px;
                    color: var(--text-3);
                }
            `}</style>
        </div>
    );
}

export default KGQueryPage;
