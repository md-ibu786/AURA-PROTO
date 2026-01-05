# AURA-PROTO Architecture Specification
## Complete System Blueprint for Canva Diagram Creation

---

## 1. High-Level Overview

### What the System Does (Business Value)
AURA-PROTO is a **Hierarchy and Note Management System** that helps educational institutions and students organize course materials in a structured, hierarchical manner. The system provides two key value propositions:

1. **Document Organization**: Store and manage educational documents (PDFs, Word files, text files) within a logical hierarchy: Departments → Semesters → Subjects → Modules → Notes
2. **AI-Powered Note Generation**: Transform voice recordings into structured, university-grade notes through an automated pipeline that transcribes audio, refines the content, and generates professional PDF documents

### User Journey Summary
1. **Navigate**: Users browse through the organizational hierarchy (e.g., Computer Science → Semester 1 → Data Structures → Module 1)
2. **Upload**: Users can either upload existing documents or record voice lectures
3. **Process**: Voice recordings go through AI pipeline: Audio → Transcription → Refinement → Summarization → PDF
4. **Access**: Generated notes and documents are stored and accessible within the hierarchy

### Technology Stack Summary
- **Frontend**: React 18 + TypeScript + Vite (Port 5173)
- **Backend**: FastAPI (Python) + Uvicorn (Port 8000)
- **Database**: Firebase Firestore (Cloud NoSQL)
- **External Services**: Deepgram (Speech-to-Text), Google Cloud/Firebase (Auth & Storage), Google Gemini (AI Processing)
- **File Storage**: Local filesystem (pdfs/ directory) served via FastAPI static files
- **Testing**: Playwright E2E tests

---

## 2. System Components (Layer by Layer)

### Presentation Layer (Frontend)

#### React Application Structure
**Main Entry Point**: `frontend/src/main.tsx`
- Bootstraps React application
- Sets up React Query for state management
- Renders the main App component

**App Component**: `frontend/src/App.tsx`
- Simple router setup with React Router
- Routes all traffic to ExplorerPage

**ExplorerPage**: `frontend/src/pages/ExplorerPage.tsx`
- **Purpose**: Main application container that orchestrates the entire UI
- **Key Functions**:
  - Fetches complete hierarchy tree from backend
  - Manages navigation state (current path, view mode)
  - Renders Sidebar and main content area
  - Handles delete confirmations
  - Manages context menus

**Key UI Components**:

1. **Sidebar** (`frontend/src/components/layout/Sidebar.tsx`)
   - **Purpose**: Navigation tree and contextual actions
   - **Features**:
     - Displays hierarchical tree structure
     - Dynamic "Create" button based on current depth
     - Upload dialog trigger at module level
   - **Non-Technical Description**: Like a file explorer sidebar, but for educational content. Shows folders (Departments, Semesters, etc.) and allows navigation.

2. **SidebarTree** (`frontend/src/components/explorer/SidebarTree.tsx`)
   - **Purpose**: Recursive tree renderer
   - **Features**: Expandable/collapsible nodes with icons, visual hierarchy indicators
   - **Non-Technical Description**: The actual tree view that shows nested folders with proper indentation

3. **Header** (`frontend/src/components/layout/Header.tsx`)
   - **Purpose**: Top navigation bar with breadcrumbs and view controls
   - **Features**: Path display, view mode toggle (Grid/List)

4. **GridView / ListView** (`frontend/src/components/explorer/`)
   - **Purpose**: Display children of current folder
   - **Features**: Visual cards (Grid) or detailed rows (List) showing notes and subfolders

5. **UploadDialog** (`frontend/src/components/explorer/UploadDialog.tsx`)
   - **Purpose**: Handles all file uploads and AI processing
   - **Features**:
     - Two modes: Document upload vs Voice recording
     - Drag-and-drop support
     - Real-time progress polling for AI pipeline
     - Status display with progress bars
   - **Non-Technical Description**: A popup dialog that lets users either upload existing files or record voice to generate AI notes

