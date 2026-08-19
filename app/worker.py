import asyncio
import json
from datetime import datetime
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
        self.Cloud_Status = 0  # 1=on-line, 0=off-line

config = WorkerConfig()

logger = get_daily_logger()

# ##############################################################################################
# Funciones para manejar los objetos (assigns) en la base de datos
def change_assign_by_name(name, accion, parametro=0):
    if accion == "ON":
        logger.info(f"[change_assign_by_name] Encender: {name}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = 1, Actualizar = 1 WHERE Objeto = '{name}'")
    elif accion == "OFF":
        logger.info(f"[change_assign_by_name] Apagar: {name}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = 0, Actualizar = 1 WHERE Objeto = '{name}'")
    elif accion == "SWITCH":
        logger.info(f"[change_assign_by_name] Alternar: {name}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = (1 - Estado), Actualizar = 1 WHERE Objeto = '{name}'")
    elif accion == "PULSE":
        logger.info(f"[change_assign_by_name] Pulso de: {parametro}s a: {name}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = (1 + {parametro}), Actualizar = 1 WHERE Objeto = '{name}'")
    else:
        logger.warning(f"change_assign_by_name: acción desconocida {accion} para Objeto={name}")

# ##############################################################################################
# Verifica si hay comandos a ejecutar en la respuesta de la nube y los ejecuta.
# Por ahora no hace nada.
def Check_Cloud_Response(resp):
    if resp != None:
        # {'objeto': 'Luz Dormitorio Fondo', 'accion': 'OFF', 'error': 0, 'message': 'Ok'}
        #logger.info(f"[Check_Cloud_Response] Respuesta de la nube: {resp}")
        if 'error' in resp and resp['error'] == 0:
            if 'accion' in resp and 'objeto' in resp:
                logger.info(f"[Check_Cloud_Response] Acción recibida: {resp['accion']} para el objeto: {resp['objeto']}")
                change_assign_by_name(resp['objeto'], resp['accion'])
    return None

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
            if config.Cloud_Status == 0:
                logger.info(f"[query_cloud] Host {config.Use_host} en línea.")
                config.Cloud_Status = 1  # Marcar como on-line
        else:
            logger.error(f"[query_cloud] [{response.status_code}] en POST a {url}")
            # Cambio de host para el próximo intento
            config.Use_host = (3 - config.Use_host)
            if config.Cloud_Status == 0:
                logger.info(f"[query_cloud] Host Cloud fuera de línea.")
                config.Cloud_Status = 0  # Marcar como off-line
    except Exception as e:
        logger.error(f"[query_cloud] Excepción en POST a {url} [{e}]")
        # Cambio de host para el próximo intento
        config.Use_host = (3 - config.Use_host)
        if config.Cloud_Status == 0:
            logger.info(f"[query_cloud] Host Cloud fuera de línea.")
            config.Cloud_Status = 0  # Marcar como off-line
    
    return Check_Cloud_Response(resp_message)

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

async def tareas_de_assigns():
    logger.debug("[tareas_de_assign]")
    # Mantengo el estado de las salidas de pulso
    mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = (Estado-1) WHERE Estado > 0 AND Tipo = 5;")

async def check_notificar_abm_objetos():
    query_result = mysql_query("SELECT Id AS ASS_Id,Objeto,Tipo,Estado,Icono_Apagado,"
        "Icono_Encendido,Grupo_Visual,Planta,Cord_x,"
        "Cord_y,Coeficiente,Analog_Mult_Div,Analog_Mult_Div_Valor,Flags "
        "FROM TB_DOM_ASSIGN WHERE Id > 0 AND Grupo_Visual > 0 AND Actualizar = 1;")
    if query_result:
        for i in range(0, len(query_result)):
            query_result[i]['System_Key'] = config.System_Key
            logger.info(f"[check_notificar_abm_objetos] Actualizando estado de objeto: {query_result[i]}")
            query_cloud(query_result[i])
            mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Actualizar = 0 WHERE Id = {query_result[i]['ASS_Id']};")
    else:
        query_result = [{"System_Key": config.System_Key}]
        query_cloud(query_result[0])

async def check_notificar_abm_usuario():
    query_result = mysql_query("SELECT Usuario_Cloud AS User_Id, Clave_Cloud AS Clave, Amazon_Key, Google_Key, Apple_Key, Other_Key, Estado from TB_DOM_USER WHERE Actualizar = 1 AND Id > 0;")
    if query_result:
        for i in range(0, len(query_result)):
            if query_result[i]['User_Id'] and query_result[i]['Clave']:
                query_result[i]['System_Key'] = config.System_Key
                logger.info(f"[check_notificar_abm_usuario] Req: {query_result[i]}")
                query_cloud(query_result[i])
                mysql_execute(f"UPDATE TB_DOM_USER SET Actualizar = 0 WHERE Id = {query_result[i]['Id']};")

