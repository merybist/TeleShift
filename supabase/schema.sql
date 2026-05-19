CREATE TABLE IF NOT EXISTS devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid UNIQUE NOT NULL,
    name text,
    is_online boolean DEFAULT false,
    last_seen_at timestamptz,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS connections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    hash_token text UNIQUE NOT NULL,
    user_id bigint,
    username text,
    first_name text,
    is_active boolean DEFAULT false,
    connected_at timestamptz,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    name text NOT NULL,
    path text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS settings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE UNIQUE,
    notify_on_command boolean DEFAULT true,
    notify_online boolean DEFAULT true,
    auto_disconnect_enabled boolean DEFAULT false,
    auto_disconnect_hours int DEFAULT 24,
    disconnect_on_close boolean DEFAULT false,
    screenshot_quality text DEFAULT 'high',
    language text DEFAULT 'ua'
);

CREATE TABLE IF NOT EXISTS logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    user_id bigint,
    username text,
    action text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_commands (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    command text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    status text DEFAULT 'pending', -- pending, processing, completed, error
    result text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE connections;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE connections REPLICA IDENTITY FULL;

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE apps;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE logs;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE device_commands;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE OR REPLACE FUNCTION notify_new_command()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('new_command', json_build_object(
    'id', NEW.id,
    'device_id', NEW.device_id,
    'command', NEW.command,
    'payload', NEW.payload,
    'status', NEW.status
  )::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS device_commands_notify ON device_commands;
CREATE TRIGGER device_commands_notify
AFTER INSERT ON device_commands
FOR EACH ROW EXECUTE FUNCTION notify_new_command();

-- Notify on connection changes
CREATE OR REPLACE FUNCTION notify_connection_change()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('connection_change', row_to_json(NEW)::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS connections_notify ON connections;
CREATE TRIGGER connections_notify
AFTER INSERT OR UPDATE ON connections
FOR EACH ROW EXECUTE FUNCTION notify_connection_change();

-- Notify on apps table changes
CREATE OR REPLACE FUNCTION notify_apps_change()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('apps_change', COALESCE(row_to_json(NEW), '{}')::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS apps_notify ON apps;
CREATE TRIGGER apps_notify
AFTER INSERT OR UPDATE OR DELETE ON apps
FOR EACH ROW EXECUTE FUNCTION notify_apps_change();

-- Notify on new log entries
CREATE OR REPLACE FUNCTION notify_log_insert()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('log_insert', row_to_json(NEW)::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS logs_notify ON logs;
CREATE TRIGGER logs_notify
AFTER INSERT ON logs
FOR EACH ROW EXECUTE FUNCTION notify_log_insert();

-- ── Indexes ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_device_commands_device_status
ON device_commands(device_id, status);

CREATE INDEX IF NOT EXISTS idx_device_commands_created_at
ON device_commands(created_at);

CREATE INDEX IF NOT EXISTS idx_connections_device_active
ON connections(device_id, is_active);

-- ── Cleanup: delete completed commands older than 2 days ─────────
CREATE OR REPLACE FUNCTION cleanup_old_commands()
RETURNS void AS $$
BEGIN
  DELETE FROM device_commands
  WHERE status IN ('completed', 'error')
    AND created_at < now() - interval '2 days';
END;
$$ LANGUAGE plpgsql;

-- Schedule via pg_cron (if available) or call manually:
-- SELECT cron.schedule('cleanup-commands', '0 4 * * *', 'SELECT cleanup_old_commands()');

-- ── Row Level Security ───────────────────────────────────────────
-- Electron agent uses anon key with device_id passed via request header (apikey claim).
-- Bot uses service_role key which bypasses RLS entirely.
-- RLS policies restrict anon access to only rows matching the device_id from the request header.

-- Helper: extract device_id from custom request header
CREATE OR REPLACE FUNCTION requesting_device_id()
RETURNS uuid AS $$
BEGIN
  RETURN COALESCE(
    current_setting('request.headers', true)::json->>'x-device-id',
    '00000000-0000-0000-0000-000000000000'
  )::uuid;
END;
$$ LANGUAGE plpgsql STABLE;

-- devices
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "devices_select_own" ON devices FOR SELECT USING (device_id = requesting_device_id());
CREATE POLICY "devices_update_own" ON devices FOR UPDATE USING (device_id = requesting_device_id());
CREATE POLICY "devices_insert_own" ON devices FOR INSERT WITH CHECK (device_id = requesting_device_id());

-- connections
ALTER TABLE connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "connections_select_own" ON connections FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "connections_insert_own" ON connections FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "connections_update_own" ON connections FOR UPDATE USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));

-- device_commands
ALTER TABLE device_commands ENABLE ROW LEVEL SECURITY;
CREATE POLICY "commands_select_own" ON device_commands FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "commands_update_own" ON device_commands FOR UPDATE USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "commands_insert_own" ON device_commands FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));

-- apps
ALTER TABLE apps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "apps_select_own" ON apps FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "apps_insert_own" ON apps FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "apps_update_own" ON apps FOR UPDATE USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "apps_delete_own" ON apps FOR DELETE USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));

-- settings
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "settings_select_own" ON settings FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "settings_insert_own" ON settings FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "settings_update_own" ON settings FOR UPDATE USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));

-- logs
ALTER TABLE logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "logs_select_own" ON logs FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
CREATE POLICY "logs_insert_own" ON logs FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE device_id = requesting_device_id()));
