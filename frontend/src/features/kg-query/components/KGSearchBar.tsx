/**
 * ============================================================================
 * FILE: KGSearchBar.tsx
 * LOCATION: frontend/src/features/kg-query/components/KGSearchBar.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Search bar component for Knowledge Graph queries. Provides text input,
 *    module filtering, and advanced search options.
 *
 * ROLE IN PROJECT:
 *    Main search interface for KG query feature. Builds search requests
 *    and triggers search operations via the useKGQuery hook.
 *
 * @see: hooks/useKGQuery.ts - Hook for search operations
 * @see: types/kg-query.types.ts - SearchRequest type
 * @see: pages/KGQueryPage.tsx - Parent component
 */

import React, { useState, useCallback } from 'react';
import { Search, Settings, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Module, SearchRequest } from '../types/kg-query.types';

interface KGSearchBarProps {
    onSearch: (request: SearchRequest) => void;
    isSearching: boolean;
    modules: Module[];
    defaultModuleIds?: string[];
}

interface SearchOptions {
    topK: number;
    vectorWeight: number;
    enableQueryExpansion: boolean;
    enableGraphExpansion: boolean;
    maxExpansionTerms: number;
    maxHops: number;
}

const defaultOptions: SearchOptions = {
    topK: 15,
    vectorWeight: 0.7,
    enableQueryExpansion: true,
    enableGraphExpansion: true,
    maxExpansionTerms: 10,
    maxHops: 2,
};

