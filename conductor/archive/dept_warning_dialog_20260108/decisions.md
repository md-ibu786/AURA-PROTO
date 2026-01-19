# Technology Decisions: Duplicate Department Warning Dialog

## 1. Notification Library
**Decision:** `sonner`
**Reasoning:**
- Highly customizable and unopinionated styling, perfect for our custom "sliding from top" requirement.
- Lightweight (~1kb) compared to other robust options.
- Built-in `Promise` support for async operations.
- Accessible out of the box.

## 2. Animation Strategy
**Decision:** `framer-motion`
**Reasoning:**
- Provides `AnimatePresence` which is critical for handling the "exit" animation of the dialog when it's dismissed.
- Simplifies complex spring animations for the slide-in effect.
- Easy integration with `prefers-reduced-motion` for accessibility compliance.

## 3. Error Handling Pattern
**Decision:** 409 Conflict Response
**Backend:**
- `create_department` endpoint will check for duplicate names.
- If duplicate: Raise `HTTPException(status_code=409, detail="Department with this name already exists")`.
**Frontend:**
- API client wrapper will detect 409 status.
- It will NOT throw a generic error but return a specific error object or throw a typed `DuplicateNameError`.
- The UI layer (Sidebar/Dialog) will catch this specific error and trigger the warning dialog state.

## 4. State Management (Zustand)
**Decision:** Extend `useExplorerStore`
**Schema:**
```typescript
interface ExplorerState {
  // ... existing state
  warningDialog: {
    isOpen: boolean;
    type: 'duplicate' | 'error';
    message: string;
    entityName?: string; // The name that caused the conflict
  };
  setWarningDialog: (state: Partial<ExplorerState['warningDialog']>) => void;
  closeWarningDialog: () => void;
}
```
**Timeout Handling:**
- The `sonner` library handles auto-dismissal internally if we use it directly.
- **However**, since the requirements specify a *custom* top-sliding warning dialog (which might act more like a modal than a toast), we will manage visibility in Zustand.
- We will use `setTimeout` in the `openWarningDialog` action, clearing any existing timeout to prevent race conditions.

## 5. Accessibility
- **ARIA:** The dialog will use `role="alertdialog"` or `role="alert"` depending on whether it blocks interaction.
- **Focus:** If blocking, focus will be trapped. If non-blocking (toast style), no focus trap, but accessible via keyboard.
- **Announcements:** Use `aria-live` regions for screen readers to announce the error immediately.
