CREATE TABLE IF NOT EXISTS devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid UNIQUE NOT NULL,
    name text,
    is_online boolean DEFAULT false,
    last_seen_at timestamptz,
    monitor_count int DEFAULT 1,
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
    status text DEFAULT 'pending',
    result text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scheduled_commands (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES devices(id) ON DELETE CASCADE,
    user_id bigint NOT NULL,
    command text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    scheduled_at time NOT NULL,
    is_daily boolean DEFAULT false,
    last_run_at timestamptz,
    status text DEFAULT 'pending',
    created_at timestamptz DEFAULT now()
);

-- Realtime
DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE connections;
  ALTER PUBLICATION supabase_realtime ADD TABLE apps;
  ALTER PUBLICATION supabase_realtime ADD TABLE logs;
  ALTER PUBLICATION supabase_realtime ADD TABLE device_commands;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Triggers
CREATE OR REPLACE FUNCTION notify_new_command() RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('new_command', json_build_object('id', NEW.id, 'device_id', NEW.device_id, 'command', NEW.command, 'payload', NEW.payload, 'status', NEW.status)::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS device_commands_notify ON device_commands;
CREATE TRIGGER device_commands_notify AFTER INSERT ON device_commands FOR EACH ROW EXECUTE FUNCTION notify_new_command();

-- RLS
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_commands ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION get_current_device_internal_id() RETURNS uuid AS $$
  SELECT id FROM devices WHERE device_id::text = (current_setting('request.headers', true)::json->>'x-device-id') LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE POLICY "agent_own_device" ON devices FOR ALL TO anon USING (device_id::text = (current_setting('request.headers', true)::json->>'x-device-id')) WITH CHECK (device_id::text = (current_setting('request.headers', true)::json->>'x-device-id'));
CREATE POLICY "agent_own_commands" ON device_commands FOR ALL TO anon USING (device_id = get_current_device_internal_id());
CREATE POLICY "agent_own_apps" ON apps FOR ALL TO anon USING (device_id = get_current_device_internal_id());
CREATE POLICY "agent_own_settings" ON settings FOR ALL TO anon USING (device_id = get_current_device_internal_id());
CREATE POLICY "agent_own_connections" ON connections FOR ALL TO anon USING (device_id = get_current_device_internal_id());
CREATE POLICY "agent_own_logs" ON logs FOR ALL TO anon USING (device_id = get_current_device_internal_id());
CREATE POLICY "agent_own_schedules" ON scheduled_commands FOR ALL TO anon USING (device_id = get_current_device_internal_id());

CREATE POLICY "Service Role: full access" ON devices FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON connections FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON apps FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON settings FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON logs FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON device_commands FOR ALL TO service_role USING (true);
CREATE POLICY "Service Role: full access" ON scheduled_commands FOR ALL TO service_role USING (true);
