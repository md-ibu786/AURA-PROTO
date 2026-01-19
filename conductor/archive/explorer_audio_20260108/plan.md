# Plan: Enhance React Explorer and Audio Pipeline

## Phase 1: Explorer Stability
- [x] **Task 1: Hierarchy CRUD Completion** [manual]
    - [x] Write Vitest tests for `useExplorerStore` CRUD actions.
    - [x] Implement rename and delete functionality in the React components.
- [x] **Task 2: State Synchronization** [manual]
    - [x] Write tests to verify tree and grid view sync.
    - [x] Refactor store subscriptions to ensure consistent updates.

## Phase 2: Audio Pipeline Robustness
- [x] **Task 1: Error Handling & Validation** [manual]
    - [x] Write Pytest tests for backend audio validation logic.
    - [x] Implement robust error catching in `services/stt.py` and `api/audio_processing.py`.
- [x] **Task 2: User Feedback** [manual]
    - [x] Implement progress state in the frontend for the audio-to-PDF pipeline.
    - [x] Add toast notifications for background job status.
    - [ ] Implement progress state in the frontend for the audio-to-PDF pipeline.
    - [ ] Add toast notifications for background job status.
