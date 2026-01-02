/**
 * Header Component - Breadcrumbs, search, view toggle
 */
import { useExplorerStore } from '../../stores';
import {
    ChevronRight,
    ChevronUp,
    Search,
    LayoutGrid,
    List,
    Home
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
        setActiveNode
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
        </header>
    );
}

