/**
 * ============================================================================
 * FILE: GraphFilterPanel.tsx
 * LOCATION: frontend/src/features/kg-query/components/GraphFilterPanel.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Filter panel for UnifiedGraphView that allows users to filter nodes by
 *    entity type and relationship type. Provides visual indicators with
 *    consistent ENTITY_COLORS styling.
 *
 * FEATURES:
 *    - Entity type checkboxes with color indicators
 *    - Relationship type filters
 *    - Select all / deselect all functionality
 *    - Apply and reset buttons
 *    - Collapsible sections
 *
 * @see: components/UnifiedGraphView.tsx - Parent graph component
 * @see: types/kg-query.types.ts - GraphOptions type
 * @note: Filter state managed by parent component
 */

import React, { useState, useMemo, useCallback } from 'react';
import { ChevronDown, ChevronRight, RotateCcw } from 'lucide-react';
import { ENTITY_COLORS } from './UnifiedGraphView';

// ============================================================================
// INTERFACES
// ============================================================================

export interface FilterState {
    enabledEntityTypes: Set<string>;
    enabledRelationshipTypes: Set<string>;
}

export interface GraphFilterPanelProps {
    /** Available entity types from the graph */
    entityTypes: string[];
    /** Available relationship types from the graph */
    relationshipTypes: string[];
    /** Current filter state */
    filterState: FilterState;
    /** Called when filters change */
    onFilterChange: (newState: FilterState) => void;
    /** Called when Apply is clicked */
    onApply?: () => void;
    /** Whether to show as a floating panel or inline */
    variant?: 'floating' | 'inline';
    /** Custom class name */
    className?: string;
}

// ============================================================================
// COLLAPSIBLE SECTION
// ============================================================================

interface CollapsibleSectionProps {
    title: string;
    children: React.ReactNode;
    defaultExpanded?: boolean;
}