6. **ContextMenu** (`frontend/src/components/explorer/ContextMenu.tsx`)
   - **Purpose**: Right-click actions for nodes
   - **Features**: Create, rename, move, delete operations

7. **ConfirmDialog** (`frontend/src/components/ui/ConfirmDialog.tsx`)
   - **Purpose**: Delete confirmation with safety check

**State Management**:
- **Zustand Store**: Manages UI state (navigation, dialogs, selection)
- **React Query**: Manages server state (data fetching, caching, invalidation)

**API Client** (`frontend/src/api/`):
- Functions for all backend endpoints
- Type-safe with TypeScript interfaces

---

### Application Layer (Backend)

#### FastAPI Server Structure
**Main Entry Point**: `api/main.py`
- **Purpose**: Application entry, middleware setup, routing
- **Key Functions**:
  - Initializes FastAPI app with CORS for React frontend
  - Includes routers for different functionality areas
  - Mounts static file server for PDFs
  - Health/readiness endpoints
  - Rate limiting configuration

**API Routers**:

1. **Hierarchy Router** (`api/hierarchy.py`)
   - **Purpose**: Read-only navigation queries
   - **Endpoints**:
     - `GET /departments` - List all departments
     - `GET /departments/{id}/semesters` - Get semesters under department
     - `GET /semesters/{id}/subjects` - Get subjects under semester
     - `GET /subjects/{id}/modules` - Get modules under subject
   - **Non-Technical Description**: These endpoints provide the "folder structure" data for navigation

2. **CRUD Router** (`api/hierarchy_crud.py`)
   - **Purpose**: Create, update, delete operations for hierarchy
   - **Endpoints**:
     - `POST /api/departments` - Create department
     - `PUT /api/departments/{id}` - Update department
     - `DELETE /api/departments/{id}` - Delete department (recursive)
     - Similar endpoints for semesters, subjects, modules, notes
   - **Features**: Auto-generates sequential numbers, validates hierarchy, handles file cleanup
   - **Non-Technical Description**: Allows users to create and manage the organizational structure

3. **Explorer Router** (`api/explorer.py`)
   - **Purpose**: Advanced navigation and tree building
   - **Endpoints**:
     - `GET /api/explorer/tree` - Get full hierarchy tree (async, parallel fetching)
     - `GET /api/explorer/children/{type}/{id}` - Lazy-load children
     - `POST /api/explorer/move` - Move nodes between parents
   - **Features**: Async operations, parallel fetching for performance
   - **Non-Technical Description**: Powers the tree view with efficient data loading

4. **Audio Processing Router** (`api/audio_processing.py`)
   - **Purpose**: All file and audio processing operations
   - **Endpoints**:
     - `POST /api/audio/upload-document` - Upload PDF/Doc/Txt files
     - `POST /api/audio/transcribe` - Transcribe audio (Deepgram)
     - `POST /api/audio/refine` - Clean transcript (AI)
     - `POST /api/audio/summarize` - Generate notes (AI)
     - `POST /api/audio/generate-pdf` - Create PDF from notes
     - `POST /api/audio/process-pipeline` - Full end-to-end processing
     - `GET /api/audio/pipeline-status/{job_id}` - Check processing status
   - **Features**: Background tasks, progress tracking, file size validation
   - **Non-Technical Description**: The "magic" that turns voice recordings into PDF notes

**Supporting Modules**:

- **Config** (`api/config.py`): Firebase initialization and Firestore client setup
- **Notes** (`api/notes.py`): Helper for creating note records in database

---

### Data Layer

#### Firestore Database Structure
**Database**: Firebase Firestore (NoSQL document database)

**Collections Structure**:

