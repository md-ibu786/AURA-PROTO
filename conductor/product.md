# Initial Concept
AURA-PROTO is a hierarchical note management system designed to streamline the organization and accessibility of educational content for students and professors.

# Product Vision
A centralized system where professors upload and organize notes for students to easily access their curriculum study materials, bridging the gap between lecture recordings and structured study guides.

# Target Users
- **Computer Science Students:** Seeking organized access to course notes and summaries.
- **Professors/Instructors:** Organizing curriculum materials and providing automated summaries of lectures.

# Core Goals
- **Hierarchical Organization:** Provide a structured navigation through Departments, Semesters, Subjects, and Modules.
- **Automated Summarization:** Convert audio recordings into structured, PDF-based notes to save time and improve retention.
- **Centralized Access:** Create a single source of truth for all curriculum-related documents.

# Key Features
- **Hierarchy Management:** Full CRUD operations for organizing educational levels.
- **Audio Processing Pipeline:** Seamless transcription via Deepgram and PDF generation of summaries.
- **Modern Explorer Interface:** A React-based tree and grid view for intuitive file navigation and management.

# Constraints & Non-Goals
- **Authentication:** User authentication and authorization are deferred to a future phase.
- **Storage:** Currently utilizes local filesystem storage for PDFs; cloud storage integration is a future goal.
- **Single User:** The initial prototype is built for a single-user workflow without collaboration features.
