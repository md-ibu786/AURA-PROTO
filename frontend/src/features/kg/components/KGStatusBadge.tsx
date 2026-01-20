/**
 * ============================================================================
 * FILE: KGStatusBadge.tsx
 * LOCATION: frontend/src/features/kg/components/KGStatusBadge.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Visual badge component for displaying Knowledge Graph processing status.
 *    Shows status with icon and optional label, with different colors for
 *    pending, processing, ready, and failed states.
 *
 * ROLE IN PROJECT:
 *    Used in GridView to show KG status for each note. Provides at-a-glance
 *    status indication for documents in the processing pipeline.
 *
 * STATUS TYPES:
 *    - pending: Gray - Waiting to be processed
 *    - processing: Amber - Currently processing (spinning icon)
 *    - ready: Green - Successfully processed
 *    - failed: Red - Processing failed
 *
 * PROPS:
 *    - status?: KGDocumentStatus - Status to display (default: 'pending')
 *    - size?: 'sm' | 'md' - Badge size (default: 'md')
 *    - showLabel?: boolean - Show status text (default: true)
 *    - className?: string - Additional CSS classes
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons)
 *    - Internal: types/kg.types (KGDocumentStatus)
 *
 * @see: types/kg.types.ts - KGDocumentStatus type definition
 * @see: components/explorer/GridView.tsx - Usage location
 */
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

    const config: Record<KGDocumentStatus, {
        icon: typeof Clock;
        color: string;
        bg: string;
        label: string;
        animate?: boolean;
    }> = {
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