export function KGSearchBar({
    onSearch,
    isSearching,
    modules,
    defaultModuleIds = [],
}: KGSearchBarProps) {
    const [query, setQuery] = useState('');
    const [selectedModules, setSelectedModules] = useState<string[]>(defaultModuleIds);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [showModuleDropdown, setShowModuleDropdown] = useState(false);
    const [options, setOptions] = useState<SearchOptions>(defaultOptions);

    const handleSearch = useCallback(() => {
        if (!query.trim()) return;

        const request: SearchRequest = {
            query: query.trim(),
            moduleIds: selectedModules.length > 0 ? selectedModules : undefined,
            topK: options.topK,
            vectorWeight: options.vectorWeight,
            fulltextWeight: 1 - options.vectorWeight,
            queryExpansion: {
                enabled: options.enableQueryExpansion,
                maxExpansionTerms: options.maxExpansionTerms,
                minTermWeight: 0.3,
            },
            graphExpansion: {
                enabled: options.enableGraphExpansion,
                maxHops: options.maxHops,
                maxExpandedEntities: 20,
            },
        };

        onSearch(request);
    }, [query, selectedModules, options, onSearch]);

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSearch();
            }
        },
        [handleSearch]
    );

    const toggleModule = useCallback((moduleId: string) => {
        setSelectedModules((prev) =>
            prev.includes(moduleId)
                ? prev.filter((id) => id !== moduleId)
                : [...prev, moduleId]
        );
    }, []);

    const clearModules = useCallback(() => {
        setSelectedModules([]);
    }, []);

    return (
        <div className="kg-search-bar">
            {/* Main search row */}
            <div className="search-row">
                <div className="search-input-container">
                    <Search className="search-icon" size={20} />
                    <input
                        type="text"
                        className="search-input"
                        placeholder="Search the knowledge graph..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isSearching}
                    />
                    {query && (
                        <button
                            className="clear-button"
                            onClick={() => setQuery('')}
                            aria-label="Clear search"
                        >
                            <X size={16} />
                        </button>
                    )}
                </div>

                {/* Module filter dropdown */}
                <div className="module-filter">
                    <button
                        className="module-filter-button"
                        onClick={() => setShowModuleDropdown(!showModuleDropdown)}
                    >
                        <span>
                            {selectedModules.length > 0
                                ? `${selectedModules.length} module${selectedModules.length > 1 ? 's' : ''}`
                                : 'All modules'}
                        </span>
                        {showModuleDropdown ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    {showModuleDropdown && (
                        <div className="module-dropdown">
                            <div className="module-dropdown-header">
                                <span>Filter by module</span>
                                {selectedModules.length > 0 && (
                                    <button onClick={clearModules} className="clear-modules">
                                        Clear all
                                    </button>
                                )}
                            </div>
                            <div className="module-list">
                                {modules.map((module) => (
                                    <label key={module.id} className="module-option">
                                        <input
                                            type="checkbox"
                                            checked={selectedModules.includes(module.id)}
                                            onChange={() => toggleModule(module.id)}
                                        />
                                        <span>{module.name}</span>
                                        {module.documentCount !== undefined && (
                                            <span className="doc-count">
                                                ({module.documentCount})
                                            </span>
                                        )}
                                    </label>
                                ))}
                                {modules.length === 0 && (
                                    <div className="no-modules">No modules available</div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Advanced options toggle */}
                <button
                    className={`advanced-toggle ${showAdvanced ? 'active' : ''}`}
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    aria-label="Advanced options"
                >
                    <Settings size={20} />
                </button>

                {/* Search button */}
                <Button
                    onClick={handleSearch}
                    disabled={isSearching || !query.trim()}
                    className="search-button"
                >
                    {isSearching ? 'Searching...' : 'Search'}
                </Button>
            </div>

            {/* Advanced options panel */}
            {showAdvanced && (
                <div className="advanced-options">
                    <div className="option-group">
                        <label>
                            Results to return
                            <input
                                type="number"
                                min={1}
                                max={50}
                                value={options.topK}
                                onChange={(e) =>
                                    setOptions({
                                        ...options,
                                        topK: parseInt(e.target.value) || 15,
                                    })
                                }
                            />
                        </label>
                    </div>

                    <div className="option-group">
                        <label>
                            Vector weight: {(options.vectorWeight * 100).toFixed(0)}%
                            <input
                                type="range"
                                min={0}
                                max={100}
                                value={options.vectorWeight * 100}
                                onChange={(e) =>
                                    setOptions({
                                        ...options,
                                        vectorWeight: parseInt(e.target.value) / 100,
                                    })
                                }
                            />
                        </label>
                        <span className="weight-labels">
                            <span>Fulltext</span>
                            <span>Semantic</span>
                        </span>
                    </div>

                    <div className="option-group checkboxes">
                        <label>
                            <input
                                type="checkbox"
                                checked={options.enableQueryExpansion}
                                onChange={(e) =>
                                    setOptions({
                                        ...options,
                                        enableQueryExpansion: e.target.checked,
                                    })
                                }
                            />
                            Query expansion
                        </label>

                        <label>
                            <input
                                type="checkbox"
                                checked={options.enableGraphExpansion}
                                onChange={(e) =>
                                    setOptions({
                                        ...options,
                                        enableGraphExpansion: e.target.checked,
                                    })
                                }
                            />
                            Graph expansion
                        </label>
                    </div>

                    {options.enableGraphExpansion && (
                        <div className="option-group">
                            <label>
                                Graph hops: {options.maxHops}
                                <input
                                    type="range"
                                    min={1}
                                    max={3}
                                    value={options.maxHops}
                                    onChange={(e) =>
                                        setOptions({
                                            ...options,
                                            maxHops: parseInt(e.target.value),
                                        })
                                    }
                                />
                            </label>
                        </div>
                    )}

                    <button
                        className="reset-options"
                        onClick={() => setOptions(defaultOptions)}
                    >
                        Reset to defaults
                    </button>
                </div>
            )}

            <style>{`
                .kg-search-bar {
                    background: var(--surface-1);
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                }

                .search-row {
                    display: flex;
                    gap: 12px;
                    align-items: center;
                }

                .search-input-container {
                    flex: 1;
                    position: relative;
                    display: flex;
                    align-items: center;
                }

                .search-icon {
                    position: absolute;
                    left: 12px;
                    color: var(--text-2);
                }

                .search-input {
                    width: 100%;
                    padding: 12px 40px;
                    border: 1px solid var(--border-1);
                    border-radius: 6px;
                    font-size: 16px;
                    background: var(--surface-2);
                    color: var(--text-1);
                }

                .search-input:focus {
                    outline: none;
                    border-color: var(--primary);
                }

                .search-input:disabled {
                    opacity: 0.6;
                }

                .clear-button {
                    position: absolute;
                    right: 12px;
                    background: none;
                    border: none;
                    color: var(--text-2);
                    cursor: pointer;
                    padding: 4px;
                }

                .module-filter {
                    position: relative;
                }

                .module-filter-button {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 16px;
                    border: 1px solid var(--border-1);
                    border-radius: 6px;
                    background: var(--surface-2);
                    color: var(--text-1);
                    cursor: pointer;
                    white-space: nowrap;
                }

                .module-dropdown {
                    position: absolute;
                    top: 100%;
                    right: 0;
                    margin-top: 4px;
                    background: var(--surface-1);
                    border: 1px solid var(--border-1);
                    border-radius: 6px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    min-width: 220px;
                    z-index: 100;
                }

                .module-dropdown-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    border-bottom: 1px solid var(--border-1);
                    font-weight: 500;
                }

                .clear-modules {
                    background: none;
                    border: none;
                    color: var(--primary);
                    cursor: pointer;
                    font-size: 12px;
                }

                .module-list {
                    max-height: 200px;
                    overflow-y: auto;
                    padding: 8px;
                }

                .module-option {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px;
                    cursor: pointer;
                    border-radius: 4px;
                }

                .module-option:hover {
                    background: var(--surface-2);
                }

                .doc-count {
                    color: var(--text-2);
                    font-size: 12px;
                    margin-left: auto;
                }

                .no-modules {
                    padding: 16px;
                    text-align: center;
                    color: var(--text-2);
                }

                .advanced-toggle {
                    padding: 12px;
                    border: 1px solid var(--border-1);
                    border-radius: 6px;
                    background: var(--surface-2);
                    color: var(--text-2);
                    cursor: pointer;
                }

                .advanced-toggle.active {
                    background: var(--primary);
                    color: var(--text-on-primary);
                    border-color: var(--primary);
                }

                .search-button {
                    white-space: nowrap;
                }

                .advanced-options {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 16px;
                    margin-top: 16px;
                    padding-top: 16px;
                    border-top: 1px solid var(--border-1);
                }

                .option-group {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .option-group label {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                    font-size: 14px;
                    color: var(--text-2);
                }

                .option-group.checkboxes {
                    flex-direction: row;
                    gap: 16px;
                }

                .option-group.checkboxes label {
                    flex-direction: row;
                    align-items: center;
                    gap: 8px;
                }

                .option-group input[type="number"] {
                    width: 80px;
                    padding: 8px;
                    border: 1px solid var(--border-1);
                    border-radius: 4px;
                    background: var(--surface-2);
                    color: var(--text-1);
                }

                .option-group input[type="range"] {
                    width: 150px;
                }

                .weight-labels {
                    display: flex;
                    justify-content: space-between;
                    font-size: 12px;
                    color: var(--text-3);
                }

                .reset-options {
                    background: none;
                    border: none;
                    color: var(--primary);
                    cursor: pointer;
                    font-size: 14px;
                    margin-left: auto;
                    align-self: flex-end;
                }
            `}</style>
        </div>
    );
}
