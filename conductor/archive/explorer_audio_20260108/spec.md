# Spec: Enhance React Explorer and Audio Pipeline

## Overview
This track aims to finalize the migration from Streamlit to React by ensuring the Explorer interface is fully functional and the audio-to-note pipeline is robust enough for production-like use.

## Objectives
1. **Feature Parity:** Match all hierarchy management capabilities from the legacy backend/Streamlit version in the React UI.
2. **Reliability:** Improve error handling in the asynchronous audio processing service.
3. **UX Refinement:** Provide better feedback to users during long-running operations.

## Scope
### React Explorer
- Full CRUD operations (Create, Rename, Delete) for all hierarchy levels.
- State synchronization between the tree sidebar and main content area.
- Robust handling of empty states and loading transitions.

### Audio Pipeline
- Timeout handling for Deepgram API calls.
- Validation for uploaded audio formats.
- Clear error reporting for PDF generation failures.
