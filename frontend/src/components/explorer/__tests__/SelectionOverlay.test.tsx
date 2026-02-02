// SelectionOverlay.test.tsx
// Integration tests for the Rubber-Band Selection behavior

// Tests the mouse drag interactions (mousedown, mousemove, mouseup) to ensure
// they correctly calculate intersections with DOM elements and update the
// explorer store with selected IDs.

// @see: SelectionOverlay.tsx - The component being tested
// @see: useExplorerStore.ts - The state store being mocked

/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/react';
import { SelectionOverlay } from '../SelectionOverlay';
import { useExplorerStore } from '../../../stores/useExplorerStore';
import type { FileSystemNode } from '../../../types';

// Mock getBoundingClientRect for intersection tests
// In JSDOM, getBoundingClientRect returns all zeros by default.
const mockGetBoundingClientRect = (rect: { x: number; y: number; width: number; height: number }) => {
    return {
        x: rect.x,
        y: rect.y,
        top: rect.y,
        left: rect.x,
        bottom: rect.y + rect.height,
        right: rect.x + rect.width,
        width: rect.width,
        height: rect.height,
        toJSON: () => {},
    } as DOMRect;
};

describe('SelectionOverlay', () => {
    const mockSelectAll = vi.fn();
    const mockClearSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        useExplorerStore.setState({
            selectAll: mockSelectAll,
            clearSelection: mockClearSelection,
            currentPath: [{ id: 'mod-1', label: 'Module 1', type: 'module', parentId: null } as FileSystemNode],
        });

        // Mock document.querySelectorAll to return "selectable-item" elements
        const element1 = document.createElement('div');
        element1.className = 'selectable-item';
        element1.setAttribute('data-id', 'id-1');
        element1.getBoundingClientRect = vi.fn(() => mockGetBoundingClientRect({ x: 10, y: 10, width: 50, height: 50 }));

        const element2 = document.createElement('div');
        element2.className = 'selectable-item';
        element2.setAttribute('data-id', 'id-2');
        element2.getBoundingClientRect = vi.fn(() => mockGetBoundingClientRect({ x: 100, y: 100, width: 50, height: 50 }));

        document.body.appendChild(element1);
        document.body.appendChild(element2);
    });

    afterEach(() => {
        cleanup();
        document.body.innerHTML = '';
    });

    it('renders the overlay container', () => {
        const { getByTestId } = render(<SelectionOverlay />);
        expect(getByTestId('selection-overlay-container')).toBeInTheDocument();
    });

    it('triggers selectAll when dragging over items', () => {
        const { getByTestId } = render(<SelectionOverlay />);
        const container = getByTestId('selection-overlay-container');

        // Drag from 0,0 to 70,70 (should intersect element1 but not element2)
        fireEvent.mouseDown(container, { clientX: 0, clientY: 0 });
        fireEvent.mouseMove(container, { clientX: 70, clientY: 70 });
        fireEvent.mouseUp(container);

        expect(mockSelectAll).toHaveBeenCalledWith(['id-1']);
    });

    it('triggers selectAll with multiple items when dragging over them', () => {
        const { getByTestId } = render(<SelectionOverlay />);
        const container = getByTestId('selection-overlay-container');

        // Drag from 0,0 to 160,160 (should intersect both)
        fireEvent.mouseDown(container, { clientX: 0, clientY: 0 });
        fireEvent.mouseMove(container, { clientX: 160, clientY: 160 });
        fireEvent.mouseUp(container);

        expect(mockSelectAll).toHaveBeenCalledWith(['id-1', 'id-2']);
    });

    it('clears selection on click without significant movement', () => {
        const { getByTestId } = render(<SelectionOverlay />);
        const container = getByTestId('selection-overlay-container');

        fireEvent.mouseDown(container, { clientX: 5, clientY: 5 });
        fireEvent.mouseUp(container, { clientX: 6, clientY: 6 });

        expect(mockClearSelection).toHaveBeenCalled();
        expect(mockSelectAll).not.toHaveBeenCalled();
    });
});
