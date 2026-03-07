from mysql.connector import pooling, Error
from app.config_utils import get_config_value
from app.log_utils import get_daily_logger

logger = get_daily_logger()

pool = pooling.MySQLConnectionPool(
    pool_name="main_pool",
    pool_size=10,
    host=get_config_value("DBHOST"),
    database=get_config_value("DBNAME"),
    user=get_config_value("DBUSER"),
    password=get_config_value("DBPASSWORD"),
    autocommit=True
)

def get_conn():
    try:
        return pool.get_connection()
    except Error as e:
        print(f"Error obteniendo conexión del pool: {e}")
        logger.info(f"Error obteniendo conexión del pool: {e}")
        return None
    