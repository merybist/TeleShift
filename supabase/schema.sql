CREATE TABLE devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid UNIQUE NOT NULL,
    name text,
    is_online boolean DEFAULT false,
    last_seen_at timestamptz,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE connections (
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

CREATE TABLE apps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    name text NOT NULL,
    path text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE settings (
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

CREATE TABLE logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    user_id bigint,
    username text,
    action text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE device_commands (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    command text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    status text DEFAULT 'pending', -- pending, processing, completed, error
    result text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════
-- Supabase Realtime (use this only if deploying on Supabase)
-- ══════════════════════════════════════════════════════════════
ALTER PUBLICATION supabase_realtime ADD TABLE connections;
ALTER PUBLICATION supabase_realtime ADD TABLE apps;
ALTER PUBLICATION supabase_realtime ADD TABLE logs;
ALTER PUBLICATION supabase_realtime ADD TABLE device_commands;

-- ══════════════════════════════════════════════════════════════
-- Raw PostgreSQL Realtime via LISTEN/NOTIFY
-- These triggers fire NOTIFY events so the Electron desktop
-- agent can receive commands without Supabase Realtime.
-- ══════════════════════════════════════════════════════════════

-- Notify on new command insert
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

CREATE TRIGGER logs_notify
AFTER INSERT ON logs
FOR EACH ROW EXECUTE FUNCTION notify_log_insert();
