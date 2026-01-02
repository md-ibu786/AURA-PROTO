/**
 * Context Menu Component
 */
import { useExplorerStore } from '../../stores';
import { useQueryClient } from '@tanstack/react-query';
import {
    FolderOpen,
    Edit,
    Trash2,
    Plus,
    Download,
    FileText,
    ExternalLink
} from 'lucide-react';
import type { FileSystemNode, HierarchyType } from '../../types';
import * as api from '../../api';

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
        startCreating
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

    const handleDelete = async () => {
        const confirmed = confirm(`Are you sure you want to delete "${node.label}"? This action cannot be undone.`);
        if (!confirmed) {
            closeContextMenu();
            return;
        }

        try {
            const id = parseInt(node.id.split('-')[1]);

            switch (node.type) {
                case 'department':
                    await api.deleteDepartment(id);
                    break;
                case 'semester':
                    await api.deleteSemester(id);
                    break;
                case 'subject':
                    await api.deleteSubject(id);
                    break;
                case 'module':
                    await api.deleteModule(id);
                    break;
                case 'note':
                    await api.deleteNote(id);
                    break;
            }

            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
        } catch (error) {
            alert(`Failed to delete: ${(error as Error).message}`);
        }

        closeContextMenu();
    };

    const handleCreate = () => {
        if (!childType) return;

        // Get parent ID for the new item
        const parentId = parseInt(node.id.split('-')[1]);

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

            <button className="context-menu-item danger" onClick={handleDelete}>
                <Trash2 size={16} />
                <span>Delete</span>
            </button>
        </div>
    );
}
