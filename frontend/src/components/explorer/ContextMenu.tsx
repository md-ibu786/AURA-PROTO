/**
 * ============================================================================
 * FILE: ContextMenu.tsx
 * LOCATION: frontend/src/components/explorer/ContextMenu.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Right-click context menu for explorer items with quick actions.
 *
 * ROLE IN PROJECT:
 *    Provides node-level actions (open, rename, create, delete) and enforces
 *    role-based permissions outside of module notes view.
 *
 * KEY COMPONENTS:
 *    - ContextMenu: Renders the action list for the active node.
 *    - childTypes: Maps hierarchy node types to allowed child types.
 *
 * DEPENDENCIES:
 *    - External: lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, stores/useAuthStore, types
 *
 * USAGE:
 *    {contextMenuPosition && <ContextMenu />}
 * ============================================================================
 */
import { useExplorerStore } from '../../stores';
import { useAuthStore } from '../../stores/useAuthStore';
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

    const { user } = useAuthStore();
    const isAdmin = user?.role === 'admin';
    const isStaff = user?.role === 'staff';

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

    // Check if we're inside a module (viewing notes)
    // When inside a module, the bottom action bar handles all actions
    const isInsideModule = currentPath.length > 0 &&
        currentPath[currentPath.length - 1].type === 'module';

    // Don't show context menu at all when inside a module (notes directory)
    // All actions are handled by the bottom SelectionActionBar
    if (isInsideModule) {
        closeContextMenu();
        return null;
    }

    const childType = childTypes[node.type];
    const isNote = node.type === 'note';

    // Permission checks based on RBAC:
    // - Admin: Can create/edit/delete departments, semesters, subjects
    // - Staff: Can create/edit/delete modules and notes (in their subjects)
    // - Student: Read-only for all
    const canCreateChild = () => {
        if (!childType) return false;
        // Admin can create depts, semesters, subjects
        if (isAdmin && ['department', 'semester', 'subject'].includes(node.type)) {
            return true;
        }
        // Staff can create modules
        if (isStaff && node.type === 'subject') {
            return true;
        }
        return false;
    };

    const canRename = () => {
        // Admin can rename depts, semesters, subjects
        if (isAdmin && ['department', 'semester', 'subject'].includes(node.type)) {
            return true;
        }
        // Staff can rename modules and notes
        if (isStaff && ['module', 'note'].includes(node.type)) {
            return true;
        }
        return false;
    };

    const canDelete = () => {
        // Admin can delete depts, semesters, subjects
        if (isAdmin && ['department', 'semester', 'subject'].includes(node.type)) {
            return true;
        }
        // Staff can delete modules and notes
        if (isStaff && ['module', 'note'].includes(node.type)) {
            return true;
        }
        return false;
    };

    const handleOpen = () => {
        if (isNote && node.meta?.pdfFilename) {
            // Use authenticated API endpoint for inline viewing
            window.open(`/api/pdfs/${node.meta.pdfFilename}?inline=1`, '_blank');
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
            // Use authenticated API endpoint for downloads
            link.href = `/api/pdfs/${node.meta.pdfFilename}`;
            link.download = node.meta.pdfFilename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
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

            {(canCreateChild() || canRename() || canDelete()) && (
                <div className="context-menu-separator" />
            )}

            {canCreateChild() && childType && (
                <button className="context-menu-item" onClick={handleCreate}>
                    <Plus size={16} />
                    <span>{childType.label}</span>
                </button>
            )}

            {canRename() && (
                <button className="context-menu-item" onClick={handleRename}>
                    <Edit size={16} />
                    <span>Rename</span>
                </button>
            )}

            {canDelete() && (
                <>
                    <div className="context-menu-separator" />
                    <button className="context-menu-item danger" onClick={handleDeleteClick}>
                        <Trash2 size={16} />
                        <span>Delete</span>
                    </button>
                </>
            )}
        </div>
    );
}
