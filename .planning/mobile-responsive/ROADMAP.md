# Roadmap: AURA-NOTES-MANAGER Mobile Responsiveness

## Overview

This roadmap implements full mobile responsiveness for the AURA-NOTES-MANAGER frontend. The existing desktop-first UI (Windows Explorer-style layout with fixed 280px sidebar, grid/list views, and floating action bars) will be retrofitted with responsive CSS `@media` queries and minimal React state changes to work seamlessly across mobile phones and tablets. The approach is "Hybrid Styling": maintain existing custom CSS architecture in `explorer.css` while adding mobile breakpoints, rather than rewriting in Tailwind.

## Reference Documentation

- @frontend/MOBILE_RESPONSIVE_PLAN.md - Feature specification with component requirements
- @frontend/src/styles/explorer.css - Core CSS architecture (1228 lines, desktop-first)
- @frontend/src/styles/index.css - Global styles and CSS variables

## Phases

- [ ] **Phase 1: Foundation & State** - Mobile state management and CSS breakpoint foundation
- [ ] **Phase 2: Sidebar Mobile** - Slide-in overlay sidebar with backdrop and auto-close
- [ ] **Phase 3: Header Mobile** - Hamburger menu, breadcrumb truncation, search collapse
- [ ] **Phase 4: Content Views Mobile** - Responsive ListView columns and GridView sizing
- [ ] **Phase 5: Dialogs & Action Bar** - Mobile-friendly floating action bar and dialog sizing
- [ ] **Phase 6: Testing & Verification** - Device emulation verification across breakpoints

## Phase Details

### Phase 1: Foundation & State
**Goal**: Establish mobile state management and CSS breakpoint infrastructure
**Depends on**: Nothing (first phase)
**Plans**: 2 plans

Plans:
- [ ] [01-01-PLAN.md](phases/01-foundation-state/01-01-PLAN.md): Add `mobileMenuOpen` state to `useExplorerStore.ts` and create `useMobileBreakpoint` custom hook
- [ ] [01-02-PLAN.md](phases/01-foundation-state/01-02-PLAN.md): Add mobile CSS foundation — `@media (max-width: 768px)` block, layout direction, overflow prevention, sidebar base mobile styles

Key Deliverables:
- `mobileMenuOpen` boolean + `setMobileMenuOpen` action in Zustand store
- `useMobileBreakpoint()` hook using `matchMedia` for `768px` breakpoint
- Mobile `@media` block in `explorer.css` with layout and sidebar transforms
- `overflow-x: hidden` on root container for mobile

### Phase 2: Sidebar Mobile
**Goal**: Transform sidebar into a mobile-friendly slide-in overlay with backdrop
**Depends on**: Phase 1
**Plans**: 2 plans

Plans:
- [ ] [02-01-PLAN.md](phases/02-sidebar-mobile/02-01-PLAN.md): Update `Sidebar.tsx` — mobile overlay with `translateX` animation, semi-transparent backdrop, close button in sidebar header
- [ ] [02-02-PLAN.md](phases/02-sidebar-mobile/02-02-PLAN.md): Auto-close sidebar on navigation events and backdrop click handling

Key Deliverables:
- Sidebar hidden by default on mobile (`transform: translateX(-100%)`)
- Slide-in animation with CSS transitions when `mobileMenuOpen` is true
- Semi-transparent backdrop overlay that closes sidebar on click
- Close "X" button visible in sidebar header on mobile
- Sidebar auto-closes when navigating to a new folder

### Phase 3: Header Mobile
**Goal**: Adapt header for mobile with hamburger menu, truncated breadcrumbs, and collapsible search
**Depends on**: Phase 2
**Plans**: 2 plans

Plans:
- [ ] [03-01-PLAN.md](phases/03-header-mobile/03-01-PLAN.md): Add hamburger icon button (visible only on mobile) to `Header.tsx`, truncate breadcrumbs to show only `... > [Current]`
- [ ] [03-02-PLAN.md](phases/03-header-mobile/03-02-PLAN.md): Collapse search bar to icon-toggle on small screens, adjust view toggle and header spacing

Key Deliverables:
- Hamburger button (Menu icon from lucide-react) wired to `setMobileMenuOpen(true)`
- Breadcrumbs truncated on mobile: show only Home + current folder
- Search bar collapses to search icon on mobile, expands on tap
- Header elements properly spaced without overflow

### Phase 4: Content Views Mobile
**Goal**: Make data views (ListView and GridView) readable and usable on mobile
**Depends on**: Phase 1 (CSS foundation)
**Plans**: 2 plans

