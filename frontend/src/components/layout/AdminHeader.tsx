// AdminHeader.tsx
// Persistent, shared top navigation header for Admin pages.

// Includes navigation buttons for Dashboard, Settings, Usage, and Logout.
// Visually highlights the currently active page using a glowing cyber-yellow background.

import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { cn } from '../../lib/cn';
import { ArrowLeft } from 'lucide-react';

interface AdminHeaderProps {
    title: string;
    subtitle?: string;
    showBack?: boolean;
}

export function AdminHeader({ title, subtitle, showBack }: AdminHeaderProps) {
    const { user, logout } = useAuthStore();
    const location = useLocation();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const navItems = [
        { name: 'Dashboard', path: '/admin' },
        { name: 'Settings', path: '/settings' },
        { name: 'Usage', path: '/usage' },
    ];

    return (
        <header className="flex justify-between items-center px-4 md:px-6 py-3 md:py-4 bg-[#0A0A0A] border-b border-gray-800 shrink-0">
            <div className="flex flex-col">
                <div className="flex items-center gap-2">
                    {showBack && (
                        <button
                            onClick={() => navigate(-1)}
                            className="p-2 hover:bg-white/10 rounded-full transition-colors -ml-2"
                            title="Back"
                        >
                            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                        </button>
                    )}
                    <h1 className="text-xl sm:text-2xl font-bold text-[#FFD400]">{title}</h1>
                </div>
                <span className="text-sm text-gray-400 mt-1 ml-1">
                    {subtitle || `Logged in as: ${user?.displayName || user?.email}`}
                </span>
            </div>
            <div className="flex items-center gap-2">
                {navItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <Link
                            key={item.name}
                            to={item.path}
                            className={cn(
                                "px-4 py-2 rounded-md font-medium transition-all duration-200 text-sm",
                                isActive 
                                    ? "bg-[#FFD400] text-black shadow-[0_0_15px_rgba(255,212,0,0.6)]" 
                                    : "text-gray-400 hover:text-white hover:bg-white/10"
                            )}
                        >
                            {item.name}
                        </Link>
                    );
                })}
                <button
                    className="px-4 py-2 rounded-md font-medium text-red-500 hover:text-white hover:bg-red-500/20 transition-all duration-200 text-sm ml-2"
                    onClick={handleLogout}
                >
                    Logout
                </button>
            </div>
        </header>
    );
}