async def actualizar_usuarios_a_nube():
    logger.info(f"[actualizar_usuarios_a_nube] Actualizando usuarios en la nube")
    query_result = mysql_query("SELECT Usuario_Cloud AS User_Id, Clave_Cloud AS Clave, Amazon_Key, Google_Key, Apple_Key, Other_Key, Estado FROM TB_DOM_USER WHERE Id > 0;")
    if query_result:
        for i in range(0, len(query_result)):
            if query_result[i]['User_Id'] and query_result[i]['Clave']:
                query_result[i]['System_Key'] = config.System_Key
                logger.info(f"[actualizar_usuarios_a_nube] Req: {query_result[i]}")
                query_cloud(query_result[i])

async def actualizar_objetos_a_nube():
    logger.info(f"[actualizar_objetos_a_nube] Actualizando objetos en la nube")
    query_result = mysql_query("SELECT Id AS ASS_Id,Objeto,Tipo,Estado,Icono_Apagado,"
        "Icono_Encendido,Grupo_Visual,Planta,Cord_x,"
        "Cord_y,Coeficiente,Analog_Mult_Div,Analog_Mult_Div_Valor,Flags "
        "FROM TB_DOM_ASSIGN WHERE Id > 0 AND Grupo_Visual > 0;")
    if query_result:
        for i in range(0, len(query_result)):
            query_result[i]['System_Key'] = config.System_Key
            logger.info(f"[actualizar_objetos_a_nube] Actualizando estado de objeto: {query_result[i]}")
            query_cloud(query_result[i])
            mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Actualizar = 0 WHERE Id = {query_result[i]['ASS_Id']};")

def change_assign_by_id(id, accion, parametro=0):
    if accion == 1:
        logger.info(f"[change_assign_by_id] Encender: {id}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = 1, Actualizar = 1 WHERE Id = {id}")
    elif accion == 2:
        logger.info(f"[change_assign_by_id] Apagar: {id}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = 0, Actualizar = 1 WHERE Id = {id}")
    elif accion == 3:
        logger.info(f"[change_assign_by_id] Alternar: {id}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = (1 - Estado), Actualizar = 1 WHERE Id = {id}")
    elif accion == 4:
        if parametro == 0:
            parametro = 1  # Valor por defecto para la duración del pulso
        logger.info(f"[change_assign_by_id] Pulso de: {parametro}s a: {id}")
        mysql_execute(f"UPDATE TB_DOM_ASSIGN SET Estado = (1 + {parametro}), Actualizar = 1 WHERE Id = {id}")
    else:
        logger.warning(f"change_assign_by_id: acción desconocida {accion} para Id={id}")

def change_group_by_id(id, accion, parametro=0):
    query_result = mysql_query(f"SELECT Estado, Listado_Objetos FROM TB_DOM_GROUP WHERE Id = {id};")
    estado_grupo = query_result[0]['Estado']
    objetos = query_result[0]['Listado_Objetos'].split(",")

    if accion == 1:
        logger.info(f"[change_group_by_id] Encender: {id}")
        estado_grupo = 1
    elif accion == 2:
        logger.info(f"[change_group_by_id] Apagar: {id}")
        estado_grupo = 0
    elif accion == 3:
        logger.info(f"[change_group_by_id] Alternar: {id}")
        estado_grupo = 1 - estado_grupo
    elif accion == 4:
        logger.info(f"[change_group_by_id] Pulso de: {parametro}s a: {id} - NO IMPLEMENTADO")

    else:
        logger.warning(f"change_group_by_id: acción desconocida {accion} para Id={id}")

    for obj in objetos:
        if obj:
            if estado_grupo == 1:
                logger.info(f"[change_group_by_id] Encender: {obj}")
                change_assign_by_id(obj, 1)
            elif estado_grupo == 0:
                logger.info(f"[change_group_by_id] Apagar: {obj}")
                change_assign_by_id(obj, 2)

    mysql_execute(f"UPDATE TB_DOM_GROUP SET Estado = {estado_grupo}, Actualizar = 1 WHERE Id = {id};")

    return len(objetos)