```
departments (root collection)
├── department_id (document)
│   ├── name: string
│   ├── code: string
│   ├── id: string
│   └── semesters (subcollection)
│       ├── semester_id (document)
│       │   ├── name: string
│       │   ├── semester_number: int
│       │   ├── department_id: string
│       │   ├── id: string
│       │   └── subjects (subcollection)
│       │       ├── subject_id (document)
│       │       │   ├── name: string
│       │       │   ├── code: string
│       │       │   ├── semester_id: string
│       │       │   ├── id: string
│       │       │   └── modules (subcollection)
│       │       │       ├── module_id (document)
│       │       │       │   ├── name: string
│       │       │       │   ├── module_number: int
│       │       │       │   ├── subject_id: string
│       │       │       │   ├── id: string
│       │       │       │   └── notes (subcollection)
│       │       │       │       ├── note_id (document)
│       │       │       │       │   ├── title: string
│       │       │       │       │   ├── pdf_url: string
│       │       │       │       │   ├── created_at: timestamp
│       │       │       │       │   ├── module_id: string
│       │       │       │       │   └── id: string
```

**Data Relationships**:
- **Parent-Child**: Each level stores reference to its parent ID
- **Subcollections**: Used for hierarchical nesting (semesters under departments, etc.)
- **Collection Group Queries**: Used to find documents by ID across all levels

**Non-Technical Description**: Think of this as a nested filing cabinet system where each drawer (department) contains folders (semesters), which contain subfolders (subjects), which contain dividers (modules), which contain actual documents (notes).

---

### External Services Layer

#### 1. Deepgram (Speech-to-Text)
**Service**: `services/stt.py`
- **Purpose**: Convert audio files to text transcripts
- **Integration**: Deepgram SDK v5.x
- **Configuration**: Requires `DEEPGRAM_API_KEY` environment variable
- **Features**: Uses Nova-3 model, smart formatting, diarization
- **Non-Technical Description**: Like a highly accurate transcription service that listens to voice recordings and converts them to written text

#### 2. Google Gemini (AI Processing)
**Services**:
- `services/vertex_ai_client.py` - Client wrapper
- `services/coc.py` - Content cleaning/refinement
- `services/summarizer.py` - Note generation

**Purpose**: Two-stage AI processing
1. **Refinement** (`coc.py`): Cleans raw transcript by removing noise, fixing grammar, ensuring topic relevance
2. **Summarization** (`summarizer.py`): Transforms cleaned transcript into structured university-grade notes

**Features**:
- Strict academic formatting
- Topic adherence enforcement
- Noise filtering (student questions, administrative chatter)
- Structured output with headers, definitions, examples

**Non-Technical Description**: An AI editor that takes raw transcribed text and transforms it into professional, well-organized lecture notes

#### 3. Firebase Services
**Services**:
- **Firestore**: Database (already covered)
- **Authentication**: (Configured but not implemented in current version - public read access)
- **Storage**: File storage (configured for future use)

**Security Rules** (`firestore.rules`):
- Public read access for hierarchy browsing
- Authenticated users can create/update/delete
- Hierarchical validation rules
- Non-Technical Description: Security guard that controls who can view vs. modify data

#### 4. PDF Generation
**Service**: `services/pdf_generator.py`
- **Purpose**: Convert text notes into PDF documents
- **Library**: fpdf2
- **Features**:
  - Markdown formatting support
  - Headers, bullet points, bold text
  - Professional layout
- **Non-Technical Description**: Like a word processor that automatically formats text into a clean, printable document

---

## 3. Data Flow Diagrams

### User Flow 1: Document Upload

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT UPLOAD FLOW                         │
└─────────────────────────────────────────────────────────────────────┘

User Action: Click "Upload Notes" → Select "Upload Document"

1. Frontend (UploadDialog)
   ├─ User selects file (PDF/Doc/Txt)
   ├─ User enters optional title
   └─ POST /api/audio/upload-document
       ├─ file: binary
       ├─ title: string
       └─ moduleId: string

