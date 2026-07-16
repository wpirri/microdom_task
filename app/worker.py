import asyncio
import json
import requests
from app.log_utils import get_daily_logger
from app.config_utils import get_config_value
from app.mysql_utils import mysql_execute, mysql_query

class WorkerConfig:
    def __init__(self):
        self.System_Key = ""
        self.Cloud_Host_1_Address = ""
        self.Cloud_Host_1_Port = 0
        self.Cloud_Host_1_Proto = ""
        self.Cloud_Host_2_Address = ""
        self.Cloud_Host_2_Port = 0
        self.Cloud_Host_2_Proto = ""
        self.Use_host = 1  # 1=Cloud_Host_1, 2=Cloud_Host_2
        self.Host_Api_Endpoint = "/cgi-bin/dompi_cloud_notif.cgi"  # Endpoint de la API en el host remoto

config = WorkerConfig()

logger = get_daily_logger()

# ##############################################################################################
# Query minimo
#   {"System_Key":"PUEYRREDON2679-B1686NTU"}
# Query con datos de assign
#   {"MAC":"ECFABC3B667B","Tipo_HW":"1","Direccion_IP":"192.168.10.176","Objeto":"Extractor Cocina","ASS_Id":"51","Tipo_ASS":"0","Port":"OUT3","Estado":"1","Analog_Mult_Div_Valor":"1"}
#
# Respuesta minima
#   {"response":{"resp_code":"0", "resp_msg":"Ok"}}
# Respuesta con acciones
#   {"System_Key":"PUEYRREDON2679-B1686NTU","Time_Stamp":"1784164060","Objeto":"Extractor Cocina","Accion":"on"}
#
def query_cloud(msg):
    if len(config.Cloud_Host_1_Address) == 0 and len(config.Cloud_Host_2_Address) == 0:
        logger.warning("[query_cloud] No hay hosts configurados para enviar la notificación.")
        return None

    resp_message = None

    # Si el que está apuntado no está configurado e voy por el otro
    if config.Use_host == 1 and len(config.Cloud_Host_1_Address) == 0:
        config.Use_host = 2
    elif config.Use_host == 2 and len(config.Cloud_Host_2_Address) == 0:
        config.Use_host = 1
    # Armo la URL con el host configurado
    if config.Use_host == 1:
        if {config.Cloud_Host_1_Port} == 0:
            url = f"{config.Cloud_Host_1_Proto}://{config.Cloud_Host_1_Address}{config.Host_Api_Endpoint}"
        else:
            url = f"{config.Cloud_Host_1_Proto}://{config.Cloud_Host_1_Address}:{config.Cloud_Host_1_Port}{config.Host_Api_Endpoint}"
    else:
        if {config.Cloud_Host_2_Port} == 0:
            url = f"{config.Cloud_Host_2_Proto}://{config.Cloud_Host_2_Address}{config.Host_Api_Endpoint}"
        else:
            url = f"{config.Cloud_Host_2_Proto}://{config.Cloud_Host_2_Address}:{config.Cloud_Host_2_Port}{config.Host_Api_Endpoint}"

    try:
        #logger.info(f"[query_cloud] POST: {url}")
        response = requests.post(url, data=msg)
        if response.status_code == 200:
            resp_message = response.json()
            #logger.info(f"[query_cloud] Resp: OK [{resp_message}]")
        else:
            logger.error(f"[query_cloud] [{response.status_code}] en POST a {url}")
            # Cambio de host para el próximo intento
            config.Use_host = (3 - config.Use_host)
    except Exception as e:
        logger.error(f"[query_cloud] Excepción en POST a {url} [{e}]")
        # Cambio de host para el próximo intento
        config.Use_host = (3 - config.Use_host)
    
    return resp_message

def get_estado_de_assign(id_assign):
    """
    Devuelve el estado del assign con el id proporcionado.
    """
    query_result = mysql_query(f"SELECT Estado FROM TB_DOM_ASSIGN WHERE Id = {id_assign};")
    if query_result:
        return query_result[0]['Estado']
    else:
        logger.error(f"get_estado_de_assign: No se encontró assign con Id {id_assign}")
        return None

