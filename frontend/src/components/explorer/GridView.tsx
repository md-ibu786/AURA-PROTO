/**
 * ============================================================================
 * FILE: GridView.tsx
 * LOCATION: frontend/src/components/explorer/GridView.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Icon grid view for displaying explorer items.
 *
 * ROLE IN PROJECT:
 *    Default explorer view with selection, inline editing, and navigation for
 *    folders and notes.
 *
 * KEY COMPONENTS:
 *    - GridView: Renders grid items and handles selection/rename/create.
 *    - typeConfig: Maps hierarchy types to icon and color classes.
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, api, features/kg, types
 *
 * USAGE:
 *    <GridView items={currentFolderChildren} allItems={fullTree} />
 * ============================================================================
 */
import { useExplorerStore } from '../../stores';
import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { FileSystemNode, HierarchyType } from '../../types';
import * as api from '../../api';
import {
    Building2,
    Calendar,
    BookOpen,
    FileText,
    FolderOpen,
    CheckSquare,
    Square
} from 'lucide-react';
import { KGStatusBadge } from '../../features/kg/components/KGStatusBadge';

interface GridViewProps {
    items: FileSystemNode[];
    allItems: FileSystemNode[];
}

// Icon mapping with colors
const typeConfig: Record<HierarchyType, { icon: typeof Building2; colorClass: string }> = {
    department: { icon: Building2, colorClass: 'department' },
    semester: { icon: Calendar, colorClass: 'semester' },
    subject: { icon: BookOpen, colorClass: 'subject' },
    module: { icon: FolderOpen, colorClass: 'module' },
    note: { icon: FileText, colorClass: 'note' },
};

