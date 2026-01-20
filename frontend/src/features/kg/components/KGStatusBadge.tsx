import type { KGDocumentStatus } from '../types/kg.types';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

interface KGStatusBadgeProps {
    status?: KGDocumentStatus;
    size?: 'sm' | 'md';
    showLabel?: boolean;
    className?: string;
}

export function KGStatusBadge({
    status = 'pending',
    size = 'md',
    showLabel = true,
    className = ''
}: KGStatusBadgeProps) {

    const config = {
        pending: {
            icon: Clock,
            color: 'text-gray-400',
            bg: 'bg-gray-100',
            label: 'Pending'
        },
        processing: {
            icon: Loader2,
            color: 'text-amber-500',
            bg: 'bg-amber-50',
            label: 'Processing',
            animate: true
        },
        ready: {
            icon: CheckCircle2,
            color: 'text-green-500',
            bg: 'bg-green-50',
            label: 'Ready'
        },
        failed: {
            icon: XCircle,
            color: 'text-red-500',
            bg: 'bg-red-50',
            label: 'Failed'
        }
    };

    const style = config[status] || config.pending;
    const Icon = style.icon;
    const sizeClasses = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4';

    return (
        <div className={`flex items-center gap-1.5 ${className}`} title={style.label}>
            <div className={`p-1 rounded-full ${style.bg} ${style.color}`}>
                <Icon className={`${sizeClasses} ${style.animate ? 'animate-spin' : ''}`} />
            </div>
            {showLabel && (
                <span className={`text-xs font-medium ${style.color}`}>
                    {style.label}
                </span>
            )}
        </div>
    );
}
