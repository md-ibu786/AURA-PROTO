/**
 * @vitest-environment jsdom
 */
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WarningDialog } from './WarningDialog';
import { useExplorerStore } from '../../stores';

// Mock Lucide icons
vi.mock('lucide-react', () => ({
    AlertTriangle: () => <div data-testid="alert-icon" />,
    X: () => <div data-testid="close-icon" />
}));

describe('WarningDialog', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            warningDialog: { isOpen: false, type: 'error', message: '' },
            warningTimeoutId: null
        });
    });

    afterEach(() => {
        cleanup();
    });

    it('should not render when isOpen is false', () => {
        render(<WarningDialog />);
        expect(screen.queryByTestId('warning-dialog')).toBeNull();
    });

    it('should render correct content when isOpen is true', () => {
        useExplorerStore.setState({
            warningDialog: { 
                isOpen: true, 
                type: 'duplicate', 
                message: 'Department already exists', 
                entityName: 'Engineering' 
            }
        });

        render(<WarningDialog />);
        
        expect(screen.getByText('Department already exists')).toBeTruthy();
        expect(screen.getByText('Engineering')).toBeTruthy();
        expect(screen.getByTestId('alert-icon')).toBeTruthy();
    });

    it('should close dialog when close button is clicked', () => {
        useExplorerStore.setState({
            warningDialog: { 
                isOpen: true, 
                type: 'duplicate', 
                message: 'Test' 
            }
        });

        render(<WarningDialog />);
        
        const closeBtn = screen.getByRole('button', { name: /close/i });
        fireEvent.click(closeBtn);

        expect(useExplorerStore.getState().warningDialog.isOpen).toBe(false);
    });
});
