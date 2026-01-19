<objective>
Generate a comprehensive architecture diagram specification for the AURA-PROTO project that can be used to create a visual diagram in Canva. The diagram must be understandable by non-technical stakeholders while accurately representing the complete system architecture.

The output will be used as a blueprint to manually create a professional architecture diagram in Canva, so it needs to include:
- All system components and their relationships
- Data flow between components
- External services and integrations
- Clear layering and organization
- Non-technical descriptions for each component
</objective>

<context>
Project: AURA-PROTO - A hierarchy and note management system

This is a full-stack application with:
- **Frontend**: React + Vite + TypeScript (port 5173)
- **Backend**: FastAPI Python (port 8000)
- **Database**: Firebase Firestore (Cloud NoSQL)
- **External Services**: Deepgram (Speech-to-Text), Google Cloud
- **Testing**: Playwright E2E tests

Key features:
- Hierarchical navigation (Departments → Semesters → Subjects → Modules)
- Document upload (PDF, Doc, Txt)
- Audio processing pipeline (upload → transcribe → generate notes → PDF)
- File serving and management

Relevant files to examine:
- @README.md - Project overview and setup
- @api/main.py - FastAPI application structure and endpoints
- @api/config.py - Firebase initialization
- @frontend/src/App.tsx - React routing structure
- @firebase.json - Firebase configuration
- @frontend/package.json - Frontend dependencies
- @requirements.txt - Backend dependencies
</context>

<requirements>
1. **Analyze the complete architecture** by examining all relevant files
2. **Create a structured specification** that includes:
   - System layers (Presentation, Application, Data, External Services)
   - Component breakdown for each layer
   - Data flow diagrams (what data moves where)
   - Authentication/Security layer
   - File processing pipeline
   - External service integrations

3. **Output format** - Save to: `./architecture-spec.md`

   The specification should be organized as:

   ### 1. High-Level Overview
   - What the system does (business value)
   - User journey summary
   - Technology stack summary

   ### 2. System Components (Layer by Layer)

   **Presentation Layer (Frontend)**
   - React application structure
   - Key components and their purposes
   - User interaction flows

   **Application Layer (Backend)**
   - FastAPI server structure
   - API endpoints and their functions
   - Business logic layers

   **Data Layer**
   - Firestore database structure
   - Collections and document schemas
   - Data relationships

   **External Services Layer**
   - Deepgram (audio transcription)
   - Google Cloud/Firebase services
   - Any other integrations

   ### 3. Data Flow Diagrams

   **User Flow 1: Document Upload**
   - Step-by-step data movement
   - Components involved
   - Final storage location

   **User Flow 2: Audio Processing Pipeline**
   - Upload audio → Deepgram → AI processing → PDF generation → Storage
   - Each step with inputs/outputs

   **User Flow 3: Hierarchy Navigation**
   - How users browse through the system

   ### 4. Security & Authentication
   - Firebase security rules
   - API authentication
   - File access controls

   ### 5. Technical Architecture Details
   - Port configurations
   - Environment variables
   - Dependencies and services

   ### 6. Canva Diagram Blueprint
   A section specifically for creating the visual diagram:
   - **Box Layout Suggestions**: Where to place each component on the canvas
   - **Color Coding**: Suggested colors for different layers
   - **Connector Types**: Solid lines for data flow, dashed for dependencies
   - **Labels**: Exact text to use for each box
   - **Legend**: What each color/shape represents

4. **Non-Technical Language**: Every component must include a plain English description explaining what it does and why it matters

5. **Visual Structure**: Use ASCII diagrams or clear text-based layouts to show component relationships
</requirements>

<implementation>
- Thoroughly explore all API modules (@api/*.py) to understand the complete backend
- Examine the frontend structure to understand all UI components
- Review Firebase rules to understand data access patterns
- Consider the complete user journey from upload to final output
- Explain technical terms using analogies (e.g., "Firestore is like a cloud-based spreadsheet for storing data")
- Focus on making this actionable for someone creating a Canva diagram
</implementation>

<output>
Save the complete architecture specification to: `./architecture-spec.md`

This file should be ready to hand to a designer or use yourself to create the visual diagram in Canva.
</output>

<verification>
Before completing, verify:
- All major components are documented
- Data flows are clearly explained
- External services are included
- The specification is comprehensive enough that someone could recreate the diagram without additional research
- Non-technical descriptions are present for every technical component
- The Canva Blueprint section provides concrete layout guidance
</verification>

<success_criteria>
The output should be:
1. ✅ Comprehensive - covers all aspects of the system
2. ✅ Actionable - provides clear guidance for creating the visual diagram
3. ✅ Non-technical friendly - understandable by business stakeholders
4. ✅ Structured - organized logically for diagram creation
5. ✅ Complete - includes all components, flows, and integrations
</success_criteria>
