-- Add description column to workspace_silos for theme-based silo model.
-- Silos are analytical themes (e.g., "Revenue Performance", "Customer Risk")
-- rather than column-based filters.
ALTER TABLE sentinel.workspace_silos
    ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