2. Backend (audio_processing.py:upload_document)
   ├─ Validate file type (.pdf, .doc, .docx, .txt, .md)
   ├─ Validate file size (max 50MB)
   ├─ Generate unique filename with timestamp
   ├─ Save to: pdfs/{safe_title}_{timestamp}{ext}
   ├─ Create URL: /pdfs/{filename}
   └─ Call: create_note_record(moduleId, title, pdf_url)

3. Database (notes.py:create_note_record)
   ├─ Find module by ID (collection group query)
   ├─ Create document in: departments/{dept}/semesters/{sem}/subjects/{subj}/modules/{mod}/notes
   ├─ Fields: id, title, pdf_url, created_at, module_id
   └─ Return note data

4. Response to Frontend
   ├─ success: true
   ├─ noteId: generated_id
   ├─ documentUrl: /pdfs/{filename}
   └─ message: "Document uploaded successfully"

5. Frontend
   ├─ Refresh React Query cache
   ├─ Show success message
   └─ User sees new note in hierarchy

File Location: pdfs/{filename} (local filesystem)
Database Entry: Firestore notes subcollection
```

### User Flow 2: Audio Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI AUDIO PROCESSING PIPELINE                      │
└─────────────────────────────────────────────────────────────────────┘

User Action: Click "Upload Notes" → Select "AI Note Generator"

1. Frontend (UploadDialog)
   ├─ User selects audio file (.mp3, .wav, .m4a, etc.)
   ├─ User enters topic (e.g., "Data Structures - Arrays")
   ├─ POST /api/audio/process-pipeline
   │   ├─ file: audio_binary
   │   ├─ topic: string
   │   └─ moduleId: string
   └─ Returns: jobId (for polling)

2. Backend (audio_processing.py:process-pipeline)
   ├─ Create job_id (UUID)
   ├─ Store initial status: pending, 0% progress
   ├─ Start background task: _run_pipeline()
   └─ Return immediately: {jobId, status}

3. Background Task - Step 1: Transcription (10%)
   ├─ Call: services/stt.py:process_audio_file()
   ├─ Deepgram API: Transcribe audio → Raw transcript
   └─ Update status: transcribing, 10%

4. Background Task - Step 2: Refinement (35%)
   ├─ Call: services/coc.py:transform_transcript()
   ├─ Gemini AI: Clean transcript (remove noise, fix grammar)
   ├─ Prompt: "You are an Elite Academic Editor..."
   └─ Update status: refining, 35%

5. Background Task - Step 3: Summarization (60%)
   ├─ Call: services/summarizer.py:generate_university_notes()
   ├─ Gemini AI: Create structured notes
   ├─ Output: Markdown formatted with headers, definitions, examples
   └─ Update status: summarizing, 60%

6. Background Task - Step 4: PDF Generation (85%)
   ├─ Call: services/pdf_generator.py:create_pdf()
   ├─ Generate PDF from notes
   ├─ Save to: pdfs/{topic}_{timestamp}.pdf
   ├─ Create URL: /pdfs/{filename}
   └─ Update status: generating_pdf, 85%

7. Background Task - Step 5: Database Storage (100%)
   ├─ Call: notes.py:create_note_record()
   ├─ Save to Firestore: notes subcollection
   ├─ Store: title, pdf_url, created_at
   └─ Update status: complete, 100%

8. Frontend Polling
   ├─ GET /api/audio/pipeline-status/{jobId} (every 2 seconds)
   ├─ Display progress bar with status message
   └─ On complete: Show "View PDF" button

File Locations:
- Audio: Memory (processed in background)
- PDF: pdfs/{topic}_{timestamp}.pdf
- Database: Firestore notes subcollection
```

### User Flow 3: Hierarchy Navigation

