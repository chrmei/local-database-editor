"""
Dynamic database connection management utilities.

This module handles adding and removing database connections to Django's
connections registry at runtime, allowing users to manage their own database
configurations.
"""
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from .models import DatabaseConfig


def ensure_database_connection(db_alias, user=None):
    """
    Ensure a database connection exists in Django's connections registry.
    Always updates the config to ensure it has all required Django settings.
    
    Args:
        db_alias: The database alias to ensure exists
        user: Optional User instance to verify ownership
    
    Returns:
        bool: True if connection exists and is accessible, False otherwise
    
    Raises:
        DatabaseConfig.DoesNotExist: If db_alias doesn't exist for the user
    """
    # Load database config from model
    if user is not None:
        db_config = DatabaseConfig.objects.get(user=user, alias=db_alias)
    else:
        # Try to find by alias (less secure, but needed for some operations)
        db_config = DatabaseConfig.objects.get(alias=db_alias)
    
    # Always update the config in the registry to ensure it has all required settings
    # This is important because Django expects certain keys like ATOMIC_REQUESTS and TIME_ZONE
    connections.databases[db_alias] = db_config.get_connection_config()
    
    # Close any existing connection to force reconnection with new config
    if db_alias in connections:
        connections[db_alias].close()
    
    return True


def remove_database_connection(db_alias):
    """
    Remove a database connection from Django's connections registry.
    
    Args:
        db_alias: The database alias to remove
    """
    if db_alias in connections.databases and db_alias != 'default':
        # Close connection if open
        if db_alias in connections:
            try:
                connections[db_alias].close()
            except Exception:
                pass
        
        # Remove from registry
        del connections.databases[db_alias]


def test_database_connection(host, port, database, username, password, schema=None):
    """
    Test a database connection without saving it.
    
    Uses psycopg2 directly to avoid Django connection initialization issues
    that can occur when settings aren't fully loaded.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        schema: Optional schema name to verify exists
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    import psycopg2
    from psycopg2 import OperationalError as PsycopgOperationalError, ProgrammingError as PsycopgProgrammingError
    
    try:
        # Use psycopg2 directly for testing to avoid Django connection initialization issues
        # This bypasses Django's connection handler which might try to access settings.TIME_ZONE
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # If schema is provided, verify it exists
                if schema:
                    cursor.execute("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name = %s
                    """, [schema])
                    if not cursor.fetchone():
                        return False, f'Schema "{schema}" does not exist in database "{database}".'
            
            return True, None
            
        finally:
            conn.close()
            
    except (PsycopgOperationalError, PsycopgProgrammingError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def load_user_databases(user):
    """
    Load all database connections for a user into Django's connections registry.
    
    Args:
        user: User instance
    """
    db_configs = DatabaseConfig.objects.filter(user=user)
    for db_config in db_configs:
        try:
            ensure_database_connection(db_config.alias, user=user)
        except Exception:
            # Skip databases that can't be loaded
            pass


def get_user_database_aliases(user):
    """
    Get list of database aliases owned by a user.
    
    Args:
        user: User instance
    
    Returns:
        list: List of database aliases
    """
    return list(DatabaseConfig.objects.filter(user=user).values_list('alias', flat=True))
