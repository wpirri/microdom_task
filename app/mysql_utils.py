from mysql.connector import Error
from app.db_pool import get_conn
from app.log_utils import get_daily_logger

logger = get_daily_logger()

def mysql_execute_simple(query, params=None):
    conn = get_conn()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return True
    except Error as e:
        logger.error(f"Error ejecutando query: {e}")
        return False
    finally:
        cursor.close()
        conn.close()  # vuelve al pool

def mysql_query_simple(query, params=None):
    conn = get_conn()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    except Error as e:
        logger.error(f"Error ejecutando query: {e}")
        return None
    finally:
        cursor.close()
        conn.close()  # vuelve al pool

def mysql_execute(query, params=None):
    try:
        return mysql_execute_simple(query, params)
    except Exception:
        # intento 2
        return mysql_execute_simple(query, params)

def mysql_query(query, params=None):
    try:
        return mysql_query_simple(query, params)
    except Exception:
        # intento 2
        return mysql_query_simple(query, params)