function CollapsibleSection({
    title,
    children,
    defaultExpanded = true,
}: CollapsibleSectionProps) {
    const [expanded, setExpanded] = useState(defaultExpanded);

    return (
        <div className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
            <button
                onClick={() => setExpanded((e) => !e)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {title}
                </span>
                {expanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
            </button>
            {expanded && <div className="px-3 pb-3">{children}</div>}
        </div>
    );
}

// ============================================================================
// CHECKBOX ITEM
// ============================================================================

interface CheckboxItemProps {
    id: string;
    label: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    color?: string;
}

function CheckboxItem({
    id,
    label,
    checked,
    onChange,
    color,
}: CheckboxItemProps) {
    return (
        <label
            htmlFor={id}
            className="flex items-center gap-2 py-1 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 px-2 rounded"
        >
            <input
                type="checkbox"
                id={id}
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            {color && (
                <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                />
            )}
            <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                {label}
            </span>
        </label>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function GraphFilterPanel({
    entityTypes,
    relationshipTypes,
    filterState,
    onFilterChange,
    onApply,
    variant = 'floating',
    className = '',
}: GraphFilterPanelProps) {
    // Check if all entity types are selected
    const allEntitiesSelected = useMemo(
        () => entityTypes.every((t) => filterState.enabledEntityTypes.has(t)),
        [entityTypes, filterState.enabledEntityTypes]
    );

    // Check if all relationship types are selected
    const allRelationshipsSelected = useMemo(
        () =>
            relationshipTypes.every((t) =>
                filterState.enabledRelationshipTypes.has(t)
            ),
        [relationshipTypes, filterState.enabledRelationshipTypes]
    );

    // Toggle entity type
    const toggleEntityType = useCallback(
        (type: string, enabled: boolean) => {
            const newTypes = new Set(filterState.enabledEntityTypes);
            if (enabled) {
                newTypes.add(type);
            } else {
                newTypes.delete(type);
            }
            onFilterChange({
                ...filterState,
                enabledEntityTypes: newTypes,
            });
        },
        [filterState, onFilterChange]
    );

    // Toggle relationship type
    const toggleRelationshipType = useCallback(
        (type: string, enabled: boolean) => {
            const newTypes = new Set(filterState.enabledRelationshipTypes);
            if (enabled) {
                newTypes.add(type);
            } else {
                newTypes.delete(type);
            }
            onFilterChange({
                ...filterState,
                enabledRelationshipTypes: newTypes,
            });
        },
        [filterState, onFilterChange]
    );

    // Select all entity types
    const selectAllEntities = useCallback(() => {
        onFilterChange({
            ...filterState,
            enabledEntityTypes: new Set(entityTypes),
        });
    }, [entityTypes, filterState, onFilterChange]);

    // Deselect all entity types
    const deselectAllEntities = useCallback(() => {
        onFilterChange({
            ...filterState,
            enabledEntityTypes: new Set(),
        });
    }, [filterState, onFilterChange]);

    // Select all relationship types
    const selectAllRelationships = useCallback(() => {
        onFilterChange({
            ...filterState,
            enabledRelationshipTypes: new Set(relationshipTypes),
        });
    }, [relationshipTypes, filterState, onFilterChange]);

    // Deselect all relationship types
    const deselectAllRelationships = useCallback(() => {
        onFilterChange({
            ...filterState,
            enabledRelationshipTypes: new Set(),
        });
    }, [filterState, onFilterChange]);

    // Reset all filters
    const resetAll = useCallback(() => {
        onFilterChange({
            enabledEntityTypes: new Set(entityTypes),
            enabledRelationshipTypes: new Set(relationshipTypes),
        });
    }, [entityTypes, relationshipTypes, onFilterChange]);

    // Base styles based on variant
    const baseStyles =
        variant === 'floating'
            ? 'absolute top-14 left-4 z-20 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700'
            : 'w-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700';

    return (
        <div className={`${baseStyles} ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                    Filters
                </span>
                <button
                    onClick={resetAll}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    title="Reset all filters"
                >
                    <RotateCcw className="w-3 h-3" />
                    Reset
                </button>
            </div>

            {/* Entity Types Section */}
            {entityTypes.length > 0 && (
                <CollapsibleSection title="Entity Types">
                    <div className="flex gap-2 mb-2">
                        <button
                            onClick={selectAllEntities}
                            disabled={allEntitiesSelected}
                            className="text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                            Select All
                        </button>
                        <span className="text-gray-300">|</span>
                        <button
                            onClick={deselectAllEntities}
                            disabled={filterState.enabledEntityTypes.size === 0}
                            className="text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                            Deselect All
                        </button>
                    </div>
                    <div className="space-y-0.5 max-h-48 overflow-y-auto">
                        {entityTypes.map((type) => (
                            <CheckboxItem
                                key={type}
                                id={`entity-${type}`}
                                label={type}
                                checked={filterState.enabledEntityTypes.has(type)}
                                onChange={(checked) =>
                                    toggleEntityType(type, checked)
                                }
                                color={
                                    ENTITY_COLORS[type] || ENTITY_COLORS.default
                                }
                            />
                        ))}
                    </div>
                </CollapsibleSection>
            )}

            {/* Relationship Types Section */}
            {relationshipTypes.length > 0 && (
                <CollapsibleSection title="Relationship Types">
                    <div className="flex gap-2 mb-2">
                        <button
                            onClick={selectAllRelationships}
                            disabled={allRelationshipsSelected}
                            className="text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                            Select All
                        </button>
                        <span className="text-gray-300">|</span>
                        <button
                            onClick={deselectAllRelationships}
                            disabled={
                                filterState.enabledRelationshipTypes.size === 0
                            }
                            className="text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                            Deselect All
                        </button>
                    </div>
                    <div className="space-y-0.5 max-h-48 overflow-y-auto">
                        {relationshipTypes.map((type) => (
                            <CheckboxItem
                                key={type}
                                id={`rel-${type}`}
                                label={type.replace(/_/g, ' ')}
                                checked={filterState.enabledRelationshipTypes.has(
                                    type
                                )}
                                onChange={(checked) =>
                                    toggleRelationshipType(type, checked)
                                }
                            />
                        ))}
                    </div>
                </CollapsibleSection>
            )}

            {/* Apply Button */}
            {onApply && (
                <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
                    <button
                        onClick={onApply}
                        className="w-full py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
                    >
                        Apply Filters
                    </button>
                </div>
            )}
        </div>
    );
}

export default GraphFilterPanel;