Plans:
- [ ] [04-01-PLAN.md](phases/04-content-views-mobile/04-01-PLAN.md): Adapt `ListView` — hide Type, Modified, Count columns on mobile, give Name column full width
- [ ] [04-02-PLAN.md](phases/04-content-views-mobile/04-02-PLAN.md): Adapt `GridView` — reduce `minmax` to `100px`, adjust icon sizes and padding for mobile

Key Deliverables:
- ListView mobile: only Icon + Name columns visible (no horizontal scroll)
- ListView header hidden or simplified on mobile
- GridView mobile: smaller minimum column width, reduced padding
- Grid item icons and labels properly sized for touch targets
- No horizontal scrollbar on any view

### Phase 5: Dialogs & Action Bar
**Goal**: Ensure floating action bar and all dialogs are mobile-friendly
**Depends on**: Phase 1 (CSS foundation)
**Plans**: 2 plans

Plans:
- [ ] [05-01-PLAN.md](phases/05-dialogs-action-bar/05-01-PLAN.md): Make `SelectionActionBar` mobile-friendly — icon-only buttons (hide text labels), compact layout, responsive width
- [ ] [05-02-PLAN.md](phases/05-dialogs-action-bar/05-02-PLAN.md): Ensure UploadDialog, ConfirmDialog, ProcessDialog, DeleteFromKGDialog fit within `max-width: 90vw` on mobile

Key Deliverables:
- SelectionActionBar: icon-only mode on mobile (hide `<span>` text)
- Action bar fits within mobile viewport width
- All dialogs capped at `max-width: 90vw` on mobile
- Upload zone padding and file preview adjusted for small screens
- Dialog buttons properly sized for touch (min 44px touch target)

### Phase 6: Testing & Verification
**Goal**: Verify responsive layout across target devices using Chrome DevTools emulation
**Depends on**: All previous phases
**Plans**: 1 plan

Plans:
- [ ] [06-01-PLAN.md](phases/06-testing-verification/06-01-PLAN.md): Visual verification checkpoint — test on iPhone SE (375px), iPhone 12 (390px), iPad Air (820px) using dev server

Key Deliverables:
- No horizontal scrollbar on any device
- Navigation flow: Open menu → Click item → Menu closes → Content loads
- File names readable in both views
- All dialogs usable on mobile
- Touch targets minimum 44x44px

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & State | 0/2 | Not started | - |
| 2. Sidebar Mobile | 2/2 | Complete | 2026-02-13 |
| 3. Header Mobile | 0/2 | Not started | - |
| 4. Content Views Mobile | 0/2 | Not started | - |
| 5. Dialogs & Action Bar | 0/2 | Not started | - |
| 6. Testing & Verification | 0/1 | Not started | - |

## Plan Files

All executable plans are located in `.planning/mobile-responsive/phases/`:

```
.planning/mobile-responsive/phases/
├── 01-foundation-state/
│   ├── 01-01-PLAN.md   # Zustand state + useMobileBreakpoint hook
│   └── 01-02-PLAN.md   # CSS breakpoint foundation
├── 02-sidebar-mobile/
│   ├── 02-01-PLAN.md   # Sidebar overlay + backdrop + close button
│   └── 02-02-PLAN.md   # Auto-close on navigation
├── 03-header-mobile/
│   ├── 03-01-PLAN.md   # Hamburger button + breadcrumb truncation
│   └── 03-02-PLAN.md   # Search collapse + spacing
├── 04-content-views-mobile/
│   ├── 04-01-PLAN.md   # ListView column hiding
│   └── 04-02-PLAN.md   # GridView responsive sizing
├── 05-dialogs-action-bar/
│   ├── 05-01-PLAN.md   # SelectionActionBar compact mode
│   └── 05-02-PLAN.md   # Dialog mobile sizing
└── 06-testing-verification/
    └── 06-01-PLAN.md   # Device emulation verification
```

Execute plans with: `/run-plan .planning/mobile-responsive/phases/01-foundation-state/01-01-PLAN.md`

## CSS Breakpoint Strategy

| Breakpoint | Target | Usage |
|------------|--------|-------|
| `max-width: 768px` | Tablets & phones | Primary mobile breakpoint (sidebar, layout) |
| `max-width: 480px` | Small phones | Fine-tuning only (extra-small adjustments) |

## Technical Constraints

- **No Tailwind rewrite** — use existing CSS custom properties and `@media` queries
- **No horizontal scroll** — `overflow-x: hidden` on root container
- **Touch targets** — minimum 44x44px for all interactive elements (WCAG 2.1 AA)
- **Viewport meta** — already set correctly in `index.html`
- **Existing CSS architecture** — all responsive styles go in `explorer.css` media blocks
