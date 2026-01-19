# Migration Plan: AURA-PROTO to React (Modern File Explorer)

This document outlines the roadmap to migrate the AURA-PROTO frontend from Streamlit to a React-based Single Page Application (SPA) with a Windows Explorer/Google Drive-style interface.

## 🎯 Objectives
- **Modern Stack:** Vite + React + TypeScript + Tailwind CSS.
- **UX Goal:** Hierarchical, navigable tree view, drag-and-drop organization, context menus, and split views (Sidebar Tree + Main Grid/List).
- **Performance:** Client-side routing, optimistic UI updates, and efficient data fetching.

---

## 📅 Phase 1: Backend Preparation (FastAPI)
*Goal: Enable the API to serve a frontend app and support file-system-like operations.*

### 1.1 Network & Access
- **CORS Configuration:** Allow requests from `localhost:5173` (Vite default).
- **Static File Serving:** Mount the local `pdfs/` directory to `/static/pdfs` so the frontend can preview/download generated notes.

### 1.2 "Explorer" API Endpoints
To support a fast tree view, we need endpoints that view data as "nodes" rather than strictly relational tables.

- **`GET /api/explorer/tree`:**
    - Returns a nested JSON structure (or level-by-level) of the entire hierarchy.
    - Standardized format: `{ id, type, label, children: [], ... }`.
- **Unified Move Logic:**
    - Ensure `PUT` endpoints for all entities (Dept, Sem, Subj, Module) accept a `parent_id` to allow dragging items to new parents.

### 1.3 Streaming & Async
- **WebSockets / SSE:** (Optional for V1) Implement real-time status updates for "Transcribing..." and "Summarizing..." so the UI doesn't need to poll aggressively.

---

## ⚛️ Phase 2: Frontend Architecture (React)
*Goal: Initialize the codebase with a focus on atomic design and strict typing.*

### 2.1 Scaffolding
- **Build Tool:** Vite (`npm create vite@latest`).
- **Language:** TypeScript.
- **Styling:** Tailwind CSS + `clsx` + `tailwind-merge`.
- **Icons:** `lucide-react` (clean, modern icons matching the Windows 11/Mac style).

### 2.2 Core Dependencies
- **State Management:** `zustand` (Global UI state: selections, view mode, clipboard).
- **Data Fetching:** `@tanstack/react-query` (Caching, auto-refetching, optimistic updates).
- **Drag & Drop:** `@dnd-kit/core` (Robust, accessible drag-and-drop primitives).
- **UI Components:** `shadcn/ui` (Radix UI + Tailwind) for robust, accessible primitives (Context Menus, Dialogs, Dropdowns).

### 2.3 Directory Structure
```text
/frontend
├── src
│   ├── api           # Axios instances & API definition
│   ├── components
│   │   ├── explorer  # FileRow, GridItem, SidebarTree
│   │   ├── ui        # Generic primitives (Button, Input)
│   │   └── layout    # MainLayout (Sidebar + Content)
│   ├── hooks         # Custom hooks (useContextMenu, useSelection)
│   ├── stores        # Zustand stores (useExplorerStore)
│   └── types         # TypeScript interfaces (FileSystemNode)
```

---

## 🖥️ Phase 3: The "Explorer" Interface
*Goal: Implement the specific UI features requested.*

### 3.1 Layout
- **Sidebar:** A recursive "Tree" component showing the folder structure.
- **Breadcrumb Bar:** "Home > Computer Science > Sem 1".
- **Main View:** Toggleable **Grid** (large icons) and **List** (details table) views.

### 3.2 Interactions
- **Selection:** Click to select, Ctrl+Click for multi-select, Shift+Click for range.
- **Context Menus:** Right-click handlers:
    - *Folder:* Open, Rename, Delete, New Sub-item.
    - *Note:* Download, Rename, Delete, Open PDF.
- **Drag & Drop:**
    - Drag items into folders in the main view.
    - Drag items into the sidebar tree.
    - *Logic Constraint:* Prevent illegal moves (e.g., can't drop a Semester into a Module).

### 3.3 Operations
- **Create:** Modal dialogs for "New Department", "New Semester", etc.
- **Search:** Client-side filtering of the currently viewed folder.

---

## 🔄 Phase 4: Migration & Integration
*Goal: Switch over safely.*

1.  **Dual Run:** Run Streamlit (port 8501) and React (port 5173) simultaneously against the same API/DB.
2.  **Verify:** Perform operations in React, check results in Streamlit.
3.  **Build:** Run `npm run build` to generate static assets.
4.  **Serve:** Update `api/main.py` to serve the React `index.html` at the root URL.

---

## 🛠️ Technical Decisions (Q&A)

**Q: How do we handle authentication?**
A: Deferred. For now, the app will assume an internal/trusted environment or use a simple hardcoded header if needed.

**Q: How do we handle large PDF generation times?**
A: The React UI will show a "Processing" state (placeholder file) using optimistic updates, while the background task runs.
