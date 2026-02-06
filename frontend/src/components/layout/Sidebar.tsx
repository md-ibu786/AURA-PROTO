/**
 * ============================================================================
 * FILE: Sidebar.tsx
 * LOCATION: frontend/src/components/layout/Sidebar.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Left sidebar panel containing the tree navigation and contextual
 *    action button. Provides persistent navigation while browsing the
 *    main content area.
 *
 * ROLE IN PROJECT:
 *    Main navigation container that wraps SidebarTree. Also manages the
 *    contextual "Create" or "Upload" button based on current navigation
 *    depth.
 *
 * KEY FEATURES:
 *    - Header with "Explorer" title and folder tree icon
 *    - SidebarTree component for recursive tree navigation
 *    - Contextual bottom button:
 *      - Depth 0: "New Department"
 *      - Depth 1: "New Semester"
 *      - Depth 2: "New Subject"
 *      - Depth 3: "New Module"
 *      - Depth 4 (module): "Upload Notes" → opens UploadDialog
 *
 * DEPENDENCIES:
 *    - External: lucide-react
 *    - Internal: stores/useExplorerStore, SidebarTree, UploadDialog, types
 *
 * PROPS:
 *    - tree: FileSystemNode[] - Full hierarchy tree
 *    - isLoading: boolean - Show loading spinner
 *
 * USAGE:
 *    <Sidebar tree={tree} isLoading={isLoading} />
 * ============================================================================
 */
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useExplorerStore } from '../../stores';
import { useAuthStore } from '../../stores/useAuthStore';
import { SidebarTree } from '../explorer/SidebarTree';
import { UploadDialog } from '../explorer/UploadDialog';
import type { FileSystemNode, HierarchyType } from '../../types';
import { FolderTree, Upload, Plus, LogOut, Shield, LayoutGrid } from 'lucide-react';

interface SidebarProps {
    tree: FileSystemNode[];
    isLoading: boolean;
}

export function Sidebar({ tree, isLoading }: SidebarProps) {
    const { currentPath, startCreating } = useExplorerStore();
    const { user, logout } = useAuthStore();
    const location = useLocation();
    const [isUploadOpen, setIsUploadOpen] = useState(false);

    const isAdmin = user?.role === 'admin';
    const isAdminPath = location.pathname.startsWith('/admin');

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

    // Get create button config based on depth and user permissions
    const getCreateConfig = (): { label: string; type: HierarchyType } | null => {
        // Only admins can create departments, semesters, and subjects
        // Only staff can create modules and upload notes
        switch (pathDepth) {
            case 0:
                // Department creation - admin only
                return isAdmin ? { label: 'New Department', type: 'department' } : null;
            case 1:
                // Semester creation - admin only
                return isAdmin ? { label: 'New Semester', type: 'semester' } : null;
            case 2:
                // Subject creation - admin only
                return isAdmin ? { label: 'New Subject', type: 'subject' } : null;
            case 3:
                // Module creation - staff only (NOT admin)
                return !isAdmin && user?.role === 'staff'
                    ? { label: 'New Module', type: 'module' }
                    : null;
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
                    <span className="sidebar-title">AURA</span>
                </div>
            </div>

            <div className="sidebar-content">
                {isAdmin && (
                    <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <Link 
                            to="/" 
                            className={`flex items-center gap-sm p-sm rounded-md transition-colors ${!isAdminPath ? 'bg-accent text-black font-bold' : 'hover:bg-white/5 text-secondary'}`}
                        >
                            <LayoutGrid size={18} />
                            <span>Explorer</span>
                        </Link>
                        <Link 
                            to="/admin" 
                            className={`flex items-center gap-sm p-sm rounded-md transition-colors ${isAdminPath ? 'bg-accent text-black font-bold' : 'hover:bg-white/5 text-secondary'}`}
                        >
                            <Shield size={18} />
                            <span>Admin Dashboard</span>
                        </Link>
                        <div style={{ margin: '8px 0', borderBottom: '1px solid var(--color-border)', opacity: 0.5 }} />
                    </div>
                )}

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
                ) : isAtModuleLevel && currentModule && !isAdmin && user?.role === 'staff' ? (
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

            {/* User info and logout at bottom */}
            {user && (
                <div style={{ padding: '12px', borderTop: '1px solid var(--color-border)', backgroundColor: 'rgba(255, 212, 0, 0.05)' }}>
                    <div style={{ marginBottom: '8px' }}>
                        <p style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{user.displayName}</p>
                        <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>{user.role}</p>
                    </div>
                    <button
                        onClick={() => logout()}
                        className="btn"
                        style={{ 
                            width: '100%', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center', 
                            gap: '8px',
                            padding: '6px 12px',
                            fontSize: '12px',
                            color: '#ff4444',
                            borderColor: '#ff4444',
                            backgroundColor: 'transparent'
                        }}
                    >
                        <LogOut size={14} />
                        Sign out
                    </button>
                </div>
            )}
        </aside>
    );
}