```
┌─────────────────────────────────────────────────────────────────────┐
│                      HIERARCHY NAVIGATION FLOW                       │
└─────────────────────────────────────────────────────────────────────┘

User Action: Browse through organizational structure

1. Initial Page Load
   ├─ Frontend: ExplorerPage mounts
   ├─ GET /api/explorer/tree?depth=5
   └─ Backend: explorer.py:get_explorer_tree()
       ├─ Fetch all departments
       ├─ Parallel async fetch of children (depth 5)
       ├─ Build tree structure with metadata
       └─ Return: Array of ExplorerNode objects

2. User Clicks Department
   ├─ Frontend: Updates currentPath state
   ├─ If not expanded: GET /api/explorer/children/department/{id}
   ├─ Backend: Returns semesters (lazy load)
   └─ UI: Sidebar expands, main view shows semesters

3. User Clicks Semester
   ├─ Frontend: Updates currentPath
   ├─ If not expanded: GET /api/explorer/children/semester/{id}
   ├─ Backend: Returns subjects
   └─ UI: Navigation continues

4. User Clicks Subject
   ├─ Frontend: Updates currentPath
   ├─ If not expanded: GET /api/explorer/children/subject/{id}
   ├─ Backend: Returns modules with note counts
   └─ UI: Shows modules

5. User Clicks Module
   ├─ Frontend: Updates currentPath
   ├─ If expanded: GET /api/explorer/children/module/{id}
   ├─ Backend: Returns notes with PDF metadata
   └─ UI: Shows list of notes (with "View PDF" links)

6. Upload Button Visibility
   ├─ Path depth = 4 AND type = 'module'
   ├─ Show "Upload Notes" button
   └─ Opens UploadDialog

Data Structure Flow:
ExplorerNode {
  id: string
  type: 'department' | 'semester' | 'subject' | 'module' | 'note'
  label: string
  parentId: string | null
  children: ExplorerNode[] | null
  meta: {
    hasChildren: boolean
    noteCount?: number
    code?: string
    ordering?: number
  }
}
```

---

## 4. Security & Authentication

### Firebase Security Rules

**File**: `firestore.rules`

**Access Control Strategy**:
- **Public Read**: All hierarchy data is readable by anyone (for browsing)
- **Authenticated Write**: Only authenticated users can create/update/delete
- **Hierarchical Validation**: Ensures data integrity

**Rule Structure**:
```
match /departments/{departmentId} {
  allow read: if true;                    // Public can view
  allow create: if isAuthenticated();     // Auth required
  allow update: if isAuthenticated();
  allow delete: if isAuthenticated();

  match /semesters/{semesterId} {
    allow read: if true;
    allow create: if isAuthenticated();
    // ... nested rules continue
  }
}
```

**Non-Technical Description**: Like a library where anyone can browse the catalog, but only staff can add/remove books.

### API Authentication
**Current Implementation**:
- No user authentication required
- All endpoints are open
- Rate limiting enabled via SlowAPI

**Future Enhancement**:
- Firebase Authentication for user management
- JWT token validation on API endpoints
- User-specific data isolation

### File Access Controls
**File Storage**: Local filesystem (`pdfs/` directory)
- Served via FastAPI static files at `/pdfs/`
- No authentication on file URLs
- Filenames are sanitized and timestamped for uniqueness

**Security Considerations**:
- ✅ Files are stored outside web root
- ✅ Filename sanitization prevents path traversal
- ⚠️ No access control on PDF URLs
- ⚠️ Files persist indefinitely (no cleanup)

---

## 5. Technical Architecture Details

### Port Configurations
```
Frontend:  http://localhost:5173  (Vite dev server)
Backend:   http://localhost:8000  (FastAPI + Uvicorn)
PDFs:      http://localhost:8000/pdfs/{filename}  (Static files)
```

### Environment Variables

**Backend (.env)**:
```
DEEPGRAM_API_KEY=your_deepgram_key_here
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
```

**Frontend**: No environment variables (all API calls to localhost)

### Dependencies

