/**
 * ============================================================================
 * FILE: SearchResultsList.tsx
 * LOCATION: frontend/src/features/kg-query/components/SearchResultsList.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Display search results with relevance scores, citations, and feedback
 *    options. Each result card shows text preview, source document, entities,
 *    and allows users to rate relevance.
 *
 * ROLE IN PROJECT:
 *    Results display for KG query feature. Shows search results and collects
 *    user feedback for continuous improvement.
 *
 * @see: types/kg-query.types.ts - SearchResult, ResultFeedback types
 * @see: hooks/useKGQuery.ts - useFeedback hook
 * @see: pages/KGQueryPage.tsx - Parent component
 */

import { useState, useCallback } from 'react';
import {
    ThumbsUp,
    ThumbsDown,
    ChevronDown,
    ChevronUp,
    FileText,
    Tag,
    Copy,
    Check,
} from 'lucide-react';
import { ResultFeedback, SearchResult, SearchResponse } from '../types/kg-query.types';

interface SearchResultsListProps {
    response: SearchResponse;
    onFeedback: (feedback: ResultFeedback) => void;
    onResultClick?: (result: SearchResult) => void;
}

interface SearchResultCardProps {
    result: SearchResult;
    rank: number;
    query: string;
    onFeedback: (feedback: ResultFeedback) => void;
    onClick?: (result: SearchResult) => void;
}

function SearchResultCard({
    result,
    rank,
    query,
    onFeedback,
    onClick,
}: SearchResultCardProps) {
    const [expanded, setExpanded] = useState(false);
    const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
    const [copied, setCopied] = useState(false);

    const handleFeedback = useCallback(
        (isPositive: boolean) => {
            if (feedbackGiven) return; // Already gave feedback

            onFeedback({
                query,
                resultId: result.id,
                resultRank: rank,
                relevanceScore: isPositive ? 1.0 : 0.0,
            });
            setFeedbackGiven(isPositive ? 'positive' : 'negative');
        },
        [query, result.id, rank, feedbackGiven, onFeedback]
    );

    const copyToClipboard = useCallback(() => {
        const citation = `[${result.documentTitle || result.documentId}] "${result.text.slice(0, 100)}..."`;
        navigator.clipboard.writeText(citation);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [result]);

    const scorePercent = Math.round(result.score * 100);
    const displayText = expanded ? result.text : result.text.slice(0, 200);
    const needsExpansion = result.text.length > 200;

    return (
        <div
            className={`result-card ${onClick ? 'clickable' : ''}`}
            onClick={() => onClick?.(result)}
        >
            {/* Header with rank and score */}
            <div className="result-header">
                <span className="result-rank">#{rank + 1}</span>
                <div className="result-type-badge">{result.nodeType}</div>
                <div className="score-bar-container">
                    <div
                        className="score-bar"
                        style={{ width: `${scorePercent}%` }}
                        title={`Relevance: ${scorePercent}%`}
                    />
                    <span className="score-text">{scorePercent}%</span>
                </div>
            </div>

            {/* Result text */}
            <div className="result-text">
                {displayText}
                {needsExpansion && !expanded && '...'}
            </div>

            {needsExpansion && (
                <button
                    className="expand-button"
                    onClick={(e) => {
                        e.stopPropagation();
                        setExpanded(!expanded);
                    }}
                >
                    {expanded ? (
                        <>
                            <ChevronUp size={16} /> Show less
                        </>
                    ) : (
                        <>
                            <ChevronDown size={16} /> Show more
                        </>
                    )}
                </button>
            )}

            {/* Parent context */}
            {result.parentContext && (
                <div className="parent-context">
                    <span className="context-label">Context:</span>
                    {result.parentContext}
                </div>
            )}

            {/* Entities */}
            {result.entities.length > 0 && (
                <div className="result-entities">
                    <Tag size={14} />
                    {result.entities.slice(0, 5).map((entity, i) => (
                        <span key={i} className="entity-tag">
                            {entity}
                        </span>
                    ))}
                    {result.entities.length > 5 && (
                        <span className="more-entities">+{result.entities.length - 5} more</span>
                    )}
                </div>
            )}

            {/* Source and actions */}
            <div className="result-footer">
                <div className="source-info">
                    <FileText size={14} />
                    <span>{result.documentTitle || result.documentId}</span>
                    {result.moduleId && (
                        <span className="module-badge">{result.moduleId}</span>
                    )}
                </div>

                <div className="result-actions">
                    <button
                        className="action-button copy"
                        onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard();
                        }}
                        title="Copy citation"
                    >
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                    </button>

                    <div className="feedback-buttons">
                        <button
                            className={`action-button feedback ${feedbackGiven === 'positive' ? 'active positive' : ''}`}
                            onClick={(e) => {
                                e.stopPropagation();
                                handleFeedback(true);
                            }}
                            disabled={feedbackGiven !== null}
                            title="Relevant"
                        >
                            <ThumbsUp size={16} />
                        </button>
                        <button
                            className={`action-button feedback ${feedbackGiven === 'negative' ? 'active negative' : ''}`}
                            onClick={(e) => {
                                e.stopPropagation();
                                handleFeedback(false);
                            }}
                            disabled={feedbackGiven !== null}
                            title="Not relevant"
                        >
                            <ThumbsDown size={16} />
                        </button>
                    </div>
                </div>
            </div>

            <style>{`
                .result-card {
                    background: var(--surface-2);
                    border: 1px solid var(--border-1);
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    transition: border-color 0.2s, box-shadow 0.2s;
                }

                .result-card.clickable {
                    cursor: pointer;
                }

                .result-card:hover {
                    border-color: var(--primary);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }

                .result-header {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 12px;
                }

                .result-rank {
                    font-weight: 600;
                    color: var(--text-2);
                    font-size: 14px;
                }

                .result-type-badge {
                    background: var(--surface-3);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: var(--text-2);
                }

                .score-bar-container {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    max-width: 200px;
                }

                .score-bar {
                    height: 6px;
                    background: linear-gradient(to right, var(--primary), var(--success));
                    border-radius: 3px;
                    transition: width 0.3s ease;
                }

                .score-text {
                    font-size: 12px;
                    font-weight: 500;
                    color: var(--text-2);
                    min-width: 40px;
                }

                .result-text {
                    color: var(--text-1);
                    line-height: 1.6;
                    margin-bottom: 12px;
                }

                .expand-button {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    background: none;
                    border: none;
                    color: var(--primary);
                    cursor: pointer;
                    font-size: 14px;
                    padding: 0;
                    margin-bottom: 12px;
                }

                .parent-context {
                    background: var(--surface-1);
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 14px;
                    color: var(--text-2);
                    margin-bottom: 12px;
                }

                .context-label {
                    font-weight: 500;
                    margin-right: 8px;
                }

                .result-entities {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 12px;
                    color: var(--text-2);
                }

                .entity-tag {
                    background: var(--primary-light);
                    color: var(--primary);
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                }

                .more-entities {
                    font-size: 12px;
                    color: var(--text-3);
                }

                .result-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding-top: 12px;
                    border-top: 1px solid var(--border-1);
                }

                .source-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    color: var(--text-2);
                }

                .module-badge {
                    background: var(--surface-3);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 11px;
                }

                .result-actions {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .feedback-buttons {
                    display: flex;
                    gap: 4px;
                }

                .action-button {
                    background: none;
                    border: 1px solid var(--border-1);
                    border-radius: 4px;
                    padding: 6px;
                    cursor: pointer;
                    color: var(--text-2);
                    transition: all 0.2s;
                }

                .action-button:hover:not(:disabled) {
                    background: var(--surface-3);
                    color: var(--text-1);
                }

                .action-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .action-button.feedback.active.positive {
                    background: var(--success-light);
                    color: var(--success);
                    border-color: var(--success);
                }

                .action-button.feedback.active.negative {
                    background: var(--error-light);
                    color: var(--error);
                    border-color: var(--error);
                }

                .action-button.copy {
                    border: none;
                }
            `}</style>
        </div>
    );
}

