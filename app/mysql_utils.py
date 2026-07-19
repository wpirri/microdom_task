from mysql.connector import Error
from app.db_pool import get_conn
from app.log_utils import get_daily_logger

logger = get_daily_logger()

def mysql_execute_simple(query, params=None):
    conn = get_conn()
    if not conn:
        return -1

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount
    except Error as e:
        logger.error(f"Error ejecutando query: {e}")
        return -1
    finally:
        if cursor is not None:
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
    
def mysql_next_id(table_name, column_name="Id"):
    result = mysql_query(f"SELECT MAX({column_name}) AS max_id FROM {table_name}")
    if result and len(result) > 0:
        return result[0]['max_id'] + 1
    else:
        return 1