**Backend (requirements.txt)**:
```
fastapi==0.115.0          # Web framework
uvicorn[standard]==0.32.0 # ASGI server
firebase-admin            # Firebase SDK
google-cloud-firestore    # Firestore client
deepgram-sdk              # Speech-to-Text
google-generativeai       # Gemini AI
python-dotenv==1.0.0      # Environment management
python-multipart          # File uploads
slowapi                   # Rate limiting
fpdf2                     # PDF generation
```

**Frontend (package.json)**:
```
react@18.3.1              # UI framework
react-router-dom@7.1.0    # Routing
@tanstack/react-query@5.62.0  # Server state
zustand@5.0.2             # Client state
lucide-react@0.468.0      # Icons
vite@6.0.5                # Build tool
typescript@5.6.2          # Type safety
```

### File System Structure
```
AURA-PROTO/
├── api/                    # Backend
│   ├── main.py            # Entry point
│   ├── config.py          # Firebase setup
│   ├── hierarchy.py       # Navigation queries
│   ├── hierarchy_crud.py  # CRUD operations
│   ├── explorer.py        # Tree building
│   ├── audio_processing.py# Upload & pipeline
│   └── notes.py           # Note helpers
├── frontend/              # Frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/         # Route components
│   │   ├── components/    # UI components
│   │   ├── api/           # API client
│   │   └── stores/        # State management
│   └── package.json
├── services/              # AI & Processing
│   ├── stt.py            # Deepgram transcription
│   ├── coc.py            # Transcript refinement
│   ├── summarizer.py     # Note generation
│   ├── pdf_generator.py  # PDF creation
│   └── vertex_ai_client.py # AI client
├── pdfs/                  # Generated PDFs
├── e2e/                   # Playwright tests
├── firestore.rules        # Database security
├── firebase.json          # Firebase config
└── serviceAccountKey.json # Firebase credentials
```

---

## 6. Canva Diagram Blueprint

### Box Layout Suggestions

**Canvas Layout (Top to Bottom, Left to Right)**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER (Browser)                                                     │
│  [Human Icon]                                                       │
└─────────────────────────────────────────────────────────────────────┘
         ↓ (HTTP Requests)
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (Frontend) - Port 5173                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  React Application                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │  Sidebar     │  │  Header      │  │  Main Content    │  │  │
│  │  │  (Tree Nav)  │  │  (Breadcrumbs)│  │  (Grid/List)     │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │
│  │                                                               │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Upload Dialog (Modal)                                │  │  │
│  │  │  - Document Upload                                    │  │  │
│  │  │  - Voice Recording → AI Pipeline                      │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         ↓ (REST API / JSON)
┌─────────────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER (Backend) - Port 8000                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Server                                              │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │  Hierarchy   │  │  CRUD        │  │  Explorer       │  │  │
│  │  │  (Read)      │  │  (Modify)    │  │  (Tree Build)   │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │  │
│  │                                                               │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Audio Processing Router                              │  │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │  │  │
│  │  │  │  Upload      │  │  Transcribe  │  │  Pipeline   │ │  │  │
│  │  │  │  Document    │  │  (Deepgram)  │  │  (Background)│ │  │  │
│  │  │  └──────────────┘  └──────────────┘  └─────────────┘ │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         ↓ (Service Calls)
┌─────────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICES LAYER                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Deepgram API    │  │  Google Gemini   │  │  Firebase       │  │
│  │  (Speech-to-Text)│  │  (AI Processing) │  │  (Firestore)    │  │
│  │                  │  │                  │  │                 │  │
│  │  Audio → Text    │  │  Refine → Notes  │  │  Database       │  │
│  │  $0.006/min      │  │  Token-based     │  │  NoSQL Docs     │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                    │
│  ┌──────────────────┐                                             │
│  │  PDF Generator   │                                             │
│  │  (fpdf2 Library) │                                             │
│  │  Text → PDF      │                                             │
│  └──────────────────┘                                             │
└─────────────────────────────────────────────────────────────────────┘
         ↓ (File Storage)
