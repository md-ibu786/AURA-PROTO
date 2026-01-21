/**
 * ============================================================================
 * FILE: KGStatusBadge.test.tsx
 * LOCATION: frontend/src/features/kg/components/KGStatusBadge.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for KGStatusBadge component. Tests rendering of different
 *    status states (pending, processing, ready, failed), size variants,
 *    label visibility, and styling classes.
 *
 * TEST COVERAGE:
 *    - Status rendering (pending, processing, ready, failed)
 *    - Size variants (sm, md)
 *    - Label visibility
 *    - Spinner animation for processing state
 *    - Color/styling classes
 *
 * @see: KGStatusBadge.tsx - Component under test
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KGStatusBadge } from './KGStatusBadge';

describe('KGStatusBadge', () => {
    describe('Status Rendering', () => {
        it('renders pending status correctly', () => {
            render(<KGStatusBadge status="pending" />);
            expect(screen.getByText('Pending')).toBeInTheDocument();
            expect(screen.getByTitle('Pending')).toBeInTheDocument();
        });

        it('renders processing status with spinner', () => {
            render(<KGStatusBadge status="processing" />);
            expect(screen.getByText('Processing')).toBeInTheDocument();
            // Check for animate-spin class on the icon
            const container = screen.getByTitle('Processing');
            const icon = container.querySelector('svg');
            expect(icon).toHaveClass('animate-spin');
        });

        it('renders ready status correctly', () => {
            render(<KGStatusBadge status="ready" />);
            expect(screen.getByText('Ready')).toBeInTheDocument();
        });

        it('renders failed status correctly', () => {
            render(<KGStatusBadge status="failed" />);
            expect(screen.getByText('Failed')).toBeInTheDocument();
        });

        it('defaults to pending when no status provided', () => {
            render(<KGStatusBadge />);
            expect(screen.getByText('Pending')).toBeInTheDocument();
        });
    });

    describe('Size Variants', () => {
        it('applies sm size classes', () => {
            render(<KGStatusBadge status="ready" size="sm" />);
            const container = screen.getByTitle('Ready');
            const icon = container.querySelector('svg');
            expect(icon).toHaveClass('h-3', 'w-3');
        });

        it('applies md size classes by default', () => {
            render(<KGStatusBadge status="ready" />);
            const container = screen.getByTitle('Ready');
            const icon = container.querySelector('svg');
            expect(icon).toHaveClass('h-4', 'w-4');
        });
    });

    describe('Label Visibility', () => {
        it('shows label by default', () => {
            render(<KGStatusBadge status="ready" />);
            expect(screen.getByText('Ready')).toBeInTheDocument();
        });

        it('hides label when showLabel is false', () => {
            render(<KGStatusBadge status="ready" showLabel={false} />);
            expect(screen.queryByText('Ready')).not.toBeInTheDocument();
            // But title should still be visible
            expect(screen.getByTitle('Ready')).toBeInTheDocument();
        });
    });

    describe('Styling', () => {
        it('applies correct color classes for pending', () => {
            render(<KGStatusBadge status="pending" />);
            const label = screen.getByText('Pending');
            expect(label).toHaveClass('text-gray-400');
        });

        it('applies correct color classes for processing', () => {
            render(<KGStatusBadge status="processing" />);
            const label = screen.getByText('Processing');
            expect(label).toHaveClass('text-amber-500');
        });

        it('applies correct color classes for ready', () => {
            render(<KGStatusBadge status="ready" />);
            const label = screen.getByText('Ready');
            expect(label).toHaveClass('text-green-500');
        });

        it('applies correct color classes for failed', () => {
            render(<KGStatusBadge status="failed" />);
            const label = screen.getByText('Failed');
            expect(label).toHaveClass('text-red-500');
        });

        it('applies custom className', () => {
            render(<KGStatusBadge status="ready" className="custom-class" />);
            const container = screen.getByTitle('Ready');
            expect(container).toHaveClass('custom-class');
        });
    });
});