async def check_task():
    dias = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa"]
    dia_semana = dias[int(datetime.now().strftime("%w"))]
    mes = datetime.now().strftime("%m")
    dia = datetime.now().strftime("%d")
    hora = datetime.now().strftime("%H")
    minuto = datetime.now().strftime("%M")

    query = (
        "SELECT * FROM TB_DOM_AT WHERE "
        f"((Mes = 0) OR (Mes = {mes})) AND "
        f"((Dia = 0) OR (Dia = {dia})) AND "
        f"((Hora > 23) OR (Hora = {hora})) AND "
        f"((Minuto > 59) OR (Minuto = {minuto})) AND "
        f"((Ultimo_Mes <> {mes}) OR (Ultimo_Dia <> {dia}) OR (Ultima_Hora <> {hora}) OR (Ultimo_Minuto <> {minuto})) AND "
        f"INSTR(Dias_Semana, '{dia_semana}') > 0 ORDER BY Id;"
    )

    query_result = mysql_query(query)

    if query_result:
        for item in query_result:
            id = item.get('Id')
            agenda = item.get('Agenda')
            objeto_destino = item.get('Objeto_Destino')
            grupo_destino = item.get('Grupo_Destino')
            variable_destino = item.get('Variable_Destino')
            evento = item.get('Evento')
            parametro_evento = item.get('Parametro_Evento')
            condicion_variable = item.get('Condicion_Variable')
            condicion_igualdad = item.get('Condicion_Igualdad')
            condicion_valor = item.get('Condicion_Valor')

            if agenda and ( objeto_destino or grupo_destino or variable_destino ) and evento and parametro_evento and condicion_variable and condicion_igualdad and condicion_valor :
                logger.info(f"[check_task] Ejecutando tarea: {agenda}")
                if objeto_destino > 0:
                    change_assign_by_id(objeto_destino, evento, parametro_evento)
                elif grupo_destino > 0:
                    change_group_by_id(grupo_destino, evento, parametro_evento)

            mysql_execute(
                f"UPDATE TB_DOM_AT SET Ultimo_Mes = {mes}, Ultimo_Dia = {dia}, "
                f"Ultima_Hora = {hora}, Ultimo_Minuto = {minuto} WHERE Id = {id};"
            )

