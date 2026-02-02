// SelectionOverlay.tsx
// Visual "rubber-band" selection box component

// Handles mouse events to draw a selection rectangle and identifies 
// intersecting "selectable-item" elements to update global selection state.
// Coordinates are handled in viewport space for comparison with 
// getBoundingClientRect() results. Uses flex: 1 to integrate with
// ExplorerPage's flex layout.

// @see: ExplorerPage.tsx - Where this component is integrated
// @see: useExplorerStore.ts - For selectAll and clearSelection actions
// @note: Container must be a flex item to support scrolling children correctly.

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useExplorerStore } from '../../stores/useExplorerStore';

interface SelectionBox {
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
}

export const SelectionOverlay: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    
    const { selectAll, clearSelection, currentPath } = useExplorerStore();

    const isInsideModule = currentPath.length > 0 && currentPath[currentPath.length - 1].type === 'module';

    const handleMouseDown = (e: React.MouseEvent) => {
        // Only trigger inside modules
        if (!isInsideModule) return;

        // Only trigger on primary button and on the container itself (empty space)
        // or elements that don't have a data-id (not a file/folder)
        if (e.button !== 0) return;
        
        const target = e.target as HTMLElement;
        const isSelectable = target.closest('.selectable-item');
        const isInteractive = target.closest('button, input, a, [role="button"]');
        
        if (isSelectable || isInteractive) return;

        setIsDragging(true);
        setSelectionBox({
            startX: e.clientX,
            startY: e.clientY,
            currentX: e.clientX,
            currentY: e.clientY
        });
    };

    const handleMouseMove = useCallback((e: MouseEvent) => {
        if (!isDragging) return;

        setSelectionBox(prev => prev ? ({
            ...prev,
            currentX: e.clientX,
            currentY: e.clientY
        }) : null);
    }, [isDragging]);

    const handleMouseUp = useCallback(() => {
        if (!isDragging || !selectionBox) {
            setIsDragging(false);
            setSelectionBox(null);
            return;
        }

        const { startX, startY, currentX, currentY } = selectionBox;
        
        // Calculate the bounding box of the selection
        const left = Math.min(startX, currentX);
        const top = Math.min(startY, currentY);
        const right = Math.max(startX, currentX);
        const bottom = Math.max(startY, currentY);
        
        const width = right - left;
        const height = bottom - top;

        // If it's just a click (minimal movement), clear selection
        if (width < 5 && height < 5) {
            clearSelection();
        } else {
            // Identify all intersecting selectable items
            const selectableElements = document.querySelectorAll('.selectable-item');
            const selectedIds: string[] = [];

            selectableElements.forEach((el) => {
                const rect = el.getBoundingClientRect();
                const id = el.getAttribute('data-id');

                if (id && 
                    rect.left < right && 
                    rect.right > left && 
                    rect.top < bottom && 
                    rect.bottom > top) {
                    selectedIds.push(id);
                }
            });

            if (selectedIds.length > 0) {
                selectAll(selectedIds);
            } else {
                clearSelection();
            }
        }

        setIsDragging(false);
        setSelectionBox(null);
    }, [isDragging, selectionBox, selectAll, clearSelection]);

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        } else {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    const renderSelectionBox = () => {
        if (!selectionBox) return null;

        const { startX, startY, currentX, currentY } = selectionBox;
        const left = Math.min(startX, currentX);
        const top = Math.min(startY, currentY);
        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);

        return (
            <div 
                className="selection-box"
                style={{
                    left: `${left}px`,
                    top: `${top}px`,
                    width: `${width}px`,
                    height: `${height}px`
                }}
            />
        );
    };

    return (
        <div 
            ref={containerRef}
            data-testid="selection-overlay-container"
            onMouseDown={handleMouseDown}
            style={{ 
                position: 'relative', 
                width: '100%', 
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
                userSelect: isDragging ? 'none' : 'auto'
            }}
        >
            {children}
            {renderSelectionBox()}
        </div>
    );
};
