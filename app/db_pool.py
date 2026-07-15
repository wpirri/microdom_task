from mysql.connector import pooling, Error
from app.log_utils import get_daily_logger
import os

logger = get_daily_logger()

_pool = None   # ← El pool no se crea hasta que se pida la primera conexión


def get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="main_pool",
                pool_size=10,
                host=os.getenv("DBHOST"),
                database=os.getenv("DBNAME"),
                user=os.getenv("DBUSER"),
                password=os.getenv("DBPASSWORD"),
                autocommit=True
            )
            logger.info("Pool MySQL inicializado exitosamente")
        except Error as e:
            logger.info(f"Error inicializando pool MySQL: {e}")
            raise
    return _pool


def get_conn():
    try:
        pool = get_pool()  # ← Se crea aquí recién en la primera llamada
        return pool.get_connection()
    except Error as e:
        logger.info(f"Error obteniendo conexión del pool: {e}")
        return None
