-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--  LeakOSINT Bot - Migration v2
--  Run this AFTER your existing schema
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Add invite_link column for private channel links
ALTER TABLE required_channels
ADD COLUMN IF NOT EXISTS invite_link TEXT;

-- Add description column (optional)
ALTER TABLE required_channels
ADD COLUMN IF NOT EXISTS description TEXT;

-- Add index for invite link lookups
CREATE INDEX IF NOT EXISTS idx_channels_invite_link
ON required_channels(invite_link);
