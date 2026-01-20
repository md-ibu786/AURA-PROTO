import React from 'react';
import { useKGProcessing } from '../hooks/useKGProcessing';
import { Loader2, AlertCircle } from 'lucide-react';
import type { ProcessingQueueItem } from '../types/kg.types';

export function ProcessingQueue() {
    const { useProcessingQueue } = useKGProcessing();
    const { data: queue, isLoading, error } = useProcessingQueue();

    if (isLoading) return null;
    if (error) return <div className="text-red-500 text-sm p-4">Failed to load queue</div>;
    if (!queue || queue.length === 0) return null; // Hide if empty

    return (
        <div className="fixed bottom-24 right-6 w-80 bg-white dark:bg-zinc-800 shadow-xl rounded-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300 z-40">
            <div className="bg-zinc-50 dark:bg-zinc-900/50 px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 flex justify-between items-center">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    Processing ({queue.length})
                </h3>
            </div>

            <div className="max-h-60 overflow-y-auto">
                {queue.map((item) => (
                    <QueueItem key={item.document_id} item={item} />
                ))}
            </div>
        </div>
    );
}

function QueueItem({ item }: { item: ProcessingQueueItem }) {
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'processing': return 'text-amber-500';
            case 'failed': return 'text-red-500';
            case 'ready': return 'text-green-500';
            default: return 'text-zinc-500';
        }
    };

    return (
        <div className="px-4 py-3 border-b border-zinc-100 dark:border-zinc-700/50 last:border-0 hover:bg-zinc-50 dark:hover:bg-zinc-700/30 transition-colors">
            <div className="flex justify-between items-start mb-1.5">
                <span className="text-sm font-medium truncate max-w-[180px]" title={item.file_name}>
                    {item.file_name}
                </span>
                <span className={`text-xs font-medium capitalize ${getStatusColor(item.status)}`}>
                    {item.status}
                </span>
            </div>

            <div className="flex flex-col gap-1">
                <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-700 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary transition-all duration-500 ease-out"
                        style={{ width: `${item.progress}%` }}
                    />
                </div>
                <div className="flex justify-between text-[10px] text-zinc-500">
                    <span>{item.step}</span>
                    <span>{Math.round(item.progress)}%</span>
                </div>
                {item.error && (
                    <div className="text-[10px] text-red-500 flex items-center gap-1 mt-1">
                        <AlertCircle className="h-3 w-3" />
                        {item.error}
                    </div>
                )}
            </div>
        </div>
    );
}
