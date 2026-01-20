/**
 * ============================================================================
 * FILE: Header.tsx
 * LOCATION: frontend/src/components/layout/Header.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Top navigation bar for the explorer with breadcrumbs, search, view
 *    toggles, and selection mode controls. Provides primary navigation
 *    and action controls above the main content area.
 *
 * ROLE IN PROJECT:
 *    Header component that manages:
 *    - Breadcrumb navigation with click-to-navigate
 *    - Search filtering for current folder
 *    - View mode toggle (grid/list)
 *    - Selection mode for KG processing
 *
 * KEY FEATURES:
 *    Navigation:
 *    - Up button (navigate to parent)
 *    - Home button (return to root)
 *    - Breadcrumb trail with click navigation
 *
 *    Search:
 *    - Real-time filtering via searchQuery state
 *
 *    View Toggle:
 *    - Grid view (LayoutGrid icon)
 *    - List view (List icon)
 *
 *    Selection Mode (module-level only):
 *    - Toggle between selection/browse modes
 *    - Shows selected count
 *    - Process button for KG vectorization
 *
 * STATE:
 *    - searchQuery: Filter text for current folder
 *    - viewMode: 'grid' or 'list'
 *    - selectionMode: Multi-select enabled
 *    - selectedIds: Set of selected item IDs
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons)
 *    - Internal: stores/useExplorerStore
 *
 * @see: stores/useExplorerStore.ts - For navigation and UI state
 * @note: Automatically disables selection mode when navigating out of modules
 */
import { useEffect } from 'react';
import { useExplorerStore } from '../../stores';
import {
    ChevronRight,
    ChevronUp,
    Search,
    LayoutGrid,
    List,
    Home,
    Zap,
    XCircle,
    Trash2,
    X
} from 'lucide-react';

export function Header() {
    const {
        currentPath,
        navigateUp,
        setCurrentPath,
        viewMode,
        setViewMode,
        searchQuery,
        setSearchQuery,
        setActiveNode,
        selectionMode,
        setSelectionMode,
        selectedIds,
        clearSelection,
        openProcessDialog
    } = useExplorerStore();

    const goHome = () => {
        setCurrentPath([]);
        setActiveNode(null);
    };

    const navigateToBreadcrumb = (index: number) => {
        if (index < 0) {
            goHome();
        } else {
            const newPath = currentPath.slice(0, index + 1);
            setCurrentPath(newPath);
            setActiveNode(newPath[newPath.length - 1]);
        }
    };

    // Check if we are currently inside a module folder
    const isInsideModule = currentPath.length > 0 && currentPath[currentPath.length - 1].type === 'module';

    // Automatically disable selection mode if we navigate out of a module
    useEffect(() => {
        if (!isInsideModule && selectionMode) {
            setSelectionMode(false);
        }
    }, [isInsideModule, selectionMode, setSelectionMode]);


    return (
        <header className="explorer-header">
            {/* Navigation buttons */}
            <div className="nav-buttons">
                <button
                    className="nav-btn"
                    onClick={navigateUp}
                    disabled={currentPath.length === 0}
                    title="Go up"
                >
                    <ChevronUp size={18} />
                </button>
                <button
                    className="nav-btn"
                    onClick={goHome}
                    title="Go home"
                >
                    <Home size={18} />
                </button>
            </div>

            {/* Breadcrumbs */}
            <nav className="breadcrumbs">
                <button
                    className={`breadcrumb-item ${currentPath.length === 0 ? 'active' : ''}`}
                    onClick={goHome}
                >
                    <Home size={14} />
                    <span>Home</span>
                </button>

                {currentPath.map((node, index) => (
                    <span key={node.id} className="flex items-center">
                        <ChevronRight size={14} className="breadcrumb-separator" />
                        <button
                            className={`breadcrumb-item ${index === currentPath.length - 1 ? 'active' : ''}`}
                            onClick={() => navigateToBreadcrumb(index)}
                        >
                            {node.label}
                        </button>
                    </span>
                ))}
            </nav>


            {/* Selection Mode Toggle - Only visible inside modules */}
            {isInsideModule && (
                <button
                    className="flex items-center gap-2 px-3 py-1.5 mr-4 rounded-md text-sm font-medium transition-colors"
                    style={{
                        color: selectionMode ? '#ef4444' : '#22c55e'
                    }}
                    onClick={() => {
                        if (selectionMode) {
                            clearSelection();
                            setSelectionMode(false);
                        } else {
                            setSelectionMode(true);
                        }
                    }}
                    title={selectionMode ? 'Exit selection mode' : 'Select notes for vectorization'}
                >
                    {selectionMode ? (
                        <>
                            <XCircle className="h-4 w-4" />
                            Deselect All
                        </>
                    ) : (
                        <>
                            <Zap className="h-4 w-4" />
                            Vectorize the notes
                        </>
                    )}
                </button>
            )}

            {/* Search */}
            <div className="search-box">
                <Search size={16} className="text-muted" />
                <input
                    type="text"
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {/* View toggle */}
            <div className="view-toggle">
                <button
                    className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setViewMode('grid')}
                    title="Grid view"
                >
                    <LayoutGrid size={16} />
                </button>
                <button
                    className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                    onClick={() => setViewMode('list')}
                    title="List view"
                >
                    <List size={16} />
                </button>
            </div>

            {/* Selection Mode Actions - Shows count and process button */}
            {selectionMode && (
                <>
                    <div className="h-6 w-px bg-border mx-2" style={{ marginLeft: 'auto' }} />
                    <div className="flex items-center gap-md">
                        <span
                            className="text-accent font-medium whitespace-nowrap"
                            style={{ fontSize: '14px' }}
                        >
                            {selectedIds.size} Selected
                        </span>
                        <button
                            className="btn btn-primary"
                            onClick={() => {
                                if (selectedIds.size > 0) {
                                    const currentModuleId = currentPath[currentPath.length - 1]?.id || '';
                                    openProcessDialog(Array.from(selectedIds), currentModuleId);
                                }
                            }}
                            disabled={selectedIds.size === 0}
                            title="Process selected documents for Knowledge Graph"
                            style={{ padding: '6px 16px' }}
                        >
                            <Zap size={16} />
                            Process
                        </button>
                        <div className="flex items-center gap-xs">
                            <button
                                className="nav-btn"
                                onClick={clearSelection}
                                title="Clear selection"
                            >
                                <Trash2 size={18} />
                            </button>
                            <button
                                className="nav-btn"
                                onClick={() => {
                                    clearSelection();
                                    setSelectionMode(false);
                                }}
                                title="Exit selection mode"
                            >
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                </>
            )}
        </header>
    );
}
