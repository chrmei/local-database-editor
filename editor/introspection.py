"""
Introspect PostgreSQL schemas, tables, columns, and primary keys via information_schema.
Results are cached briefly to avoid repeated queries; pass refresh=True to bypass cache.
"""
from django.core.cache import cache
from django.conf import settings


def _cache_key(prefix: str, *parts: str) -> str:
    return ":".join([prefix] + list(parts))


def get_schemas(db_alias: str, refresh: bool = False) -> list[str]:
    """Return list of schema names in the database (excluding pg_* and information_schema)."""
    key = _cache_key("editor", "schemas", db_alias)
    if not refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached
    from django.db import connections
    conn = connections[db_alias]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            AND schema_name NOT LIKE 'pg_%'
            ORDER BY schema_name
        """)
        names = [row[0] for row in cur.fetchall()]
    cache.set(key, names, timeout=getattr(settings, "INTROSPECTION_CACHE_TIMEOUT", 60))
    return names


def get_tables(db_alias: str, schema_name: str, refresh: bool = False) -> list[str]:
    """Return list of table names in the given schema (only base tables)."""
    key = _cache_key("editor", "tables", db_alias, schema_name)
    if not refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached
    from django.db import connections
    conn = connections[db_alias]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, [schema_name])
        names = [row[0] for row in cur.fetchall()]
    cache.set(key, names, timeout=getattr(settings, "INTROSPECTION_CACHE_TIMEOUT", 60))
    return names


def get_columns(db_alias: str, schema_name: str, table_name: str, refresh: bool = False) -> list[dict]:
    """
    Return list of column info dicts: name, data_type, is_nullable, column_default.
    column_default is the PostgreSQL default expression (e.g. nextval(...) for serial).
    """
    key = _cache_key("editor", "columns", db_alias, schema_name, table_name)
    if not refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached
    from django.db import connections
    conn = connections[db_alias]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, [schema_name, table_name])
        columns = [
            {
                "name": row[0],
                "data_type": row[1],
                "is_nullable": row[2] == "YES",
                "column_default": row[3],
            }
            for row in cur.fetchall()
        ]
    cache.set(key, columns, timeout=getattr(settings, "INTROSPECTION_CACHE_TIMEOUT", 60))
    return columns


def get_pk_sequence_columns(db_alias: str, schema_name: str, table_name: str, refresh: bool = False) -> list[str]:
    """
    Return list of primary key column names that use a sequence (nextval) as default.
    Used to omit these columns on INSERT so PostgreSQL fills them automatically.
    """
    columns = get_columns(db_alias, schema_name, table_name, refresh=refresh)
    pk_columns = get_primary_key_columns(db_alias, schema_name, table_name, refresh=refresh)
    pk_set = set(pk_columns)
    result = []
    for c in columns:
        if c["name"] not in pk_set:
            continue
        default = (c.get("column_default") or "").strip().lower()
        if "nextval" in default:
            result.append(c["name"])
    return result


def get_primary_key_columns(db_alias: str, schema_name: str, table_name: str, refresh: bool = False) -> list[str]:
    """Return ordered list of column names that form the primary key."""
    key = _cache_key("editor", "pk", db_alias, schema_name, table_name)
    if not refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached
    from django.db import connections
    conn = connections[db_alias]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
                AND tc.table_name = kcu.table_name
            WHERE tc.table_schema = %s AND tc.table_name = %s
            AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY kcu.ordinal_position
        """, [schema_name, table_name])
        names = [row[0] for row in cur.fetchall()]
    cache.set(key, names, timeout=getattr(settings, "INTROSPECTION_CACHE_TIMEOUT", 60))
    return names


def get_table_meta(db_alias: str, schema_name: str, table_name: str, refresh: bool = False) -> tuple[list[dict], list[str]]:
    """Return (columns, pk_columns). Convenience to get both in one go."""
    columns = get_columns(db_alias, schema_name, table_name, refresh=refresh)
    pk_columns = get_primary_key_columns(db_alias, schema_name, table_name, refresh=refresh)
    return columns, pk_columns


def invalidate_introspection_cache(db_alias: str = None, schema_name: str = None, table_name: str = None):
    """Invalidate cached introspection for the given scope. None means all for that level."""
    # LocMemCache doesn't support delete by pattern; we just document that Refresh clears by re-fetching with refresh=True.
    # So we don't need to implement pattern delete; views will pass refresh=True when user clicks Refresh.
    pass


def create_schema(db_alias: str, schema_name: str) -> tuple[bool, str]:
    """
    Create a new schema in the database.
    
    Args:
        db_alias: Database alias
        schema_name: Name of the schema to create
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    # Validate schema name
    if not schema_name or not schema_name.strip():
        return False, "Schema name cannot be empty"
    
    schema_name = schema_name.strip()
    
    # Prevent creating system schemas
    system_schemas = {'pg_catalog', 'information_schema', 'pg_toast'}
    if schema_name.lower() in system_schemas or schema_name.lower().startswith('pg_'):
        return False, f"Cannot create system schema '{schema_name}'"
    
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError
    
    try:
        conn = connections[db_alias]
        with conn.cursor() as cur:
            # Use IF NOT EXISTS to avoid errors if schema already exists
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS {conn.ops.quote_name(schema_name)}')
        # Invalidate schema cache
        cache.delete(_cache_key("editor", "schemas", db_alias))
        return True, None
    except (OperationalError, ProgrammingError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error creating schema: {str(e)}"


def delete_schema(db_alias: str, schema_name: str, force: bool = False) -> tuple[bool, str]:
    """
    Delete a schema from the database.
    
    Args:
        db_alias: Database alias
        schema_name: Name of the schema to delete
        force: If True, delete even if schema contains tables (CASCADE)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    # Validate schema name
    if not schema_name or not schema_name.strip():
        return False, "Schema name cannot be empty"
    
    schema_name = schema_name.strip()
    
    # Prevent deleting system schemas
    system_schemas = {'pg_catalog', 'information_schema', 'pg_toast'}
    if schema_name.lower() in system_schemas or schema_name.lower().startswith('pg_'):
        return False, f"Cannot delete system schema '{schema_name}'"
    
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError
    
    try:
        conn = connections[db_alias]
        
        # Check if schema has tables
        tables = get_tables(db_alias, schema_name, refresh=True)
        if tables and not force:
            return False, f"Schema '{schema_name}' contains {len(tables)} table(s). Use force delete to remove them."
        
        with conn.cursor() as cur:
            if force:
                cur.execute(f'DROP SCHEMA IF EXISTS {conn.ops.quote_name(schema_name)} CASCADE')
            else:
                cur.execute(f'DROP SCHEMA IF EXISTS {conn.ops.quote_name(schema_name)}')
        
        # Invalidate caches
        cache.delete(_cache_key("editor", "schemas", db_alias))
        # Also invalidate table caches for this schema
        for table in tables:
            cache.delete(_cache_key("editor", "tables", db_alias, schema_name))
            cache.delete(_cache_key("editor", "columns", db_alias, schema_name, table))
            cache.delete(_cache_key("editor", "pk", db_alias, schema_name, table))
        
        return True, None
    except (OperationalError, ProgrammingError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error deleting schema: {str(e)}"


def schema_has_tables(db_alias: str, schema_name: str) -> bool:
    """Check if a schema contains any tables."""
    tables = get_tables(db_alias, schema_name, refresh=True)
    return len(tables) > 0
