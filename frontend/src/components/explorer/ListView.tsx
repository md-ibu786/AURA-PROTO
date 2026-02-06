/**
 * ============================================================================
 * FILE: ListView.tsx
 * LOCATION: frontend/src/components/explorer/ListView.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Table-style list view for displaying explorer items.
 *
 * ROLE IN PROJECT:
 *    Provides a compact explorer view with selection, rename, and navigation
 *    behavior aligned with the GridView component.
 *
 * KEY COMPONENTS:
 *    - ListView: Renders rows and handles click/double-click actions.
 *    - typeIcons: Maps hierarchy types to row icons.
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, api/explorerApi, api, types
 *
 * USAGE:
 *    <ListView items={currentFolderChildren} allItems={fullTree} />
 * ============================================================================
 */
import { useExplorerStore } from '../../stores';
import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { FileSystemNode } from '../../types';
import {
    Building2,
    Calendar,
    BookOpen,
    Package,
    FileText,
    CheckSquare,
    Square
} from 'lucide-react';

interface ListViewProps {
    items: FileSystemNode[];
    allItems: FileSystemNode[];
}

const typeIcons = {
    department: Building2,
    semester: Calendar,
    subject: BookOpen,
    module: Package,
    note: FileText,
};

export function ListView({ items }: ListViewProps) {
    const {
        selectedIds,
        select,
        toggleSelect,
        rangeSelect,
        navigateTo,
        currentPath,
        openContextMenu,
        searchQuery,
        renamingNodeId,
        setRenamingNodeId,
        openWarningDialog,
        selectionMode,
        deleteMode
    } = useExplorerStore();

    // Renaming state
    const [renameValue, setRenameValue] = React.useState('');
    const renameInputRef = React.useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();

    // Start renaming
    React.useEffect(() => {
        if (renamingNodeId) {
            const node = items.find(i => i.id === renamingNodeId);
            if (node) {
                setRenameValue(node.label);
            }
        }
    }, [renamingNodeId, items]);

    const handleRenameSubmit = async (node: FileSystemNode) => {
        if (!renameValue || renameValue === node.label) {
            setRenamingNodeId(null);
            return;
        }

        try {
            const id = node.id;
            const { renameNode } = await import('../../api/explorerApi');
            await renameNode(node.type, id, renameValue);

            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
            setRenamingNodeId(null);
        } catch (error) {
            const api = await import('../../api');
            if (error instanceof api.DuplicateError) {
                openWarningDialog('duplicate', error.message, renameValue);
            } else {
                console.error("Rename failed", error);
                alert("Rename failed");
                setRenamingNodeId(null);
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent, node: FileSystemNode) => {
        if (e.key === 'Enter') {
            handleRenameSubmit(node);
        } else if (e.key === 'Escape') {
            setRenamingNodeId(null);
        }
        e.stopPropagation();
    };

    // Filter items based on search query
    const filteredItems = searchQuery
        ? items.filter(item =>
            item.label.toLowerCase().includes(searchQuery.toLowerCase())
        )
        : items;

    const handleClick = (e: React.MouseEvent, item: FileSystemNode) => {
        e.stopPropagation();

        const itemIds = filteredItems.map(i => i.id);

        // Check if note is already KG-processed
        const isKGReady = item.type === 'note' && item.meta?.kg_status === 'ready';

        if (selectionMode) {
            if (deleteMode) {
                // In delete mode, only allow selecting KG-ready notes
                if (!isKGReady) {
                    return; // Do nothing - item is disabled in delete mode
                }
            } else {
                // In process mode, prevent selecting already-processed notes
                if (isKGReady) {
                    return; // Do nothing - item is disabled
                }
            }
            toggleSelect(item.id);
            return;
        }

        if (e.shiftKey) {
            rangeSelect(item.id, itemIds);
        } else if (e.ctrlKey || e.metaKey) {
            toggleSelect(item.id);
        } else {
            select(item.id);
        }
    };

    const handleDoubleClick = (item: FileSystemNode) => {
        if (item.type === 'note') {
            if (item.meta?.pdfFilename) {
                // Use authenticated API endpoint for inline viewing
                window.open(`/api/pdfs/${item.meta.pdfFilename}?inline=1`, '_blank');
            }
        } else {
            navigateTo(item, currentPath);
        }
    };

    const handleContextMenu = (e: React.MouseEvent, item: FileSystemNode) => {
        e.preventDefault();
        e.stopPropagation();

        if (!selectedIds.has(item.id)) {
            select(item.id);
        }

        openContextMenu(e.clientX, e.clientY, item.id);
    };

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return '-';
        try {
            return new Date(dateStr).toLocaleDateString();
        } catch {
            return '-';
        }
    };

    return (
        <div className="list-view">
            <div className="list-header">
                <div></div>
                <div>Name</div>
                <div>Type</div>
                <div>Items</div>
                <div>Modified</div>
            </div>

            {filteredItems.map((item) => {
                const Icon = typeIcons[item.type] || FileText;
                const isSelected = selectedIds.has(item.id);
                const isRenaming = item.id === renamingNodeId;
                // Check if note is already KG-processed
                const isKGReady = item.type === 'note' && item.meta?.kg_status === 'ready';
                
                // Determine disabled state based on mode:
                // - Process mode (deleteMode=false): KG-ready notes are disabled (can't reprocess)
                // - Delete mode (deleteMode=true): non-KG-ready notes are disabled (can't delete)
                const isDisabledInSelection = selectionMode && (
                    deleteMode ? !isKGReady : isKGReady
                );
                
                // Tooltip for disabled items
                const disabledTooltip = deleteMode 
                    ? 'Not processed - cannot delete from KG'
                    : 'Already processed - will be skipped';

                return (
                    <div
                        key={item.id}
                        data-id={item.id}
                        className={`list-row selectable-item ${isSelected ? 'selected' : ''} ${isDisabledInSelection ? 'kg-disabled' : ''}`}
                        onClick={(e) => handleClick(e, item)}
                        onDoubleClick={() => handleDoubleClick(item)}
                        onContextMenu={(e) => handleContextMenu(e, item)}
                        title={isDisabledInSelection ? disabledTooltip : undefined}
                    >
                        <div className={`list-row-icon grid-item-icon ${item.type}`}>
                            {/* Selection Checkbox - overlays icon in selection mode */}
                            {selectionMode ? (
                                isDisabledInSelection ? (
                                    <div 
                                        className="kg-ready-led-inline" 
                                        title={disabledTooltip}
                                    />
                                ) : isSelected ? (
                                    <CheckSquare className="h-5 w-5 text-primary fill-background" />
                                ) : (
                                    <Square className="h-5 w-5 text-zinc-300 dark:text-zinc-600" />
                                )
                            ) : (
                                <Icon size={18} />
                            )}
                        </div>

                        <div className="list-row-name">
                            {isRenaming ? (
                                <input
                                    ref={renameInputRef}
                                    type="text"
                                    className="rename-input"
                                    value={renameValue}
                                    onChange={(e) => setRenameValue(e.target.value)}
                                    onBlur={() => handleRenameSubmit(item)}
                                    onKeyDown={(e) => handleKeyDown(e, item)}
                                    onClick={(e) => e.stopPropagation()}
                                    autoFocus
                                    onFocus={(e) => e.target.select()}
                                />
                            ) : (
                                item.label
                            )}
                        </div>

                        <div className="list-row-type">{item.type}</div>
                        <div className="list-row-count">
                            {item.meta?.noteCount !== undefined ? item.meta.noteCount : '-'}
                        </div>
                        <div className="list-row-date">
                            {formatDate(item.meta?.createdAt)}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