┌─────────────────────────────────────────────────────────────────────┐
│  STORAGE LAYER                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Filesystem: pdfs/ directory                                  │  │
│  │  - Generated PDFs                                             │  │
│  │  - Uploaded documents                                         │  │
│  │  - Served via FastAPI static files                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Color Coding

**Suggested Colors for Canva**:

| Layer | Color | Hex Code | Usage |
|-------|-------|----------|-------|
| **User** | Blue | `#3B82F6` | Human/user icon |
| **Frontend** | Green | `#10B981` | React components, UI |
| **Backend** | Purple | `#8B5CF6` | API routes, business logic |
| **External Services** | Orange | `#F59E0B` | Deepgram, Gemini, Firebase |
| **Storage** | Gray | `#6B7280` | Filesystem, Database |
| **Data Flow** | Black | `#000000` | Arrows/connections |
| **Background** | Light | `#F9FAFB` | Canvas background |

### Connector Types

**Visual Guidelines**:

1. **Solid Lines (───►)**: Primary data flow
   - User → Frontend
   - Frontend → Backend
   - Backend → External Services
   - Backend → Storage

2. **Dashed Lines (---►)**: Secondary/optional flows
   - Frontend polling for status
   - Background task processing
   - Database validation checks

3. **Dotted Lines (···►)**: Dependency/configuration
   - Environment variables
   - API keys
   - Service credentials

4. **Bidirectional Arrows (◄──►)**: Two-way communication
   - Frontend ↔ Backend (REST API)
   - Backend ↔ External Services

### Labels

**Exact Text for Boxes**:

**User Layer**:
- Box: "User (Browser)"
- Subtext: "HTTP Requests, File Uploads"

**Frontend Layer**:
- Main Box: "React Frontend"
- Sub-box 1: "Sidebar Navigation"
- Sub-box 2: "Header & Breadcrumbs"
- Sub-box 3: "Content View (Grid/List)"
- Sub-box 4: "Upload Dialog"
- Port Label: "Port 5173"

**Backend Layer**:
- Main Box: "FastAPI Backend"
- Sub-box 1: "Hierarchy API (Read)"
- Sub-box 2: "CRUD API (Modify)"
- Sub-box 3: "Explorer API (Tree)"
- Sub-box 4: "Audio Processing"
- Port Label: "Port 8000"

**External Services**:
- Box 1: "Deepgram API" + "Speech-to-Text"
- Box 2: "Google Gemini" + "AI Processing"
- Box 3: "Firebase Firestore" + "Database"
- Box 4: "PDF Generator" + "fpdf2"

**Storage**:
- Box: "File System"
- Subtext: "pdfs/ directory"
- Box: "Firestore"
- Subtext: "NoSQL Collections"

### Legend

**Component Types**:

```
┌─────────────────────────────────────────┐
│ LEGEND                                 │
├─────────────────────────────────────────┤
│ [Human Icon]  →  User/Actor            │
│ [React Icon]  →  Frontend Component    │
│ [Server Icon] →  Backend API           │
│ [Cloud Icon]  →  External Service      │
│ [Database]    →  Data Storage          │
│ [File Box]    →  File Storage          │
└─────────────────────────────────────────┘

Connection Types:
━━━━►  Primary Data Flow
───►   Secondary Flow
···►   Dependency/Config
◄──►   Two-way Communication

Color Coding:
Blue    = User Interaction
Green   = Frontend Layer
Purple  = Backend Layer
Orange  = External Services
Gray    = Storage Layer
```

**Flow Numbering** (for step-by-step diagrams):

```
1. User Action → 2. Frontend → 3. Backend → 4. External Service → 5. Storage
```

---

## 7. Complete Data Flow Examples

### Example 1: Voice Recording to PDF Notes

