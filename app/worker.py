import asyncio
import httpx
from app.log_utils import get_daily_logger
from app.config_utils import get_config_value
from app.mysql_utils import mysql_execute, mysql_query


class WorkerState:
    def __init__(self):
        self.div = 0
        self.control_flag = 0

state = WorkerState()

logger = get_daily_logger()

def set_worker_control_flag():
    state.control_flag = 1

async def control_online_devices():
    logger.debug("[control_online_devices]")
    """
        CREATE TABLE IF NOT EXISTS TB_DOM_PERIF (
            Id integer primary key,
            MAC varchar(16) NOT NULL,                       -- MAC Address
            Dispositivo varchar(128) NOT NULL,
            Tipo integer DEFAULT 0,                         -- 0=Ninguno, 1=Wifi 2=RBPi 3=DSC 4=Garnet
    >       Estado integer DEFAULT 0,                       -- 0=Offline
            Direccion_IP varchar(16) DEFAULT "0.0.0.0",
    >       Ultimo_Ok integer DEFAULT 0,
            Usar_Https integer DEFAULT 0,
            Habilitar_Wiegand integer DEFAULT 0,
            Update_Firmware integer DEFAULT 0,
            Update_WiFi integer DEFAULT 0,
            Update_Config integer DEFAULT 0,
            Informacion varchar(1024),
            UNIQUE INDEX idx_perif_id (Id),
            UNIQUE INDEX idx_perif_mac (MAC)
        );
    """
    mysql_execute("UPDATE TB_DOM_PERIF SET Estado = 0 WHERE Ultimo_Ok < (UNIX_TIMESTAMP()-90)")

async def control_assign_pending():
    logger.debug("[control_online_devices]")




async def worker_loop():
    while True:
        # Contador de una hora c/1 segundo
        state.div += 1
        if(state.div >= 3600):
            state.div = 0
        # Cada 1 Segundo
        if(state.control_flag):
            state.control_flag = 0
            control_assign_pending()

        # Cada 60 segundos
        if((state.div % 60) == 0):
            await control_online_devices()

        await asyncio.sleep(get_config_value("TASK_INTERVAL", 1))
        