export function GridView({ items }: GridViewProps) {
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
        creatingNodeType,
        creatingParentId,
        cancelCreating,
        openWarningDialog,
        selectionMode,
        deleteMode
    } = useExplorerStore();

    // Renaming state
    const [renameValue, setRenameValue] = React.useState('');
    const [createValue, setCreateValue] = React.useState('');
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

    // Reset create value when starting creation - start with empty string
    React.useEffect(() => {
        if (creatingNodeType) {
            setCreateValue('');  // Start empty to show placeholder
        }
    }, [creatingNodeType]);

    // Get default names for when user submits empty input
    const getDefaultName = (type: HierarchyType): string => {
        const defaultNames: Record<string, string> = {
            department: 'New Department',
            semester: 'New Semester',
            subject: 'New Subject',
            module: 'New Module',
            note: 'New Note'
        };
        return defaultNames[type] || 'New Item';
    };

    // Get placeholder text for each type
    const getPlaceholder = (type: HierarchyType): string => {
        const placeholders: Record<string, string> = {
            department: 'New Department',
            semester: 'New Semester',
            subject: 'New Subject',
            module: 'New Module',
            note: 'Note title'
        };
        return placeholders[type] || 'Enter name';
    };

    const handleRenameSubmit = async (node: FileSystemNode) => {
        if (!renameValue || renameValue === node.label) {
            setRenamingNodeId(null);
            return;
        }

        try {
            const id = node.id;
            await api.renameNode(node.type, id, renameValue);
            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
            setRenamingNodeId(null);
        } catch (error) {
            if (error instanceof api.DuplicateError) {
                openWarningDialog('duplicate', error.message, renameValue);
            } else {
                console.error("Rename failed", error);
                alert("Rename failed");
                setRenamingNodeId(null);
            }
        }
    };

    const handleRenameKeyDown = (e: React.KeyboardEvent, node: FileSystemNode) => {
        if (e.key === 'Enter') {
            handleRenameSubmit(node);
        } else if (e.key === 'Escape') {
            setRenamingNodeId(null);
        }
        e.stopPropagation();
    };

    // Handle inline creation submit
    const handleCreateSubmit = async () => {
        if (!creatingNodeType) {
            cancelCreating();
            return;
        }

        // Use default name if input is empty
        const name = createValue.trim() || getDefaultName(creatingNodeType);


        try {
            switch (creatingNodeType) {
                case 'department': {
                    const code = name.substring(0, 4).toUpperCase().replace(/\s/g, '');
                    await api.createDepartment(name, code);
                    break;
                }
                case 'semester': {
                    // Calculate next semester number from existing items
                    const existingSemesters = items.filter(i => i.type === 'semester');
                    // Find max semester number and add 1
                    let semNum = 1;
                    if (existingSemesters.length > 0) {
                        // Try to find semester numbers from names (e.g., "Semester 3")
                        const numbers = existingSemesters.map(s => {
                            const match = s.label.match(/\d+/);
                            return match ? parseInt(match[0]) : 0;
                        });
                        semNum = Math.max(...numbers, existingSemesters.length) + 1;
                    }
                    await api.createSemester(creatingParentId!, semNum, name);
                    break;
                }
                case 'subject': {
                    const code = name.substring(0, 6).toUpperCase().replace(/\s/g, '');
                    await api.createSubject(creatingParentId!, name, code);
                    break;
                }
                case 'module': {
                    const modNum = items.filter(i => i.type === 'module').length + 1;
                    await api.createModule(creatingParentId!, modNum, name);
                    break;
                }
            }
            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
            cancelCreating();
        } catch (error) {
            if (error instanceof api.DuplicateError) {
                openWarningDialog('duplicate', error.message, name);
                // Keep input open
            } else {
                console.error("Create failed", error);
                alert(`Failed to create: ${(error as Error).message}`);
                cancelCreating();
            }
        }
    };

    const handleCreateKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleCreateSubmit();
        } else if (e.key === 'Escape') {
            cancelCreating();
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

    return (
        <div className="grid-view">
            {/* Inline creation placeholder */}
            {creatingNodeType && (
                <div className="grid-item selected">
                    <div className={`grid-item-icon ${typeConfig[creatingNodeType].colorClass}`}>
                        {React.createElement(typeConfig[creatingNodeType].icon)}
                    </div>
                    <input
                        type="text"
                        className="rename-input"
                        value={createValue}
                        placeholder={getPlaceholder(creatingNodeType)}
                        onChange={(e) => setCreateValue(e.target.value)}
                        onBlur={handleCreateSubmit}
                        onKeyDown={handleCreateKeyDown}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        onFocus={(e) => {
                            // Only select if there's actual content
                            if (e.target.value) {
                                e.target.select();
                            }
                        }}
                    />
                </div>
            )}

            {filteredItems.map((item) => {
                const config = typeConfig[item.type] || typeConfig.note;
                const Icon = config.icon;
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
                        className={`grid-item selectable-item ${isSelected ? 'selected' : ''} ${isDisabledInSelection ? 'kg-disabled' : ''}`}
                        onClick={(e) => handleClick(e, item)}
                        onDoubleClick={() => handleDoubleClick(item)}
                        onContextMenu={(e) => handleContextMenu(e, item)}
                        title={isDisabledInSelection ? disabledTooltip : undefined}
                    >
                        {/* Green LED indicator for KG-ready notes */}
                        {isKGReady && !selectionMode && (
                            <div 
                                className="kg-ready-led" 
                                title="Already processed"
                            />
                        )}
                        
                        {/* Selection Checkbox */}
                        {selectionMode && (
                            <div className="absolute top-2 right-2 text-primary z-10">
                                {isDisabledInSelection ? (
                                    // Show indicator for disabled items in selection mode
                                    <div 
                                        className="kg-ready-led-inline" 
                                        title={disabledTooltip}
                                    />
                                ) : isSelected ? (
                                    <CheckSquare className="h-5 w-5 fill-background" />
                                ) : (
                                    <Square className="h-5 w-5 text-zinc-300 dark:text-zinc-600" />
                                )}
                            </div>
                        )}

                        <div className={`grid-item-icon ${config.colorClass}`}>
                            <Icon />
                        </div>

                        {isRenaming ? (
                            <input
                                type="text"
                                className="rename-input"
                                value={renameValue}
                                onChange={(e) => setRenameValue(e.target.value)}
                                onBlur={() => handleRenameSubmit(item)}
                                onKeyDown={(e) => handleRenameKeyDown(e, item)}
                                onClick={(e) => e.stopPropagation()}
                                autoFocus
                                onFocus={(e) => e.target.select()}
                            />
                        ) : (
                            <div className="grid-item-label">{item.label}</div>
                        )}

                        {item.meta?.noteCount !== undefined && item.meta.noteCount > 0 && (
                            <div className="grid-item-meta">
                                {item.meta.noteCount} note{item.meta.noteCount !== 1 ? 's' : ''}
                            </div>
                        )}
                        {item.type === 'note' && (
                            <div className="mt-1">
                                {item.meta?.kg_status ? (
                                    <KGStatusBadge status={item.meta.kg_status} size="sm" />
                                ) : item.meta?.processing ? (
                                    <div className="status-badge processing">Processing</div>
                                ) : null}
                            </div>
                        )}
                        {/* Legacy processing badge fallback handled above */}
                    </div>
                );
            })}
        </div>
    );
}
