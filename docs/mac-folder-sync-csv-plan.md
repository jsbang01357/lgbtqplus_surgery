# Mac Folder Sync + CSV Plan

This document defines the target architecture for synchronizing a Mac `Developer` folder with Jisong Cloud while keeping patient exam data in CSV for now.

## Goal

- Keep the Mac folder as the human-editable source of truth for files and working artifacts.
- Mirror those files to the cloud for app access and backup.
- Store patient and exam metadata in CSV for now, with a later path to SQL if the data model hardens.
- Avoid coupling file sync, document indexing, and clinical data storage into one datastore.

## Recommended Split

### 1. File Layer

- Mac `Developer` folder
- GCS object storage mirror
- Optional local cache/index on the Mac

This layer owns:

- uploads
- generated PDFs, MD, CSV, ZIP
- raw source files
- per-file hashes and modified timestamps

### 2. Clinical Data Layer

- CSV files

This layer owns:

- patients
- exams
- exam metadata
- file references
- review status
- audit events

The sync layer writes two CSV artifacts:

- `_manifest.csv` for the current workspace snapshot
- `_files.csv` for file reference rows, statuses, and conflict copy pointers

### 3. Sync Layer

- filesystem watcher
- sync queue
- conflict resolver
- retry worker

This layer owns:

- detecting local file change
- pushing to GCS
- pulling from GCS when needed
- recording sync state

## Why Not MongoDB

MongoDB is reasonable for JSON documents, but it does not solve the main problem here:

- folder change detection
- deterministic conflict handling
- file rename/move semantics
- binary artifact storage
- auditability across local and cloud copies

For this project, MongoDB would add operational overhead without removing the need for a file-sync system.

## Sync Model

### Source of Truth

- Human-authored working files live on the Mac folder.
- Cloud storage is the replicated copy.
- CSV stores the durable structured metadata for now.

### Event Flow

1. File changes happen in the Mac folder.
2. A watcher detects create/update/delete/rename events.
3. The event is normalized into a sync job.
4. The worker hashes the file and checks current sync state.
5. If the file changed locally, the worker uploads it to GCS.
6. If the remote copy changed first, the worker creates a conflict copy.
7. CSV records the resulting file reference and sync status.

## Conflict Rules

- Never silently overwrite newer remote data.
- Prefer content hash plus modified time comparison.
- On collision, preserve both versions and mark one as a conflict copy.
- Record the conflict in CSV so the UI can surface it later.

## Proposed CSV Schema

Minimal tables:

- `patients`
- `exams`
- `exam_files`
- `exam_notes`
- `sync_state`
- `sync_events`
- `sync_files`
- `audit_events`

Useful fields:

- `id`
- `patient_id`
- `exam_id`
- `storage_key`
- `local_path`
- `content_hash`
- `mime_type`
- `size_bytes`
- `created_at`
- `updated_at`
- `synced_at`
- `sync_status`
- `source_system`

## Recommended Implementation Phases

### Phase 1

- Add a sync manifest format for local files.
- Track file hash, path, and remote key.
- Store sync state in CSV.

### Phase 2

- Implement filesystem watcher on macOS.
- Add a worker that batches and retries sync jobs.
- Add conflict copy behavior.

### Phase 3

- Add CSV-backed patient/exam metadata.
- Connect file references to exams.
- Surface sync status in the UI.

## Operational Notes

- Do not make the app depend on one monolithic DB for files and clinical data.
- Keep binary artifacts in object storage.
- Keep structured clinical data in CSV for now, and graduate to SQL later if needed.
- Keep the sync worker small and restartable.

## Current Recommendation

For this repo, the best path is:

1. Mac folder watcher + GCS mirror for files
2. CSV for patient exam records
3. No MongoDB in the critical path
