# AURA-PROTO

A simplified hierarchy and note management prototype with React frontend and FastAPI backend.

## Architecture
- **Backend**: FastAPI (Python) running on port 8000
- **Frontend**: React + Vite + TypeScript running on port 5173
- **Database**: Firebase Firestore (Cloud NoSQL)
- **Services**: Deepgram (STT), OpenAI/Gemini (Refinement - placeholder)

## Prerequisites
- Python 3.9+
- Node.js 16+
- Firebase Project with Firestore enabled
- Deepgram API Key (get from https://console.deepgram.com/)

## Installation & Setup

### 1. Firebase Setup
1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Firestore in the Firebase Console
3. Generate a service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - **IMPORTANT:** Save the key locally (e.g., `serviceAccountKey-local.json`) and add it to `.gitignore`. **Never commit service account keys to the repository.**

### 2. Backend Setup
```bash
# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

**Environment Variables:**
Create a `.env` file in the root directory:
```
DEEPGRAM_API_KEY=your_deepgram_key_here
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey-local.json
```
**Security:** Never commit `.env` or credential files to git. The repository uses gitleaks CI to prevent secret leaks.

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Deploy Firestore Rules
```bash
firebase login
firebase use <your-project-id>
firebase deploy --only firestore:rules,firestore:indexes
```

## Running the Application

### Start the Backend
```bash
cd api
python -m uvicorn main:app --reload --port 8000
```
API runs at: http://localhost:8000

### Start the Frontend
```bash
cd frontend
npm run dev
```
Frontend runs at: http://localhost:5173

## Authentication

The application uses a mock authentication system for local development.

### Test Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@test.com | Admin123! |
| Staff | staff@test.com | Staff123! |
| Student | student@test.com | Student123! |

### Role Permissions

- **Admin**: Full access to user management, can view all departments
- **Staff**: Can upload notes to assigned department only
- **Student**: Read-only access to assigned department's notes

### Environment Configuration

Set `USE_REAL_FIREBASE=false` in `.env` for mock authentication (default).
Set `USE_REAL_FIREBASE=true` to use real Firebase Authentication.

## E2E Testing

Comprehensive end-to-end tests using Playwright are located in `frontend/e2e/`.

### Quick Start
```bash
cd frontend
npm install
npx playwright install --with-deps
npm run test:e2e
```

### Test Suites
- **API Tests**: Full backend CRUD, hierarchy, and operations coverage
- **UI Tests**: Frontend navigation, CRUD, search, and interactions
- **Audio Tests**: Complete audio processing pipeline (transcription → AI → PDF)

### Running Specific Tests
```bash
cd frontend
npm run test:e2e         # All E2E tests
npm run test:e2e:ui      # Run with Playwright UI
npm run test:e2e:headed  # Run with visible browser
npx playwright test tests/explorer.spec.ts  # Specific test
```

### Test Documentation
See `frontend/e2e/` for test implementation. The root `e2e/` directory is deprecated.

## Features
- **Explorer**: Navigate hierarchies (Computer Science > Semester > Subject > Module)
- **Document Upload**: Upload PDF, Doc, Txt files to specific modules.
- **Audio to Notes**: Upload voice recordings, transcribing them via Deepgram to generate notes.

## Project Structure
```
AURA-PROTO/
├── api/               # FastAPI backend
├── frontend/          # React frontend
│   └── e2e/          # Playwright E2E tests (canonical location)
├── e2e/               # DEPRECATED - retained as tombstone only
├── pdfs/              # Generated PDF files
├── services/          # Backend services (STT, PDF generation)
├── firestore.rules    # Firestore security rules
├── firestore.indexes.json # Firestore indexes
└── .env              # Environment variables (never commit credentials)
```
