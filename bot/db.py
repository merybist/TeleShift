"""
Unified database abstraction layer.
Automatically uses raw PostgreSQL (asyncpg) if DATABASE_URL is set,
otherwise falls back to Supabase.
"""
import json
import re
import asyncio
import logging
from config import DATABASE_URL, SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Security: Whitelist of allowed table names
ALLOWED_TABLES = frozenset([
    'devices', 'device_commands', 'connections', 'apps', 'logs', 'users', 'settings'
])

# Security: Regex for valid SQL identifiers
IDENTIFIER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str) -> str:
    """Validate that a string is a safe SQL identifier."""
    if not IDENTIFIER_REGEX.match(name) or len(name) > 64:
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def _validate_table(table: str) -> str:
    """Validate table name against whitelist."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table not allowed: {table!r}")
    return table


class Database:
    def __init__(self):
        self.pool = None
        self.sb = None
        self.use_pg = bool(DATABASE_URL)

    async def init(self):
        if self.use_pg:
            import asyncpg
            async def _init_conn(conn):
                await conn.set_type_codec(
                    'jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog'
                )
                await conn.set_type_codec(
                    'json', encoder=json.dumps, decoder=json.loads, schema='pg_catalog'
                )
            self.pool = await asyncpg.create_pool(DATABASE_URL, init=_init_conn)
            logger.info("Database: connected via PostgreSQL (asyncpg)")
        else:
            from supabase import create_client
            self.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Database: connected via Supabase")

    # ── SELECT ──────────────────────────────────────────────────
    async def select(self, table: str, columns: str = "*", filters: dict = None,
                     order_by: str = None, ascending: bool = True, limit: int = None) -> list[dict]:
        _validate_table(table)
        if self.use_pg:
            # Validate columns
            if columns != "*":
                cols = [_validate_identifier(c.strip()) for c in columns.split(",")]
                columns = ", ".join(cols)
            query = f"SELECT {columns} FROM {table}"
            params = []
            if filters:
                conds = []
                for i, (k, v) in enumerate(filters.items(), 1):
                    _validate_identifier(k)
                    conds.append(f"{k} = ${i}")
                    params.append(v)
                query += " WHERE " + " AND ".join(conds)
            if order_by:
                _validate_identifier(order_by)
                direction = "ASC" if ascending else "DESC"
                query += f" ORDER BY {order_by} {direction}"
            if limit:
                query += f" LIMIT {int(limit)}"
            rows = await self.pool.fetch(query, *params)
            return [dict(r) for r in rows]
        else:
            q = self.sb.table(table).select(columns)
            for k, v in (filters or {}).items():
                q = q.eq(k, v)
            if order_by:
                q = q.order(order_by, desc=not ascending)
            if limit:
                q = q.limit(limit)
            resp = await asyncio.to_thread(q.execute)
            return resp.data or []

    async def select_one(self, table: str, columns: str = "*", filters: dict = None) -> dict | None:
        rows = await self.select(table, columns, filters, limit=1)
        return rows[0] if rows else None

    # ── INSERT ──────────────────────────────────────────────────
    async def insert(self, table: str, data: dict) -> dict | None:
        _validate_table(table)
        if self.use_pg:
            for k in data.keys():
                _validate_identifier(k)
            cols = ", ".join(data.keys())
            placeholders = ", ".join(f"${i}" for i in range(1, len(data) + 1))
            query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) RETURNING *"
            row = await self.pool.fetchrow(query, *data.values())
            return dict(row) if row else None
        else:
            resp = await asyncio.to_thread(
                lambda: self.sb.table(table).insert(data).execute()
            )
            return resp.data[0] if resp.data else None

    # ── UPDATE ──────────────────────────────────────────────────
    async def update(self, table: str, data: dict, filters: dict = None):
        _validate_table(table)
        if self.use_pg:
            set_parts, params, i = [], [], 1
            for k, v in data.items():
                _validate_identifier(k)
                set_parts.append(f"{k} = ${i}")
                params.append(v)
                i += 1
            query = f"UPDATE {table} SET {', '.join(set_parts)}"
            if filters:
                conds = []
                for k, v in filters.items():
                    _validate_identifier(k)
                    conds.append(f"{k} = ${i}")
                    params.append(v)
                    i += 1
                query += " WHERE " + " AND ".join(conds)
            await self.pool.execute(query, *params)
        else:
            def _run():
                q = self.sb.table(table).update(data)
                for k, v in (filters or {}).items():
                    q = q.eq(k, v)
                q.execute()
            await asyncio.to_thread(_run)

    # ── DELETE ──────────────────────────────────────────────────
    async def delete(self, table: str, filters: dict = None):
        _validate_table(table)
        if self.use_pg:
            query = f"DELETE FROM {table}"
            params = []
            if filters:
                conds = []
                for i, (k, v) in enumerate(filters.items(), 1):
                    _validate_identifier(k)
                    conds.append(f"{k} = ${i}")
                    params.append(v)
                query += " WHERE " + " AND ".join(conds)
            await self.pool.execute(query, *params)
        else:
            def _run():
                q = self.sb.table(table).delete()
                for k, v in (filters or {}).items():
                    q = q.eq(k, v)
                q.execute()
            await asyncio.to_thread(_run)

    # ── RAW EXECUTE (for maintenance queries) ──────────────────
    async def execute(self, query: str, *params):
        if self.use_pg:
            await self.pool.execute(query, *params)
        else:
            await asyncio.to_thread(
                lambda: self.sb.rpc('exec_sql', {'query': query}).execute()
            )


db = Database()
