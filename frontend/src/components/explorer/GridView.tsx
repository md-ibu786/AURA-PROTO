/**
 * Grid View Component - Windows Explorer-style icon grid with inline creation
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
    FolderOpen
} from 'lucide-react';

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
        cancelCreating
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

    // Reset create value when starting creation
    React.useEffect(() => {
        if (creatingNodeType) {
            // Use simple names - backend will add prefixes like "Semester X - "
            const defaultNames: Record<string, string> = {
                department: 'New Department',
                semester: 'Fall 2025',  // Just descriptive name, backend adds "Semester X - "
                subject: 'New Subject',
                module: 'Introduction',  // Just descriptive name, backend adds "Module X - "
                note: 'New Note'
            };
            setCreateValue(defaultNames[creatingNodeType] || 'New Item');
        }
    }, [creatingNodeType]);

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
        } catch (error) {
            console.error("Rename failed", error);
            alert("Rename failed");
        } finally {
            setRenamingNodeId(null);
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
        if (!creatingNodeType || !createValue.trim()) {
            cancelCreating();
            return;
        }

        const name = createValue.trim();


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
        } catch (error) {
            console.error("Create failed", error);
            alert(`Failed to create: ${(error as Error).message}`);
        } finally {
            cancelCreating();
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
                window.open(`/pdfs/${item.meta.pdfFilename}`, '_blank');
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
                        onChange={(e) => setCreateValue(e.target.value)}
                        onBlur={handleCreateSubmit}
                        onKeyDown={handleCreateKeyDown}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        onFocus={(e) => e.target.select()}
                    />
                </div>
            )}

            {filteredItems.map((item) => {
                const config = typeConfig[item.type] || typeConfig.note;
                const Icon = config.icon;
                const isSelected = selectedIds.has(item.id);
                const isRenaming = item.id === renamingNodeId;

                return (
                    <div
                        key={item.id}
                        className={`grid-item ${isSelected ? 'selected' : ''}`}
                        onClick={(e) => handleClick(e, item)}
                        onDoubleClick={() => handleDoubleClick(item)}
                        onContextMenu={(e) => handleContextMenu(e, item)}
                    >
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
                        {item.type === 'note' && item.meta?.processing && (
                            <div className="status-badge processing">Processing</div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
