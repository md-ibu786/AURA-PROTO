# Product Guidelines

## Tone and Prose Style
- **Academic and Professional:** All interface copy and AI-generated summaries should maintain a formal, structured tone appropriate for a university environment.
- **Clarity Above All:** While professional, avoid unnecessary jargon. The goal is to facilitate learning.

## Visual Identity and UI Design
- **Modern & Minimalist:** Emphasize whitespace, clean typography (Sans-serif), and a layout that feels light and organized, similar to Notion or modern SaaS tools.
- **Consistent Hierarchy:** Use distinct visual markers (icons, indentation, color coding) to differentiate between Department, Semester, Subject, and Module levels.

## Error Handling and Feedback
- **Silent & Graceful:** Prefer subtle loading indicators (spinners or progress bars) and generic, non-intrusive messages for background tasks.
- **Stability:** Ensure the system handles network interruptions or transcription timeouts without crashing the UI.

## Navigation and Information Architecture
- **Existing Convention:** Strictly follow the current implementation consisting of a Sidebar Tree for deep navigation paired with Breadcrumbs for orientation.
- **Contextual Access:** Ensure that the current location within the academic hierarchy is always clear to the user.

## AI and Content Structure
- **Current Flow Preservation:** AI-generated notes must adhere to the existing summarization and PDF generation logic currently implemented in the `services/` layer.
- **Structural Integrity:** Maintain the relationship between the original transcription and the refined, summarized output.
