/**
 * Sidebar Tree Component - Recursive tree navigation
 */
import { useExplorerStore } from '../../stores';
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

export function SidebarTree({ nodes, level, ancestors }: SidebarTreeProps) {
    const {
        activeNodeId,
        expandedIds,
        toggleExpand,
        navigateTo,
        selectedIds
    } = useExplorerStore();

    return (
        <div className="tree-children" style={{ marginLeft: level === 0 ? 0 : undefined }}>
            {nodes.map((node) => {
                const Icon = typeIcons[node.type] || FileText;
                const isExpanded = expandedIds.has(node.id);
                const isActive = activeNodeId === node.id;
                const isSelected = selectedIds.has(node.id);
                const hasChildren = node.meta?.hasChildren || (node.children && node.children.length > 0);

                return (
                    <div key={node.id}>
                        <div
                            className={`tree-item ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''}`}
                            onClick={() => navigateTo(node, ancestors)}
                            onDoubleClick={() => {
                                if (hasChildren) {
                                    toggleExpand(node.id);
                                }
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

                            {/* Label */}
                            <span className="tree-item-label">{node.label}</span>
                        </div>

                        {/* Children */}
                        {isExpanded && node.children && node.children.length > 0 && (
                            <SidebarTree
                                nodes={node.children}
                                level={level + 1}
                                ancestors={[...ancestors, node]}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
