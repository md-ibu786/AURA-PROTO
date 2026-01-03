/**
 * Sidebar Component - Tree navigation + contextual create button
 */
import { useState } from 'react';
import { useExplorerStore } from '../../stores';
import { SidebarTree } from '../explorer/SidebarTree';
import { UploadDialog } from '../explorer/UploadDialog';
import type { FileSystemNode, HierarchyType } from '../../types';
import { FolderTree, Upload, Plus } from 'lucide-react';

interface SidebarProps {
    tree: FileSystemNode[];
    isLoading: boolean;
}

export function Sidebar({ tree, isLoading }: SidebarProps) {
    const { currentPath, startCreating } = useExplorerStore();
    const [isUploadOpen, setIsUploadOpen] = useState(false);

    // Determine what we can create based on current path depth
    // 0 = root (create department)
    // 1 = inside department (create semester)
    // 2 = inside semester (create subject)
    // 3 = inside subject (create module)
    // 4 = inside module (upload notes)
    const pathDepth = currentPath.length;
    const currentNode = currentPath[currentPath.length - 1];

    const isAtModuleLevel = pathDepth === 4 && currentNode?.type === 'module';
    const currentModule = isAtModuleLevel ? currentNode : null;
    const moduleId = currentModule?.id ?? '';

    // Get create button config based on depth
    const getCreateConfig = (): { label: string; type: HierarchyType } | null => {
        switch (pathDepth) {
            case 0:
                return { label: 'New Department', type: 'department' };
            case 1:
                return { label: 'New Semester', type: 'semester' };
            case 2:
                return { label: 'New Subject', type: 'subject' };
            case 3:
                return { label: 'New Module', type: 'module' };
            default:
                return null; // At module level, show upload instead
        }
    };

    const createConfig = getCreateConfig();

    const handleCreate = () => {
        if (createConfig) {
            // Get parent ID from current path (null for root/departments)
            const parentId = currentNode?.id ?? null;
            startCreating(createConfig.type, parentId);
        }
    };

    return (
        <aside className="explorer-sidebar">
            <div className="sidebar-header">
                <div className="flex items-center gap-sm">
                    <FolderTree size={18} className="text-accent" />
                    <span className="sidebar-title">Explorer</span>
                </div>
            </div>

            <div className="sidebar-content">
                {isLoading ? (
                    <div className="flex items-center justify-center" style={{ padding: '24px' }}>
                        <div className="spinner" />
                    </div>
                ) : (
                    <SidebarTree nodes={tree} level={0} ancestors={[]} />
                )}
            </div>

            {/* Contextual create button at bottom */}
            <div style={{ padding: '12px', borderTop: '1px solid var(--color-border)', marginTop: 'auto' }}>
                {createConfig ? (
                    <button
                        className="btn btn-primary"
                        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                        onClick={handleCreate}
                    >
                        <Plus size={16} />
                        {createConfig.label}
                    </button>
                ) : isAtModuleLevel && currentModule ? (
                    <button
                        className="btn btn-primary"
                        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                        onClick={() => setIsUploadOpen(true)}
                    >
                        <Upload size={16} />
                        Upload Notes
                    </button>
                ) : null}
            </div>

            {/* Upload Dialog */}
            <UploadDialog
                isOpen={isUploadOpen}
                onClose={() => setIsUploadOpen(false)}
                moduleId={moduleId}
                moduleName={currentModule?.label || ''}
            />
        </aside>
    );
}
