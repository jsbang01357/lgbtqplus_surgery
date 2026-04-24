# 📝 Todo

Use this file to write short checklists for non-trivial work.
Mark items as complete as you go.

---

- [x] Read the repository structure and main entrypoints
- [x] Inspect core modules for storage, memos, tools, auth, and logging
- [x] Review deployment/configuration files and supporting assets
- [x] Summarize architecture, behavior, risks, and improvement opportunities

## Summary
- Reviewed the full codebase and mapped how the Streamlit app routes into GCS-backed file, memo, tool, auth, and access-log features.
- Identified a few architecture mismatches between README claims and current implementation, plus several maintainability and security risks to watch.

- [x] Re-read the current README against the implementation
- [x] Rewrite README to match the current project behavior only
- [x] Verify the updated README is consistent with the repository structure
- [x] Inspect dependency and ignore-file consistency
- [x] Update requirements.txt to match runtime imports
- [x] Clean up .gitignore for the current repo workflow
- [x] Polish README wording after dependency/ignore cleanup

## Summary
- Added the missing runtime dependency used by the access-log admin table.
- Cleaned `.gitignore` to match current local-development artifacts while keeping repo-managed task files and instructions trackable.
- Updated README so installation and repo-management notes align with the current dependency and local-config setup.