export function SearchResultsList({
    response,
    onFeedback,
    onResultClick,
}: SearchResultsListProps) {
    return (
        <div className="search-results-list">
            {/* Results header */}
            <div className="results-header">
                <h3>
                    {response.totalCount} result{response.totalCount !== 1 ? 's' : ''} for "
                    {response.query}"
                </h3>
                <span className="search-time">{response.searchTimeMs.toFixed(0)}ms</span>
            </div>

            {/* Expansion info */}
            {response.expansionInfo && (
                <div className="expansion-info">
                    <span className="expansion-label">Query expanded:</span>
                    <span className="expanded-query">{response.expansionInfo.expandedQuery}</span>
                </div>
            )}

            {/* Results list */}
            <div className="results-container">
                {response.results.map((result, index) => (
                    <SearchResultCard
                        key={result.id}
                        result={result}
                        rank={index}
                        query={response.query}
                        onFeedback={onFeedback}
                        onClick={onResultClick}
                    />
                ))}
            </div>

            {response.results.length === 0 && (
                <div className="no-results">
                    <p>No results found for your query.</p>
                    <p>Try adjusting your search terms or expanding your module filter.</p>
                </div>
            )}

            <style>{`
                .search-results-list {
                    padding: 0;
                }

                .results-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                }

                .results-header h3 {
                    margin: 0;
                    font-size: 16px;
                    color: var(--text-1);
                }

                .search-time {
                    font-size: 14px;
                    color: var(--text-3);
                }

                .expansion-info {
                    background: var(--surface-1);
                    padding: 12px;
                    border-radius: 6px;
                    margin-bottom: 16px;
                    font-size: 14px;
                }

                .expansion-label {
                    color: var(--text-2);
                    margin-right: 8px;
                }

                .expanded-query {
                    color: var(--primary);
                    font-style: italic;
                }

                .results-container {
                    max-height: calc(100vh - 300px);
                    overflow-y: auto;
                }

                .no-results {
                    text-align: center;
                    padding: 48px;
                    color: var(--text-2);
                }

                .no-results p {
                    margin: 8px 0;
                }
            `}</style>
        </div>
    );
}
