# AURA-PROTO

A simplified hierarchy and note management prototype with React frontend and FastAPI backend.

## Architecture
- **Backend**: FastAPI (Python) running on port 8000
- **Frontend**: React + Vite + TypeScript running on port 5173
- **Database**: SQLite (managed via internal scripts)
- **Services**: Deepgram (STT), OpenAI/Gemini (Refinement - placeholder)

## Prerequisites
- Python 3.9+
- Node.js 16+
- Deepgram API Key (get from https://console.deepgram.com/)

## Installation & Setup

### 1. Backend Setup
```bash
# Crate virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install deepgram-sdk python-multipart
```

**Environment Variables:**
Create a `.env` file in the root directory:
```
DEEPGRAM_API_KEY=your_deepgram_key_here
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend
Open a terminal in the project root:
```bash
cd api
# Make sure venv is activated if not activate it
.venv\Scripts\activate
#Then run the below command to start the backend

python -m uvicorn main:app --reload --port 8000
```
API runs at: http://localhost:8000

### Start the Frontend
Open a new terminal in the `frontend` folder:
```bash
cd frontend
npm run dev
```
Frontend runs at: http://localhost:5173

## Features
- **Explorer**: Navigate hierarchies (Computer Science > Semester > Subject > Module)
- **Document Upload**: Upload PDF, Doc, Txt files to specific modules.
- **Audio to Notes**: Upload voice recordings, transcribing them via Deepgram to generate notes.
