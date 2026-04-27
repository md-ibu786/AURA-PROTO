/**
 * ============================================================================
 * FILE: DateRangeFilter.tsx
 * LOCATION: frontend/src/features/usage/components/DateRangeFilter.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Date range filter with preset buttons for the usage dashboard.
 *
 * ROLE IN PROJECT:
 *    Provides two date input fields and quick-select preset buttons
 *    (7 days, 30 days, 90 days) for filtering usage data by time range.
 *    Styled with dark theme matching the Cyber Yellow design system.
 *
 * KEY COMPONENTS:
 *    - DateRangeFilter: Filter component with date inputs and preset buttons
 *    - DateRangeFilterProps: Interface for component props
 *    - formatDate: Utility to format Date as YYYY-MM-DD string
 *    - getPresetRange: Computes date ranges relative to today
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None
 *
 * USAGE:
 *    <DateRangeFilter
 *        startDate="2024-01-01"
 *        endDate="2024-01-31"
 *        onChange={(start, end) => setDateRange({ start, end })}
 *    />
 * ============================================================================
 */

interface DateRangeFilterProps {
    startDate: string;
    endDate: string;
    onChange: (start: string, end: string) => void;
}

function formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
}

function getPresetRange(days: number): { start: string; end: string } {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return { start: formatDate(start), end: formatDate(end) };
}

export function DateRangeFilter({ startDate, endDate, onChange }: DateRangeFilterProps) {
    const presets = [
        { label: '7 days', days: 7 },
        { label: '30 days', days: 30 },
        { label: '90 days', days: 90 },
    ];

    return (
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-3">
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                    <label htmlFor="usage-start-date" className="text-xs sm:text-sm text-gray-400">
                        From
                    </label>
                    <input
                        id="usage-start-date"
                        type="date"
                        value={startDate}
                        onChange={(e) => onChange(e.target.value, endDate)}
                        className="bg-card border border-border text-white text-xs sm:text-sm rounded-lg px-2 sm:px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <label htmlFor="usage-end-date" className="text-xs sm:text-sm text-gray-400">
                        To
                    </label>
                    <input
                        id="usage-end-date"
                        type="date"
                        value={endDate}
                        onChange={(e) => onChange(startDate, e.target.value)}
                        className="bg-card border border-border text-white text-xs sm:text-sm rounded-lg px-2 sm:px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                </div>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
                {presets.map(({ label, days }) => {
                    const preset = getPresetRange(days);
                    const isActive = startDate === preset.start && endDate === preset.end;
                    return (
                        <button
                            key={days}
                            onClick={() => onChange(preset.start, preset.end)}
                            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                isActive
                                    ? 'bg-primary/20 border-primary text-primary'
                                    : 'bg-card border-border text-gray-400 hover:border-gray-500 hover:text-white'
                            }`}
                        >
                            {label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
