-- ============================================================================
-- Audit Log Table Creation Script
-- ============================================================================
-- This script creates the audit_log table in Supabase to track all admin
-- review actions (approve, reject, edit) and link them to affected records.
--
-- Run this script in your Supabase SQL Editor
-- ============================================================================

-- Create the audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
  reviewer_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'edited')),
  affected_vuln_ids TEXT[] DEFAULT '{}',
  affected_ofc_ids TEXT[] DEFAULT '{}',
  notes TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_audit_log_submission ON audit_log(submission_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_reviewer ON audit_log(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- Add table comment
COMMENT ON TABLE audit_log IS 'Tracks all admin review actions (approve, reject, edit) with links to affected submissions and production records';

-- Add column comments
COMMENT ON COLUMN audit_log.id IS 'Primary key UUID';
COMMENT ON COLUMN audit_log.submission_id IS 'Foreign key to submissions table';
COMMENT ON COLUMN audit_log.reviewer_id IS 'Foreign key to auth.users table (reviewer who performed the action)';
COMMENT ON COLUMN audit_log.action IS 'Action type: approved, rejected, or edited';
COMMENT ON COLUMN audit_log.affected_vuln_ids IS 'Array of vulnerability IDs that were inserted into production tables';
COMMENT ON COLUMN audit_log.affected_ofc_ids IS 'Array of OFC IDs that were inserted into production tables';
COMMENT ON COLUMN audit_log.notes IS 'Optional reviewer comments or notes';
COMMENT ON COLUMN audit_log.timestamp IS 'Timestamp when the action was performed (UTC)';

-- Enable Row Level Security (RLS)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Admins can view all audit logs
CREATE POLICY "Admins can view all audit logs"
  ON audit_log
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM users_profiles
      WHERE users_profiles.user_id = auth.uid()
      AND users_profiles.role IN ('admin', 'spsa')
    )
  );

-- RLS Policy: Service role can insert audit logs (for API routes)
CREATE POLICY "Service role can insert audit logs"
  ON audit_log
  FOR INSERT
  WITH CHECK (true);  -- Service role bypasses RLS, but this allows API routes to insert

-- RLS Policy: Service role can view all audit logs (for API routes)
CREATE POLICY "Service role can view all audit logs"
  ON audit_log
  FOR SELECT
  USING (true);  -- Service role bypasses RLS, but this ensures API routes can read

-- Grant necessary permissions
GRANT SELECT ON audit_log TO authenticated;
GRANT INSERT ON audit_log TO authenticated;
GRANT SELECT ON audit_log TO service_role;
GRANT INSERT ON audit_log TO service_role;

-- ============================================================================
-- Verification Query
-- ============================================================================
-- Run this after creating the table to verify it was created correctly:
--
-- SELECT 
--   table_name,
--   column_name,
--   data_type,
--   is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'audit_log'
-- ORDER BY ordinal_position;
--
-- ============================================================================