**Visual Flow**:
```
User Recording
     ↓ [1. Upload Audio + Topic]
Upload Dialog
     ↓ [2. POST /api/audio/process-pipeline]
FastAPI Router
     ↓ [3. Background Task Starts]
     ├─→ [4. Deepgram API] ← Audio Bytes
     │     ↓ Transcribed Text
     ├─→ [5. Gemini AI #1] ← Refinement Prompt
     │     ↓ Cleaned Text
     ├─→ [6. Gemini AI #2] ← Summarization Prompt
     │     ↓ Structured Notes
     ├─→ [7. PDF Generator] ← Notes Text
     │     ↓ PDF File
     └─→ [8. Firestore] ← Note Metadata
           ↓
     [9. Frontend Polling] ← Job Status
           ↓
     [10. User Sees Progress] → [11. View PDF]
```

### Example 2: Creating New Hierarchy

```
User Clicks "New Department"
     ↓
Sidebar prompts for name/code
     ↓
POST /api/departments
     ↓
Backend validates input
     ↓
Firestore: Create document
     ├─ departments/{id}
     │   ├─ name: "Computer Science"
     │   ├─ code: "CS"
     │   └─ id: auto-generated
     ↓
React Query invalidates cache
     ↓
Sidebar refreshes to show new department
```

---

## 8. Key Technical Concepts Explained

### Firestore Subcollections
**Analogy**: Like nested folders in a file system
- Each "folder" (department) can contain sub-folders (semesters)
- Sub-folders can contain their own sub-folders (subjects → modules → notes)
- You navigate by knowing the full path

### Collection Group Queries
**Problem**: How to find a document when you only know its ID, not its full path?
**Solution**: Query all collections with the same name across the entire database
**Example**: Find any "module" document with ID "abc123" regardless of which subject it belongs to

### Async/Await in Python
**Purpose**: Handle operations that take time (database queries, API calls) without blocking
**In This App**: Used heavily in `explorer.py` to fetch multiple hierarchy levels in parallel

### React Query
**Purpose**: Manage server state (data from API) automatically
**Benefits**:
- Caching (don't fetch same data twice)
- Auto-refetch on focus
- Background updates
- Error handling

### Zustand
**Purpose**: Manage client state (UI state, navigation)
**In This App**: Tracks current path, expanded tree nodes, dialog states

---

## 9. Success Metrics & Monitoring

### What to Monitor
1. **API Response Times**: Should be < 500ms for hierarchy queries
2. **Audio Processing**: Pipeline should complete in 30-60 seconds
3. **File Uploads**: Should handle files up to 50MB (documents) / 100MB (audio)
4. **Database Reads**: Minimize collection group queries for performance

### Health Checks
- `GET /health` - Is the server running?
- `GET /ready` - Is Firebase connected?

---

## 10. Summary for Canva Creation

**For the Designer**:

1. **Start with User**: Place user icon at top center
2. **Three Main Layers**: Stack Frontend (green), Backend (purple), External Services (orange)
3. **Left-to-Right Flow**: Data flows top-to-bottom, services flow left-to-right
4. **Use Icons**: React logo for frontend, Python/FastAPI for backend, cloud icons for services
5. **Highlight Key Features**:
   - AI Pipeline (show 4-step process)
   - Hierarchy Navigation (show depth)
   - Two Upload Types (Document vs Voice)
6. **Keep it Clean**: Don't overcrowd - use separate diagrams for complex flows if needed
7. **Add Legend**: Include color coding and connector types
8. **Non-Technical Labels**: Use plain English (e.g., "AI Note Generator" instead of "Gemini Integration")

**Key Diagram Elements**:
- ✅ User at top
- ✅ Three distinct layers
- ✅ Clear data flow arrows
- ✅ External services on right
- ✅ Storage at bottom
- ✅ Color-coded components
- ✅ Legend for symbols
- ✅ Port numbers visible
- ✅ File paths shown

---

**End of Specification**
This document provides everything needed to create a comprehensive, professional architecture diagram in Canva that accurately represents the AURA-PROTO system for both technical and non-technical stakeholders.
