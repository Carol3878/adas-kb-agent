import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import PG_CONFIG

_connection = None


def get_pg_connection():
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(**PG_CONFIG, cursor_factory=RealDictCursor)
    return _connection