async def check_auto():
    dias = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa"]
    tabla_enviar = ["Nada", "Encender", "Apagar", "Cambiar"]
    dia_semana = dias[int(datetime.now().strftime("%w"))]
    mes = datetime.now().strftime("%m")
    dia = datetime.now().strftime("%d")
    hora = datetime.now().strftime("%H")
    minuto = datetime.now().strftime("%M")

    enviar = 0

    query = (
        "SELECT AU.*, ASS.Estado AS Estado_Sensor "
        "FROM TB_DOM_AUTO AS AU, TB_DOM_ASSIGN AS ASS "
        "WHERE AU.Objeto_Sensor = ASS.Id AND AU.Id > 0;"
    )

    query_result = mysql_query(query)

    if query_result:
        for item in query_result:
            id = item.get('Id')

            Id = item.get('Id')
            Objeto = item.get('Objeto')
            Objeto_Salida = item.get('Objeto_Salida')
            Objeto_Sensor = item.get('Objeto_Sensor')
            Grupo_Salida = item.get('Grupo_Salida')
            Particion_Salida = item.get('Particion_Salida')
            Funcion_Salida = item.get('Funcion_Salida')
            Variable_Salida = item.get('Variable_Salida')
            Parametro_Evento = item.get('Parametro_Evento')
            Estado = item.get('Estado')
            Estado_Sensor = item.get('Estado_Sensor')
            Min_Sensor = item.get('Min_Sensor')
            Max_Sensor = item.get('Max_Sensor')
            Habilitado = item.get('Habilitado')
            Hora_Inicio = item.get('Hora_Inicio')
            Minuto_Inicio = item.get('Minuto_Inicio')
            Hora_Fin = item.get('Hora_Fin')
            Minuto_Fin = item.get('Minuto_Fin')
            Dias_Semana = item.get('Dias_Semana')
            Enviar_Max = item.get('Enviar_Max')
            Enviar_Min = item.get('Enviar_Min')

            set_estado = 0
            enviar = 0

            while True:
                # Habiltado   
                #   0 - Apagado
                #   1 - Encendido
                #   2 - Automático
                if Habilitado == 0:
                    if Estado == 1:
                        logger.info(f"[check_auto] Apagar {Objeto} - Apagado forzado")
                        enviar = 2   # apagar
                elif Habilitado == 1:
                    if Estado == 0:
                        logger.info(f"[check_auto] Encender {Objeto} - Encendido forzado")
                        enviar = 1   # encender
                elif Habilitado == 2: 
                    # Automatico
                    dias_configurados = [d.strip() for d in str(Dias_Semana or "").split(",") if d.strip()]
                    if dia_semana not in dias_configurados:
                        if Estado == 1:
                            logger.info(f"[check_auto] Apagar {Objeto} - Fuera de dia de la semana")
                            enviar = 2 # Apagar
                        break
                    # Si hay valores validos en el horario
                    if Hora_Inicio != Hora_Fin or Minuto_Inicio!= Minuto_Fin:
                        # Controlo horario de funcionamiento
                        if Hora_Inicio > Hora_Fin or (Hora_Inicio == Hora_Fin and Minuto_Inicio > Minuto_Fin):
                            # Inicio y Fin en distinto día
                            if(( hora < Hora_Inicio or (hora == Hora_Inicio and minuto < Minuto_Inicio) )
                                and 
                                (hora > Hora_Fin  or  (hora == Hora_Fin and minuto > Minuto_Fin) ) ):
                                # Fuera de horario
                                if Estado == 1:
                                    logger.info(f"[check_auto] Apagar {Objeto} - Fuera de Horario")
                                    enviar = 2 # Apagar
                                break
                        else:
                            # Inicio y Fin en mismo día
                            if(( hora < Hora_Inicio or (hora == Hora_Inicio and minuto < Minuto_Inicio) )
                                or
                                (hora > Hora_Fin  or  (hora == Hora_Fin and minuto > Minuto_Fin) ) ):
                                # Fuera de horario
                                if Estado == 1:
                                    logger.info(f"[check_auto] Apagar {Objeto} - Fuera de Horario")
                                    enviar = 2 # Apagar
                                break
                    # Si hay sensor definido evalúo el estado del sensor
                    if Objeto_Sensor > 0:
                        if Estado == 0 and Estado_Sensor >= Max_Sensor:
                            enviar = Enviar_Max     # Encender o Apagar
                            logger.info(f"[check_auto] {Objeto} -> {tabla_enviar[enviar]}")
                            break;
                        if Estado == 1 and Estado_Sensor <= Min_Sensor:
                            enviar = Enviar_Min     # Encender o Apagar
                            logger.info(f"[check_auto] {Objeto} -> {tabla_enviar[enviar]}")
                            break;
                    else:
                        # No hay sensor definido
                        if Estado == 0:
                            enviar = 1      # Encender
                            logger.info(f"[check_auto] {Objeto} -> {enviar} - Sin sensor")
                            break
                break
            # Si la condicion lo permite ejecuto según corresponda
            if enviar > 0:
                if Objeto_Salida > 0:
                    change_assign_by_id(Objeto_Salida, enviar, Parametro_Evento)
                elif Grupo_Salida > 0:
                    change_group_by_id(Objeto_Salida, enviar, Parametro_Evento)
            #
            if enviar == 1:
                set_estado = 1
            else:
                set_estado = 0
            mysql_execute(f"UPDATE TB_DOM_AUTO SET Estado = {set_estado} WHERE Id = {Id};")

async def worker_loop():
    div_5seg = 0
    div_60seg = 0
    div_3600seg = 3595

    get_system_config()
    
    logger.info(f"System_Key: {config.System_Key}")
    logger.info(f"Cloud_Host_1_Address: {config.Cloud_Host_1_Address}")
    logger.info(f"Cloud_Host_1_Port: {config.Cloud_Host_1_Port}")
    logger.info(f"Cloud_Host_1_Proto: {config.Cloud_Host_1_Proto}")
    logger.info(f"Cloud_Host_2_Address: {config.Cloud_Host_2_Address}")
    logger.info(f"Cloud_Host_2_Port: {config.Cloud_Host_2_Port}")
    logger.info(f"Cloud_Host_2_Proto: {config.Cloud_Host_2_Proto}")

    while True:
        div_5seg += 1
        if div_5seg >= 15:
            div_5seg = 0
            # Cada 15 segundos
            await tareas_de_dispositivos()
            await tareas_de_grupos()
            await check_notificar_abm_usuario()

        div_60seg += 1
        if div_60seg >= 60:
            div_60seg = 0
            # Cada minuto
            await check_task()
            await check_auto()

        div_3600seg += 1
        if div_3600seg >= 3600:
            div_3600seg = 0
            # Cada hora
            await actualizar_usuarios_a_nube()
            await actualizar_objetos_a_nube()

        # Cada segundo
        await check_notificar_abm_objetos()
        await tareas_de_assigns()

        await asyncio.sleep(get_config_value("TASK_INTERVAL", 1))
        