<?xml version="1.0" encoding="UTF-8"?>
<!--
  GEMINI.md - AI Assistant Guide for AURA-PROTO
  =============================================
  
  This file provides comprehensive guidance for AI assistants working on the AURA-PROTO project.
  All AI assistants MUST read and follow these guidelines before making any changes to the codebase.
  
  CRITICAL: This file contains binding rules for AI behavior.
  Violation of these rules will result in poor quality output and potential codebase corruption.
  
  Version: 1.0
  Last Updated: 2026-01-03
-->

<guidelines>
  
  <!-- CORE BEHAVIORAL RULES - MANDATORY COMPLIANCE -->
  <behavioral_rules>
    <rule id="research-first" priority="absolute">
      <name>Research-First Approach</name>
      <description>
        BEFORE implementing ANY feature, fix, or change:
        1. Use web search to find current best practices
        2. Search for similar implementations in the codebase
        3. Check documentation for existing patterns
        4. Understand the problem space before proposing solutions
        
        NEVER proceed with implementation without research.
        NEVER assume you know the best approach without verification.
        ALWAYS cite your sources when proposing solutions.
      </description>
      <enforcement>
        <action>Web search must precede every implementation task</action>
        <action>Codebase search must precede architectural decisions</action>
        <action>Documentation review must precede configuration changes</action>
        <tool_requirement>web-search-zai_webSearchPrime OR codesearch OR context7_query-docs OR mgrep must be used</tool_requirement>
        <verification>
          "Show me what research you conducted before proposing this solution"
          "What sources informed your implementation approach?"
        </verification>
      </enforcement>
    </rule>
    
    <rule id="sequential-thinking" priority="absolute">
      <name>Sequential Thinking</name>
      <description>
        Use sequential thinking mcp to solve problems.
        Think through problems step-by-step, ONE step at a time.
        
        WRONG: "I'll fix the bug by updating the validation logic and refactoring the store"
        RIGHT: "First, I need to understand the current validation flow. Let me trace through the code to see how validation currently works..."
        
        For EVERY non-trivial task:
        1. Break the problem into discrete steps
        2. Analyze each step in isolation
        3. Identify dependencies between steps
        4. Execute steps in logical order
        5. Validate each step before proceeding
        6. Document your reasoning at each stage
        
        Use explicit thinking markers:
        - "Step 1: [Action] - [Reasoning]"
        - "Step 2: [Action] - [Reasoning]"
        - "Validation: [What you verified]"
      </description>
      <enforcement>
        <action>Break complex tasks into numbered steps</action>
        <action>Show reasoning for each step</action>
        <action>Validate before moving to next step</action>
        <action>Never skip from problem to solution without analysis</action>
      </enforcement>
    </rule>
    
    <rule id="no-hallucination" priority="absolute">
      <name>Never Hallucinate</name>
      <description>
        AI assistants MUST NOT fabricate information, code, or facts.
        
        FORBIDDEN BEHAVIORS:
        - Inventing API endpoints that don't exist
        - Creating file paths that don't exist
        - Claiming functionality that isn't implemented
        - Suggesting configurations that aren't verified
        - Making up error messages or exception types
        - Inventing library features or methods
        - Creating fake test cases or documentation
        
        REQUIRED BEHAVIORS:
        - Verify all information through code inspection or testing
        - If information is unknown, say "I need to research this"
        - Use exact code and paths from actual files
        - Test assumptions before acting on them
        - Confidently say "I don't know" when appropriate
      </description>
      <examples>
        <wrong>
          "The API has a /api/users endpoint that returns user data"
          (If you haven't verified this endpoint exists)
        </wrong>
        <right>
          "I need to check if a /api/users endpoint exists. Let me search the codebase."
        </right>
      </examples>
      <enforcement>
        <action>Verify existence of all mentioned files, endpoints, and functions</action>
        <action>Test code snippets before presenting them</action>
        <action>Acknowledge uncertainty when present</action>
        <action>Prefer "I need to verify this" over assumption</action>
      </enforcement>
    </rule>
    
    <rule id="not-lazy" priority="absolute">
      <name>Do Not Be Lazy</name>
      <description>
        Thoroughness is mandatory. Lazy shortcuts result in technical debt and bugs.
        
        LAZY BEHAVIORS (PROHIBITED):
        - Copy-pasting code without understanding it
        - Using superficial fixes that don't address root causes
        - Skipping validation steps
        - Ignoring edge cases
        - Making minimal changes without considering implications
        - Not reading related files before editing
        - Assuming "it should work" without testing
        - Skipping error handling "for simplicity"
        - Not considering backward compatibility
        - Ignoring security implications
        
        THOROUGH BEHAVIORS (REQUIRED):
        - Read and understand the full context of changes
        - Consider all affected files and dependencies
        - Implement proper error handling
        - Handle edge cases explicitly
        - Test changes in realistic scenarios
        - Consider security implications
        - Consider performance implications
        - Document reasoning and trade-offs
        - Follow through on complete implementation, not partial fixes
      </description>
      <enforcement>
        <action>Read ALL related files before making changes</action>
        <action>Implement complete solutions, not minimal patches</action>
        <action>Consider and address edge cases</action>
        <action>Add appropriate error handling</action>
        <action>Test changes before considering complete</action>
      </enforcement>
    </rule>

    <rule id="use-subagents" priority="HIGH">
      <name>Use Sub-Agents to Extend Sessions</name>
      <description>
        Use suitable and available sub-agents whenever possible to extend the current session by conserving the context window.
        Sub-agents are crucial for long-running tasks that involve multiple files, complex exploration, or extensive modifications.

        Benefits of using sub-agents:
        - Fresh context windows for each subtask
        - Parallel execution of independent operations
        - Better focus on specific domains (visual, documentation, debugging)
        - Reduced cognitive load on main session

        When to use sub-agents:
        - Multi-file modifications across different features
        - Complex exploration or research tasks
        - Visual/UI changes requiring specialized attention
        - Documentation updates
        - Long-running debugging sessions
        - Tasks that would exceed practical context limits

        Don't try to handle everything in a single session — delegate appropriately.
      </description>
    </rule>

  </behavioral_rules>
  
  <!-- PROJECT OVERVIEW -->
  <project_overview>
    <name>AURA-PROTO</name>
    <description>
      A simplified hierarchy and note management prototype with React frontend and FastAPI backend.
      System for organizing educational content (Computer Science notes) into a hierarchical structure
      (Department &rarr; Semester &rarr; Subject &rarr; Module &rarr; Note) with PDF generation and audio transcription capabilities.
    </description>
    <purpose>
      - Manage educational hierarchy (departments, semesters, subjects, modules)
      - Upload and organize notes within the hierarchy
      - Convert audio recordings to notes via speech-to-text (Deepgram)
      - Generate PDF summaries of notes
      - Migrate from Streamlit to React-based explorer interface
    </purpose>
    <current_status>
      - Backend: FastAPI with SQLite, REST APIs for hierarchy CRUD
      - Frontend: React + Vite + TypeScript (in development for migration)
      - Services: Deepgram STT, OpenAI/Gemini integration (placeholder)
      - Migration: Actively migrating from Streamlit to React explorer
    </current_status>
    <key_directories>
      <directory path="api/" description="FastAPI backend application"/>
      <directory path="frontend/" description="React frontend application (Vite + TypeScript)"/>
      <directory path="pdfs/" description="Generated PDF files"/>
      <directory path="services/" description="Backend services (STT, summarization, PDF generation)"/>
      <directory path="tools/" description="Utility scripts for database maintenance"/>
      <directory path="database/" description="Database schema and initialization scripts"/>
      <directory path="plans/" description="Migration and development plans"/>
      <directory path="prompts/" description="Development prompts and completed tasks"/>
    </key_directories>
  </project_overview>
  
  <!-- ARCHITECTURE -->
  <architecture>
    <backend>
      <framework>FastAPI (Python 3.9+)</framework>
      <port>8000</port>
      <base_url>http://localhost:8000</base_url>
      <database>SQLite (managed via internal scripts)</database>
      <key_components>
        <component name="api/main.py" description="Main FastAPI application entry point"/>
        <component name="api/hierarchy_crud.py" description="CRUD operations for hierarchy entities"/>
        <component name="api/explorer.py" description="Explorer API endpoints for tree navigation"/>
        <component name="api/notes.py" description="Notes management endpoints"/>
        <component name="api/audio_processing.py" description="Audio transcription and processing"/>
        <component name="services/stt.py" description="Speech-to-text service (Deepgram integration)"/>
        <component name="services/pdf_generator.py" description="PDF generation from notes"/>
        <component name="services/summarizer.py" description="Text summarization service"/>
      </key_components>
    </backend>
    
    <frontend>
      <framework>React + Vite + TypeScript</framework>
      <port>5173</port>
      <base_url>http://localhost:5173</base_url>
      <styling>Tailwind CSS</styling>
      <state_management>Zustand + React Query</state_management>
      <ui_components>
        <component name="explorer/" description="File explorer components (Sidebar, Grid, List, ContextMenu)"/>
        <component name="layout/" description="Layout components (Header, Sidebar)"/>
        <component name="components/ui/" description="Reusable UI primitives"/>
      </ui_components>
      <key_files>
        <file name="frontend/src/App.tsx" description="Application entry point"/>
        <file name="frontend/src/pages/ExplorerPage.tsx" description="Main explorer page"/>
        <file name="frontend/src/stores/useExplorerStore.ts" description="Explorer state management"/>
        <file name="frontend/src/types/FileSystemNode.ts" description="TypeScript types for hierarchy nodes"/>
      </key_files>
    </frontend>
    
    <hierarchy_structure>
      <level name="department" description="Top-level organization (e.g., Computer Science)"/>
      <level name="semester" description="Academic semester under a department"/>
      <level name="subject" description="Subject/course under a semester"/>
      <level name="module" description="Module/topic under a subject"/>
      <level name="note" description="Individual note under a module (with PDF)"/>
    </hierarchy_structure>
  </architecture>
  
  <!-- TECHNOLOGY STACK -->
  <technology_stack>
    <backend_technologies>
      <technology name="Python" version="3.9+" description="Backend programming language"/>
      <technology name="FastAPI" version="latest" description="Web framework"/>
      <technology name="Uvicorn" version="latest" description="ASGI server"/>
      <technology name="SQLite" description="Database"/>
      <technology name="Deepgram SDK" description="Speech-to-text transcription"/>
      <technology name="python-multipart" description="File upload handling"/>
    </backend_technologies>
    
    <frontend_technologies>
      <technology name="React" version="18+" description="UI framework"/>
      <technology name="TypeScript" version="5+" description="Type-safe JavaScript"/>
      <technology name="Vite" version="5+" description="Build tool and dev server"/>
      <technology name="Tailwind CSS" version="3+" description="Utility-first CSS"/>
      <technology name="Zustand" description="State management"/>
      <technology name="@tanstack/react-query" description="Server state management"/>
      <technology name="@dnd-kit/core" description="Drag-and-drop functionality"/>
      <technology name="shadcn/ui" description="UI component library"/>
    </frontend_technologies>
    
    <external_services>
      <service name="Deepgram" description="Speech-to-text transcription (API key required)"/>
      <service name="OpenAI/Gemini" description="AI text processing (placeholder)"/>
    </external_services>
  </technology_stack>
  
  <!-- DEVELOPMENT WORKFLOW -->
  <development_workflow>
    <getting_started>
      <step id="1" description="Install Python dependencies">
        <command>pip install -r requirements.txt</command>
        <command>pip install deepgram-sdk python-multipart</command>
      </step>
      <step id="2" description="Set up environment variables">
        <action>Create .env file in root directory</action>
        <content>DEEPGRAM_API_KEY=your_deepgram_key_here</content>
      </step>
      <step id="3" description="Install frontend dependencies">
        <command>cd frontend && npm install</command>
      </step>
      <step id="4" description="Start backend server">
        <command>cd api && python -m uvicorn main:app --reload --port 8000</command>
      </step>
      <step id="5" description="Start frontend dev server">
        <command>cd frontend && npm run dev</command>
      </step>
    </getting_started>
    
    <running_services>
      <service name="Backend" port="8000" url="http://localhost:8000" command="cd api && python -m uvicorn main:app --reload --port 8000"/>
      <service name="Frontend" port="5173" url="http://localhost:5173" command="cd frontend && npm run dev"/>
      <service name="API Docs" endpoint="/docs" url="http://localhost:8000/docs"/>
      <service name="API Redoc" endpoint="/redoc" url="http://localhost:8000/redoc"/>
    </running_services>
    
    <database_operations>
      <operation name="Initialize database">
        <command>cd api && python seed_db.py</command>
        <description>Creates default hierarchy (Computer Science &rarr; Semester &rarr; Subject &rarr; Module)</description>
      </operation>
      <operation name="Cleanup orphaned PDFs">
        <command>python tools/prune_missing_notes.py</command>
        <description>Remove PDF files without database entries</description>
      </operation>
      <operation name="Reset database">
        <command>rm database/database.db && cd api && python seed_db.py</command>
        <description>Delete and recreate database with seed data</description>
      </operation>
    </database_operations>
  </development_workflow>
  
  <!-- CODING CONVENTIONS -->
  <coding_conventions>
    <general>
      <rule>Use clear, descriptive names for variables, functions, and files</rule>
      <rule>Follow existing patterns in the codebase</rule>
      <rule>Add comments for complex logic and non-obvious behavior</rule>
      <rule>Keep functions focused on a single responsibility</rule>
      <rule>Use TypeScript for all new frontend code</rule>
      <rule>Use type hints for all new Python code</rule>
    </general>
    
    <python <rule>Use_conventions>
      snake_case for variables and functions</rule>
      <rule>Use PascalCase for classes</rule>
      <rule>Use Pydantic models for request/response schemas</rule>
      <rule>Follow PEP 8 style guide</rule>
      <rule>Use type hints for function parameters and return values</rule>
      <example>
        def get_hierarchy_tree(depth: int = 5dict[str, Any) -> list[]]:
            """Retrieve hierarchy tree up to specified depth."""
            ...
      </example>
    </python_conventions>
    
    <typescript_conventions>
      <rule>Use camelCase for variables and functions</rule>
      <rule>Use PascalCase for components and classes</rule>
      <rule>Define interfaces for all data structures</rule>
      <rule>Use functional components with hooks</rule>
      <rule>Prefer composition over inheritance</rule>
      <example>
        interface FileSystemNode {
          id: string;
          type: HierarchyType;
          label: string;
          parentId: string | null;
          children?: FileSystemNode[];
          meta?: FileSystemNodeMeta;
        }
      </example>
    </typescript_conventions>
    
    <file_organization>
      <backend_structure>
        <pattern>api/{feature}.py</pattern>
        <description>Each feature gets its own module</description>
        <example>
          api/explorer.py - Explorer API endpoints
          api/hierarchy_crud.py - Hierarchy CRUD operations
          api/audio_processing.py - Audio processing endpoints
        </example>
      </backend_structure>
      <frontend_structure>
        <pattern>frontend/src/{component_type}/{feature}/{files}</pattern>
        <description>Group by feature within component type directory</description>
        <example>
          frontend/src/components/explorer/SidebarTree.tsx
          frontend/src/components/explorer/GridView.tsx
          frontend/src/pages/ExplorerPage.tsx
          frontend/src/stores/useExplorerStore.ts
        </example>
      </frontend_structure>
    </file_organization>
  </coding_conventions>
  
  <!-- API CONVENTIONS -->
  <api_conventions>
    <base_path>/api</base_path>
    
    <endpoints>
      <endpoint_group name="Hierarchy CRUD">
        <endpoint method="POST" path="/departments" description="Create department"/>
        <endpoint method="PUT" path="/departments/{id}" description="Rename department"/>
        <endpoint method="DELETE" path="/departments/{id}" description="Delete department (cascades)"/>
        <endpoint method="POST" path="/semesters" description="Create semester"/>
        <endpoint method="PUT" path="/semesters/{id}" description="Rename semester"/>
        <endpoint method="DELETE" path="/semesters/{id}" description="Delete semester (cascades)"/>
        <endpoint method="POST" path="/subjects" description="Create subject"/>
        <endpoint method="PUT" path="/subjects/{id}" description="Rename subject"/>
        <endpoint method="DELETE" path="/subjects/{id}" description="Delete subject (cascades)"/>
        <endpoint method="POST" path="/modules" description="Create module"/>
        <endpoint method="PUT" path="/modules/{id}" description="Rename module"/>
        <endpoint method="DELETE" path="/modules/{id}" description="Delete module (cascades)"/>
      </endpoint_group>
      
      <endpoint_group name="Notes">
        <endpoint method="GET" path="/notes/{id}" description="Get note by ID"/>
        <endpoint method="PUT" path="/notes/{id}" description="Rename note"/>
        <endpoint method="DELETE" path="/notes/{id}" description="Delete note (PDF remains)"/>
        <endpoint method="POST" path="/notes" description="Create note from audio processing"/>
      </endpoint_group>
      
      <endpoint_group name="Explorer">
        <endpoint method="GET" path="/explorer/tree" description="Get full hierarchy tree"/>
        <endpoint method="GET" path="/explorer/node/{id}" description="Get single node with children"/>
      </endpoint_group>
      
      <endpoint_group name="Audio">
        <endpoint method="POST" path="/audio/transcribe" description="Transcribe audio file"/>
        <endpoint method="POST" path="/audio/process" description="Full audio to PDF pipeline"/>
      </endpoint_group>
    </endpoints>
    
    <response_format>
      <success_response>
        <field name="data" type="any" description="Response payload"/>
        <field name="status" type="string" description="Success status"/>
      </success_response>
      <error_response>
        <field name="detail" type="string" description="Error message"/>
        <field name="status" type="string" description="Error status"/>
      </error_response>
    </response_format>
  </api_conventions>
  
  <!-- STATE MANAGEMENT -->
  <state_management>
    <explorer_store>
      <file>frontend/src/stores/useExplorerStore.ts</file>
      <purpose>Manage explorer UI state</purpose>
      <state_fields>
        <field name="selectedIds" type="string[]" description="Currently selected node IDs"/>
        <field name="activeNodeId" type="string | null" description="Currently active/focused node"/>
        <field name="expandedIds" type="string[]" description="Expanded tree node IDs"/>
        <field name="viewMode" type="'grid' | 'list'" description="Current view mode"/>
        <field name="clipboard" type="object" description="Cut/copy operations"/>
        <field name="currentPath" type="FileSystemNode[]" description="Breadcrumb path"/>
      </state_fields>
      <actions>
        <action name="select" description="Select a single node"/>
        <action name="toggleSelect" description="Toggle selection with Ctrl/Cmd"/>
        <action name="rangeSelect" description="Select range with Shift"/>
        <action name="setViewMode" description="Switch between grid/list"/>
        <action name="expand/collapse" description="Toggle node expansion"/>
      </actions>
    </explorer_store>
    
    <data_fetching>
      <library>@tanstack/react-query</library>
      <purpose>Server state management and caching</purpose>
      <query_keys>
        <key>['explorer', 'tree']</key>
        <key>['notes', noteId]</key>
        <key>['hierarchy', entityType, parentId]</key>
      </query_keys>
    </data_fetching>
  </state_management>
  
  <!-- CURRENT WORK -->
  <current_work>
    <priority name="1">
      <task>Migrate from Streamlit to React explorer interface</task>
      <details>
        - Phase 1: Backend preparation (CORS, static files, explorer API)
        - Phase 2: React frontend architecture (setup, types, stores)
        - Phase 3: Explorer interface implementation (tree, grid/list, drag-drop)
        - Phase 4: Migration and integration
      </details>
      <reference>plans/react-explorer-migration-plan.md</reference>
    </priority>
    
    <priority name="2">
      <task>Enhance backend services</task>
      <details>
        - Improve error handling and validation
        - Add more robust PDF generation
        - Implement better progress tracking for long-running operations
      </details>
    </priority>
    
    <priority name="3">
      <task>Performance optimization</task>
      <details>
        - Optimize tree loading for large hierarchies
        - Implement lazy loading for tree nodes
        - Add pagination for large note lists
      </details>
    </priority>
  </current_work>
  
  <!-- CRITICAL PATHS -->
  <critical_paths>
    <path name="Audio to Note Pipeline">
      <steps>
        <step>Upload audio file</step>
        <step>Transcribe using Deepgram STT</step>
        <step>Summarize/transcribe to structured note</step>
        <step>Generate PDF from note</step>
        <step>Save note to database with hierarchy reference</step>
        <step>Return note to frontend</step>
      </steps>
      <files>
        <file>api/audio_processing.py</file>
        <file>services/stt.py</file>
        <file>services/pdf_generator.py</file>
      </files>
    </path>
    
    <path name="Hierarchy CRUD Operations">
      <steps>
        <step>Receive request at API endpoint</step>
        <step>Validate input and hierarchy constraints</step>
        <step>Execute database operation (with cascade for deletes)</step>
        <step>Update related data structures</step>
        <step>Return updated entity</step>
      </steps>
      <files>
        <file>api/hierarchy_crud.py</file>
        <file>api/hierarchy.py</file>
      </files>
    </path>
    
    <path name="Explorer Tree Loading">
      <steps>
        <step>Frontend requests tree data</step>
        <step>Backend queries database (departments &rarr; semesters &rarr; subjects &rarr; modules &rarr; notes)</step>
        <step>Map entities to ExplorerNode format</step>
        <step>Return nested tree structure</step>
        <step>Frontend renders tree with Zustand state</step>
      </steps>
      <files>
        <file>api/explorer.py</file>
        <file>frontend/src/stores/useExplorerStore.ts</file>
        <file>frontend/src/components/explorer/SidebarTree.tsx</file>
      </files>
    </path>
  </critical_paths>
  
  <!-- COMMON TASKS -->
  <common_tasks>
    <task name="Add new hierarchy level">
      <steps>
        <step>Update database schema (database/schema.sql)</step>
        <step>Add Pydantic models in api/hierarchy_crud.py</step>
        <step>Add CRUD endpoints in api/hierarchy_crud.py</step>
        <step>Update explorer node model in api/explorer.py</step>
        <step>Add TypeScript types in frontend/src/types/FileSystemNode.ts</step>
        <step>Update migration plan if needed</step>
      </steps>
    </task>
    
    <task name="Add new API endpoint">
      <steps>
        <step>Define request/response Pydantic models</step>
        <step>Implement endpoint function in appropriate api module</step>
        <step>Add route to FastAPI app in main.py</step>
        <step>Add frontend API client function</step>
        <step>Add TypeScript types if needed</step>
        <step>Write integration tests</step>
      </steps>
    </task>
    
    <task name="Add new UI component">
      <steps>
        <step>Create component file in appropriate directory</step>
        <step>Define TypeScript interfaces for props</step>
        <step>Implement component with proper state management</step>
        <step>Add to parent component</step>
        <step>Update store if component manages explorer state</step>
        <step>Add styles using Tailwind CSS</step>
      </steps>
    </task>
  </common_tasks>
  
  <!-- TESTING REQUIREMENTS -->
  <testing_requirements>
    <rule>All new features must have corresponding tests</rule>
    <rule>Bug fixes must include regression tests</rule>
    <rule>API endpoints must have integration tests</rule>
    <rule>Complex components must have unit tests</rule>
    
    <testing_tools>
      <tool name="pytest" description="Python testing framework"/>
      <tool name="pytest-asyncio" description="Async test support for FastAPI"/>
      <tool name="Vitest" description="JavaScript/TypeScript testing"/>
    </testing_tools>
    
    <test_locations>
      <location>tests/</location>
      <location>frontend/src/__tests__/</location>
    </test_locations>
  </testing_requirements>
  
  <!-- IMPORTANT NOTES -->
  <important_notes>
    <note type="critical">
      Database uses cascading deletes. Deleting a department deletes all semesters, subjects, modules, and notes under it.
      Use dry_run mode before deletions to see impact.
    </note>
    
    <note type="important">
      PDF files are NOT deleted when notes are deleted from database.
      Use tools/prune_missing_notes.py to clean up orphaned PDFs.
    </note>
    
    <note type="important">
      Deepgram API key must be set in .env file for audio transcription to work.
    </note>
    
    <note type="important">
      Frontend is in active development. Some features may not be fully wired to backend yet.
      Reference plans/react-explorer-migration-plan.md for current status.
    </note>
    
    <note type="caution">
      CORS is configured for localhost:5173 (Vite dev server). Update for production deployment.
    </note>
  </important_notes>
  
  <!-- DEPENDENCIES -->
  <dependencies>
    <dependency name="deepgram-sdk" source="pip" required_for="Audio transcription"/>
    <dependency name="python-multipart" source="pip" required_for="File uploads"/>
    <dependency name="zustand" source="npm" required_for="Frontend state"/>
    <dependency name="@tanstack/react-query" source="npm" required_for="Data fetching"/>
    <dependency name="@dnd-kit/core" source="npm" required_for="Drag and drop"/>
  </dependencies>
  
  <!-- GOTCHAS AND EDGE CASES -->
  <gotchas>
    <gotcha id="1">
      <problem>Tree loading performance with large hierarchies</problem>
      <solution>Implement lazy loading or depth-limited fetching. Don't load entire tree at once for deep hierarchies.</solution>
    </gotcha>
    
    <gotcha id="2">
      <problem>PDF filename encoding and special characters</problem>
      <solution>Sanitize filenames before saving. Use URL-safe names with original title as metadata.</solution>
    </gotcha>
    
    <gotcha id="3">
      <problem>CORS blocking API calls in development</problem>
      <solution>Ensure localhost:5173 is in allowed origins in api/main.py CORSMiddleware configuration.</solution>
    </gotcha>
    
    <gotcha id="4">
      <problem>State synchronization between sidebar tree and main panel</problem>
      <solution>Use Zustand store as single source of truth. Subscribe components to store changes.</solution>
    </gotcha>
    
    <gotcha id="5">
      <problem>Move operations corrupting hierarchy</problem>
      <solution>Validate parent-child relationships on backend. Prevent moving parent into own subtree.</solution>
    </gotcha>
  </gotchas>
  
  <!-- DEBUGGING TIPS -->
  <debugging_tips>
    <tip name="API Issues">
      Use http://localhost:8000/docs to test endpoints interactively
    </tip>
    
    <tip name="Database Issues">
      Check database/database.db directly using SQLite browser or CLI
    </tip>
    
    <tip name="Frontend Issues">
      Use React Dev Tools browser extension and check console for errors
    </tip>
    
    <tip name="Audio Processing">
      Check Deepgram console for transcription status and errors
    </tip>
    
    <tip name="PDF Issues">
      Verify PDF files exist in pdfs/ directory and have correct naming format
    </tip>
  </debugging_tips>
  
  <!-- REFERENCE MATERIALS -->
  <reference_materials>
    <material type="documentation" name="README.md" location="./README.md" description="Project overview and setup"/>
    <material type="documentation" name="HIERARCHY_MANAGEMENT.md" location="./HIERARCHY_MANAGEMENT.md" description="Hierarchy CRUD operations explained"/>
    <material type="plan" name="react-explorer-migration-plan.md" location="./plans/react-explorer-migration-plan.md" description="Detailed migration plan"/>
    <material type="plan" name="MIGRATION_PLAN.md" location="./plans/MIGRATION_PLAN.md" description="High-level migration roadmap"/>
    <material type="code" name="API Main" location="./api/main.py" description="FastAPI application entry point"/>
    <material type="code" name="Explorer API" location="./api/explorer.py" description="Explorer endpoints"/>
    <material type="code" name="Hierarchy CRUD" location="./api/hierarchy_crud.py" description="Hierarchy operations"/>
    <material type="code" name="TypeScript Types" location="./frontend/src/types/FileSystemNode.ts" description="Frontend type definitions"/>
    <material type="code" name="Explorer Store" location="./frontend/src/stores/useExplorerStore.ts" description="State management"/>
  </reference_materials>
  
</guidelines>
