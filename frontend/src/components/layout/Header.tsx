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
import { useEffect, useState } from 'react';
import { useMobileBreakpoint } from '../../hooks/useMobileBreakpoint';
import { useExplorerStore } from '../../stores';
import {
    ChevronRight,
    ChevronUp,
    Search,
    LayoutGrid,
    List,
    Home,
    Menu,
    X
} from 'lucide-react';

export function Header() {
    const isMobile = useMobileBreakpoint();
    const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

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
        setDeleteMode,
        setMobileMenuOpen,
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
            setDeleteMode(false);
        }
    }, [isInsideModule, selectionMode, setSelectionMode, setDeleteMode]);


    return (
        <header className="explorer-header">
            {/* Hamburger menu button - mobile only */}
            {isMobile && (
                <button
                    className="nav-btn"
                    onClick={() => setMobileMenuOpen(true)}
                    title="Open menu"
                >
                    <Menu size={20} />
                </button>
            )}

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
                    {!isMobile && <span>Home</span>}
                </button>

                {isMobile && currentPath.length > 0 ? (
                    <span className="flex items-center">
                        <ChevronRight size={14} className="breadcrumb-separator" />
                        {currentPath.length > 1 && (
                            <>
                                <span className="breadcrumb-item" style={{ opacity: 0.5 }}>...</span>
                                <ChevronRight size={14} className="breadcrumb-separator" />
                            </>
                        )}
                        <button
                            className="breadcrumb-item active"
                            onClick={() => navigateToBreadcrumb(currentPath.length - 1)}
                        >
                            {currentPath[currentPath.length - 1].label}
                        </button>
                    </span>
                ) : (
                    currentPath.map((node, index) => (
                        <span key={node.id} className="flex items-center">
                            <ChevronRight size={14} className="breadcrumb-separator" />
                            <button
                                className={`breadcrumb-item ${index === currentPath.length - 1 ? 'active' : ''}`}
                                onClick={() => navigateToBreadcrumb(index)}
                            >
                                {node.label}
                            </button>
                        </span>
                    ))
                )}
            </nav>


            {/* Search */}
            {isMobile ? (
                mobileSearchOpen ? (
                    <div className="search-box mobile-search-expanded">
                        <Search size={16} className="text-muted" />
                        <input
                            type="text"
                            placeholder="Search..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            autoFocus
                            onBlur={() => {
                                if (!searchQuery) {
                                    setMobileSearchOpen(false);
                                }
                            }}
                        />
                        <button
                            className="nav-btn"
                            onClick={() => {
                                setSearchQuery('');
                                setMobileSearchOpen(false);
                            }}
                            style={{ width: '24px', height: '24px' }}
                        >
                            <X size={14} />
                        </button>
                    </div>
                ) : (
                    <button
                        className="nav-btn"
                        onClick={() => setMobileSearchOpen(true)}
                        title="Search"
                    >
                        <Search size={18} />
                    </button>
                )
            ) : (
                <div className="search-box ml-auto">
                    <Search size={16} className="text-muted" />
                    <input
                        type="text"
                        placeholder="Search..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            )}


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
        </header>
    );
}