def get_system_config():
    """
    Devuelve la configuración del sistema.
    """
    query_result = mysql_query("SELECT * FROM TB_DOM_CONFIG ORDER BY Id DESC LIMIT 1;")
    if query_result:
        config.System_Key = query_result[0]['System_Key']
        config.Cloud_Host_1_Address = query_result[0]['Cloud_Host_1_Address']
        config.Cloud_Host_1_Port = query_result[0]['Cloud_Host_1_Port']
        config.Cloud_Host_1_Proto = query_result[0]['Cloud_Host_1_Proto']
        config.Cloud_Host_2_Address = query_result[0]['Cloud_Host_2_Address']
        config.Cloud_Host_2_Port = query_result[0]['Cloud_Host_2_Port']
        config.Cloud_Host_2_Proto = query_result[0]['Cloud_Host_2_Proto']
    else:
        logger.error("get_system_config: No se encontró configuración del sistema.")

async def tareas_de_dispositivos():
    logger.debug("[tareas_de_dispositivos]")
    mysql_execute("UPDATE TB_DOM_PERIF SET Estado = 0 WHERE Ultimo_Ok < (UNIX_TIMESTAMP()-30) AND Estado != 0;")

async def tareas_de_grupos():
    logger.debug("[tareas_de_grupos]")
    query_result = mysql_query("SELECT * FROM TB_DOM_GROUP WHERE Id > 0;")
    if query_result:
        for i in range(0, len(query_result)):
            listado_objetos = query_result[i]['Listado_Objetos'].split(",")
            todos_encendidos = True
            todos_apagados = True
            for obj_id in listado_objetos:
                if obj_id.isnumeric():
                    estado = get_estado_de_assign(obj_id)
                    if estado == 0:
                        todos_encendidos = False
                    elif estado == 1:
                        todos_apagados = False
            if todos_encendidos and query_result[i]['Estado'] != 1:
                mysql_execute(f"UPDATE TB_DOM_GROUP SET Estado = 1, Actualizar = 1 WHERE Id = {query_result[i]['Id']};")
            elif todos_apagados and query_result[i]['Estado'] != 0:
                mysql_execute(f"UPDATE TB_DOM_GROUP SET Estado = 0, Actualizar = 1 WHERE Id = {query_result[i]['Id']};")

async def tareas_de_nube():
    query_result = mysql_query("SELECT Id AS ASS_Id,Objeto,Tipo,Estado,Icono_Apagado,"
        "Icono_Encendido,Grupo_Visual,Planta,Cord_x,"
        "Cord_y,Coeficiente,Analog_Mult_Div,Analog_Mult_Div_Valor,Flags "
        "FROM TB_DOM_ASSIGN WHERE Id > 0 AND Grupo_Visual > 0 AND Actualizar = 1;")
    if query_result:
        for i in range(0, len(query_result)):
            query_result[i]['System_Key'] = config.System_Key
            logger.info(f"[tareas_de_nube] Req: {query_result[i]}")
            cloud_response = query_cloud(query_result[i])
            logger.info(f"[tareas_de_nube] Resp: {cloud_response}")
            mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Actualizar = 0 WHERE Id = {query_result[i]['ASS_Id']};")
    else:
        query_result = [{"System_Key": config.System_Key}]
        logger.info(f"[tareas_de_nube] Req: {query_result[0]}")
        cloud_response = query_cloud(query_result[0])
        logger.info(f"[tareas_de_nube] Resp: {cloud_response}")

async def worker_loop():
    div = 0
    get_system_config()
    logger.info(f"System_Key: {config.System_Key}")
    logger.info(f"Cloud_Host_1_Address: {config.Cloud_Host_1_Address}")
    logger.info(f"Cloud_Host_1_Port: {config.Cloud_Host_1_Port}")
    logger.info(f"Cloud_Host_1_Proto: {config.Cloud_Host_1_Proto}")
    logger.info(f"Cloud_Host_2_Address: {config.Cloud_Host_2_Address}")
    logger.info(f"Cloud_Host_2_Port: {config.Cloud_Host_2_Port}")
    logger.info(f"Cloud_Host_2_Proto: {config.Cloud_Host_2_Proto}")

    while True:
        div += 1
        if div >= 5:
            div = 0
            await tareas_de_dispositivos()
            await tareas_de_grupos()
            
        await tareas_de_nube()

        await asyncio.sleep(get_config_value("TASK_INTERVAL", 1))
        