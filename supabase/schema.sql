CREATE TABLE devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid UNIQUE NOT NULL,
    name text,
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

-- Увімкнення Realtime для таблиць
ALTER PUBLICATION supabase_realtime ADD TABLE connections;
ALTER PUBLICATION supabase_realtime ADD TABLE apps;
ALTER PUBLICATION supabase_realtime ADD TABLE logs;
ALTER PUBLICATION supabase_realtime ADD TABLE device_commands;
