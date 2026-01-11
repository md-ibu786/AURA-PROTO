/**
 * ============================================================================
 * FILE: ContextMenu.tsx
 * LOCATION: frontend/src/components/explorer/ContextMenu.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Right-click context menu for file explorer items. Provides quick
 *    actions like Open, Rename, Delete, and Create Child based on the
 *    selected node type.
 *
 * ROLE IN PROJECT:
 *    Primary action menu for interacting with hierarchy nodes. Appears
 *    on right-click in both SidebarTree and GridView/ListView.
 *
 * MENU ACTIONS:
 *    - Open: Navigate into folder or open PDF for notes
 *    - Download PDF: (notes only) Download the PDF file
 *    - New [Child Type]: Create child entity (e.g., New Semester inside Department)
 *    - Rename: Trigger inline rename mode
 *    - Delete: Open confirm delete dialog
 *
 * CHILD TYPE MAPPING:
 *    - department → New Semester
 *    - semester → New Subject
 *    - subject → New Module
 *    - module → New Note (redirects to upload dialog)
 *    - note → null (no children)
 *
 * DEPENDENCIES:
 *    - External: lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, types
 *
 * USAGE:
 *    {contextMenuPosition && <ContextMenu />}
 *    Renders as a positioned overlay based on click coordinates.
 * ============================================================================
 */
import { useExplorerStore } from '../../stores';
import { useQueryClient } from '@tanstack/react-query';
import {
    FolderOpen,
    Edit,
    Trash2,
    Plus,
    Download,
    ExternalLink
} from 'lucide-react';
import type { FileSystemNode, HierarchyType } from '../../types';

// Define what can be created under each type
const childTypes: Record<HierarchyType, { label: string; type: HierarchyType } | null> = {
    department: { label: 'New Semester', type: 'semester' },
    semester: { label: 'New Subject', type: 'subject' },
    subject: { label: 'New Module', type: 'module' },
    module: { label: 'New Note', type: 'note' },
    note: null, // Notes don't have children
};

export function ContextMenu() {
    const {
        contextMenuPosition,
        contextMenuNodeId,
        closeContextMenu,
        currentPath,
        navigateTo,
        setRenamingNodeId,
        startCreating,
        openDeleteDialog
    } = useExplorerStore();

    const queryClient = useQueryClient();

    if (!contextMenuPosition || !contextMenuNodeId) return null;

    // Find the node in the tree
    const findNodeInTree = (nodes: FileSystemNode[], id: string): FileSystemNode | null => {
        for (const node of nodes) {
            if (node.id === id) return node;
            if (node.children) {
                const found = findNodeInTree(node.children, id);
                if (found) return found;
            }
        }
        return null;
    };

    const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
    const node = findNodeInTree(tree, contextMenuNodeId);

    if (!node) return null;

    const childType = childTypes[node.type];
    const isNote = node.type === 'note';

    const handleOpen = () => {
        if (isNote && node.meta?.pdfFilename) {
            window.open(`/pdfs/${node.meta.pdfFilename}`, '_blank');
        } else {
            navigateTo(node, currentPath);
        }
        closeContextMenu();
    };

    const handleRename = () => {
        setRenamingNodeId(contextMenuNodeId);
        closeContextMenu();
    };

    const handleDeleteClick = () => {
        // Use global dialog via store action
        openDeleteDialog({
            id: node.id,
            type: node.type,
            label: node.label
        });
    };

    const handleCreate = () => {
        if (!childType) return;

        // Get parent ID for the new item
        const parentId = node.id;

        // For notes, show a message to use upload feature
        if (childType.type === 'note') {
            alert('Use the Audio Upload feature to create notes with transcription and summarization.');
            closeContextMenu();
            return;
        }

        // Start inline creation - parent ID is stored so we don't need to navigate
        startCreating(childType.type, parentId);
        closeContextMenu();
    };

    const handleDownload = () => {
        if (node.meta?.pdfFilename) {
            const link = document.createElement('a');
            link.href = `/pdfs/${node.meta.pdfFilename}`;
            link.download = node.meta.pdfFilename;
            link.click();
        }
        closeContextMenu();
    };

    return (
        <div
            className="context-menu"
            style={{
                left: contextMenuPosition.x,
                top: contextMenuPosition.y
            }}
            onClick={(e) => e.stopPropagation()}
        >
            <button className="context-menu-item" onClick={handleOpen}>
                {isNote ? <ExternalLink size={16} /> : <FolderOpen size={16} />}
                <span>{isNote ? 'Open PDF' : 'Open'}</span>
            </button>

            {isNote && node.meta?.pdfFilename && (
                <button className="context-menu-item" onClick={handleDownload}>
                    <Download size={16} />
                    <span>Download PDF</span>
                </button>
            )}

            <div className="context-menu-separator" />

            {childType && (
                <button className="context-menu-item" onClick={handleCreate}>
                    <Plus size={16} />
                    <span>{childType.label}</span>
                </button>
            )}

            <button className="context-menu-item" onClick={handleRename}>
                <Edit size={16} />
                <span>Rename</span>
            </button>

            <div className="context-menu-separator" />

            <button className="context-menu-item danger" onClick={handleDeleteClick}>
                <Trash2 size={16} />
                <span>Delete</span>
            </button>
        </div>
    );
}
