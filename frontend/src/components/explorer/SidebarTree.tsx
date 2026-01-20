/**
 * ============================================================================
 * FILE: SidebarTree.tsx
 * LOCATION: frontend/src/components/explorer/SidebarTree.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Recursive tree navigation component for the sidebar. Renders the
 *    hierarchy as an expandable/collapsible tree with icons, inline
 *    renaming, and inline creation of new nodes.
 *
 * ROLE IN PROJECT:
 *    Provides the left-panel tree navigation similar to Windows Explorer.
 *    Allows users to quickly navigate the hierarchy without drilling
 *    down one level at a time through the main content area.
 *
 * KEY COMPONENTS:
 *    - SidebarTree: Main recursive component that renders tree nodes
 *    - TreeItem: Individual tree node with expand/collapse, icon, label
 *    - CreationItem: Inline input for creating new nodes
 *
 * FEATURES:
 *    - Expandable/collapsible nodes with chevron icons
 *    - Type-specific icons (Building2, Calendar, BookOpen, etc.)
 *    - Inline renaming (F2 or context menu)
 *    - Inline creation (right-click → New Folder)
 *    - Active/selected state highlighting
 *    - Right-click context menu support
 *
 * ICON MAPPING:
 *    - department: Building2
 *    - semester: Calendar
 *    - subject: BookOpen
 *    - module: Package
 *    - note: FileText
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons), @tanstack/react-query
 *    - Internal: stores/useExplorerStore, api, types
 *
 * USAGE:
 *    <SidebarTree nodes={tree} level={0} ancestors={[]} />
 * ============================================================================
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useExplorerStore } from '../../stores';
import * as api from '../../api';
import type { FileSystemNode } from '../../types';
import {
    ChevronRight,
    ChevronDown,
    Building2,
    Calendar,
    BookOpen,
    Package,
    FileText
} from 'lucide-react';

interface SidebarTreeProps {
    nodes: FileSystemNode[];
    level: number;
    ancestors: FileSystemNode[];
}

// Icon mapping for each type
const typeIcons = {
    department: Building2,
    semester: Calendar,
    subject: BookOpen,
    module: Package,
    note: FileText,
};

function CreationItem({ parentId, type }: { parentId: string | null; type: import('../../types').HierarchyType }) {
    const { cancelCreating, openWarningDialog } = useExplorerStore();
    const queryClient = useQueryClient();
    const [name, setName] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const Icon = typeIcons[type] || FileText;

    useEffect(() => {
        if (inputRef.current) {
            inputRef.current.focus();
        }
    }, []);

    const handleSubmit = async () => {
        if (isSubmitting) return;
        if (!name.trim()) {
            cancelCreating();
            return;
        }

        setIsSubmitting(true);
        try {
            switch (type) {
                case 'department': {
                    const code = name.substring(0, 4).toUpperCase().replace(/\s/g, '');
                    await api.createDepartment(name, code);
                    break;
                }
                case 'semester':
                    await api.createSemester(parentId!, 1, name);
                    break;
                case 'subject': {
                    const subjCode = name.substring(0, 6).toUpperCase().replace(/\s/g, '');
                    await api.createSubject(parentId!, name, subjCode);
                    break;
                }
                case 'module':
                    await api.createModule(parentId!, 1, name);
                    break;
            }
            await queryClient.invalidateQueries({ queryKey: ['explorer', 'tree'] });
            cancelCreating();
        } catch (error) {
            if (error instanceof api.DuplicateError) {
                openWarningDialog('duplicate', error.message, name);
            } else {
                console.error(error);
                alert(`Failed to create: ${(error as Error).message}`);
                cancelCreating();
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSubmit();
        } else if (e.key === 'Escape') {
            cancelCreating();
        }
    };

    return (
        <div className="tree-item">
            <div style={{ width: 20 }} />
            <div className={`tree-item-icon ${type === 'note' ? 'note' : 'folder'}`}>
                <Icon size={16} />
            </div>
            <input
                ref={inputRef}
                type="text"
                className="tree-item-input"
                value={name}
                placeholder={`New ${type}`}
                onChange={(e) => setName(e.target.value)}
                onBlur={handleSubmit}
                onKeyDown={handleKeyDown}
                onClick={(e) => e.stopPropagation()}
                disabled={isSubmitting}
            />
        </div>
    );
}

function TreeItem({
    node,
    level,
    ancestors
}: {
    node: FileSystemNode;
    level: number;
    ancestors: FileSystemNode[]
}) {
    const {
        activeNodeId,
        expandedIds,
        toggleExpand,
        navigateTo,
        selectedIds,
        renamingNodeId,
        setRenamingNodeId,
        openContextMenu,
        creatingParentId,
        creatingNodeType
    } = useExplorerStore();

    const queryClient = useQueryClient();
    const [renameValue, setRenameValue] = useState(node.label);
    const inputRef = useRef<HTMLInputElement>(null);

    const Icon = typeIcons[node.type] || FileText;
    const isExpanded = expandedIds.has(node.id);
    const isActive = activeNodeId === node.id;
    const isSelected = selectedIds.has(node.id);
    const isRenaming = renamingNodeId === node.id;
    const hasChildren = node.meta?.hasChildren || (node.children && node.children.length > 0);

    // Focus input when renaming starts
    useEffect(() => {
        if (isRenaming && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
            setRenameValue(node.label);
        }
    }, [isRenaming, node.label]);

    const handleRenameSubmit = async () => {
        if (!renameValue.trim() || renameValue === node.label) {
            setRenamingNodeId(null);
            return;
        }

        try {
            await api.renameNode(node.type, node.id, renameValue);
            await queryClient.invalidateQueries({ queryKey: ['explorer', 'tree'] });
            setRenamingNodeId(null);
        } catch (error) {
            if (error instanceof api.DuplicateError) {
                useExplorerStore.getState().openWarningDialog('duplicate', error.message, renameValue);
            } else {
                console.error('Failed to rename:', error);
                alert('Failed to rename item');
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleRenameSubmit();
        } else if (e.key === 'Escape') {
            setRenamingNodeId(null);
            setRenameValue(node.label);
        }
    };

    return (
        <div>
            <div
                className={`tree-item ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''}`}
                onClick={() => !isRenaming && navigateTo(node, ancestors)}
                onDoubleClick={() => {
                    if (!isRenaming && hasChildren) {
                        toggleExpand(node.id);
                    }
                }}
                onContextMenu={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openContextMenu(e.clientX, e.clientY, node.id);
                }}
            >
                {/* Expand/collapse button */}
                {hasChildren ? (
                    <button
                        className="tree-expand-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleExpand(node.id);
                        }}
                    >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                ) : (
                    <div style={{ width: 20 }} />
                )}

                {/* Icon */}
                <div className={`tree-item-icon ${node.type === 'note' ? 'note' : 'folder'}`}>
                    <Icon size={16} />
                </div>

                {/* Label or Rename Input */}
                {isRenaming ? (
                    <input
                        ref={inputRef}
                        type="text"
                        className="tree-item-input"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={handleRenameSubmit}
                        onKeyDown={handleKeyDown}
                        onClick={(e) => e.stopPropagation()}
                    />
                ) : (
                    <span className="tree-item-label">{node.label}</span>
                )}
            </div>

            {/* Children */}
            {isExpanded && (
                <>
                    {node.children && node.children.length > 0 && (
                        <SidebarTree
                            nodes={node.children}
                            level={level + 1}
                            ancestors={[...ancestors, node]}
                        />
                    )}
                    {creatingParentId === node.id && creatingNodeType && (
                        <div className="tree-children" style={{ marginLeft: undefined }}>
                            <CreationItem type={creatingNodeType} parentId={node.id} />
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export function SidebarTree({ nodes, level, ancestors }: SidebarTreeProps) {
    const { creatingParentId, creatingNodeType } = useExplorerStore();

    return (
        <div className="tree-children" style={{ marginLeft: level === 0 ? 0 : undefined }}>
            {nodes.map((node) => (
                <TreeItem
                    key={node.id}
                    node={node}
                    level={level}
                    ancestors={ancestors}
                />
            ))}

            {/* Root Level Creation */}
            {level === 0 && creatingParentId === null && creatingNodeType === 'department' && (
                <CreationItem type='department' parentId={null} />
            )}
        </div>
    );
}
