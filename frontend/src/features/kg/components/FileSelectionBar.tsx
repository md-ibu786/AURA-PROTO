// FileSelectionBar.tsx
// Floating action bar for processing selected notes in the knowledge graph pipeline

// Component that appears when selection mode is active, allowing users to
// batch process selected documents (vectorization), clear selection, or
// exit selection mode. Displays the count of currently selected items.

// @see: stores/useExplorerStore.ts - For selection state management
// @see: features/kg/hooks/useKGProcessing.ts - For processing logic
// @note: Only visible when selectionMode is true in useExplorerStore
// @note: Functionality moved to Header.tsx, this component now returns null.

export function FileSelectionBar() {
    return null;
}
