"""Extrae y normaliza datos de la Copa Mundial desde API-Football."""

import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv


# Cargar las variables guardadas en el archivo .env.
load_dotenv()

API_KEY = os.getenv("API_SPORTS_KEY")
BASE_URL = os.getenv("BASE_URL", "https://v3.football.api-sports.io")

COMPETENCIA_ID = 1
TEMPORADA = 2022
CARPETA_CACHE = ".cache/api_football"
CARPETA_SALIDA = os.getenv("CARPETA_SALIDA", ".")

COLUMNAS_EQUIPOS = [
    "equipo_id", "nombre_equipo", "codigo_equipo", "pais", "anio_fundacion",
    "es_seleccion_nacional", "logo_url", "competencia_id", "temporada",
    "fecha_extraccion", "endpoint_origen",
]

COLUMNAS_PARTIDOS = [
    "partido_id", "competencia_id", "competencia_nombre", "temporada", "ronda",
    "fecha_partido", "zona_horaria", "estado_partido", "minuto_transcurrido",
    "arbitro", "estadio_id", "estadio_nombre", "estadio_ciudad",
    "equipo_local_id", "equipo_local_nombre", "equipo_visitante_id",
    "equipo_visitante_nombre", "gano_local", "gano_visitante", "goles_local",
    "goles_visitante", "penales_local", "penales_visitante", "fecha_extraccion",
    "endpoint_origen",
]

COLUMNAS_CLASIFICACION = [
    "grupo", "posicion", "equipo_id", "nombre_equipo", "puntos",
    "partidos_jugados", "partidos_ganados", "partidos_empatados",
    "partidos_perdidos", "goles_favor", "goles_contra", "diferencia_gol",
    "forma_reciente", "estado_clasificacion", "descripcion_clasificacion",
    "fecha_actualizacion", "competencia_id", "temporada", "fecha_extraccion",
    "endpoint_origen",
]


def consultar_api(endpoint):
    """Consulta un endpoint y guarda una copia para no repetir la solicitud."""
    os.makedirs(CARPETA_CACHE, exist_ok=True)
    nombre_archivo = f"{endpoint}_{COMPETENCIA_ID}_{TEMPORADA}.json"
    ruta_cache = os.path.join(CARPETA_CACHE, nombre_archivo)

    # Si ya se hizo la consulta, se usan los datos guardados.
    if os.path.exists(ruta_cache):
        with open(ruta_cache, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    headers = {"x-apisports-key": API_KEY}
    params = {"league": COMPETENCIA_ID, "season": TEMPORADA}

    respuesta = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        params=params,
        timeout=30,
    )

    if respuesta.status_code != 200:
        raise Exception(
            f"Error {respuesta.status_code} al consultar el endpoint /{endpoint}"
        )

    datos = respuesta.json()

    if datos.get("errors"):
        raise Exception(f"La API devolvio un error: {datos['errors']}")

    registros = datos.get("response", [])

    # Algunos endpoints pueden tener mas de una pagina.
    total_paginas = datos.get("paging", {}).get("total", 1)

    for pagina in range(2, total_paginas + 1):
        params["page"] = pagina
        respuesta = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            params=params,
            timeout=30,
        )

        if respuesta.status_code != 200:
            raise Exception(
                f"Error {respuesta.status_code} en la pagina {pagina} de /{endpoint}"
            )

        datos_pagina = respuesta.json()

        if datos_pagina.get("errors"):
            raise Exception(f"La API devolvio un error: {datos_pagina['errors']}")

        registros.extend(datos_pagina.get("response", []))

    with open(ruta_cache, "w", encoding="utf-8") as archivo:
        json.dump(registros, archivo, ensure_ascii=False, indent=2)

    return registros


def normalizar_equipos(datos, fecha_extraccion):
    """Convierte la respuesta de /teams en una tabla de pandas."""
    filas = []

    for registro in datos:
        equipo = registro.get("team", {})

        filas.append(
            {
                "equipo_id": equipo.get("id"),
                "nombre_equipo": equipo.get("name"),
                "codigo_equipo": equipo.get("code"),
                "pais": equipo.get("country"),
                "anio_fundacion": equipo.get("founded"),
                "es_seleccion_nacional": equipo.get("national"),
                "logo_url": equipo.get("logo"),
                "competencia_id": COMPETENCIA_ID,
                "temporada": TEMPORADA,
                "fecha_extraccion": fecha_extraccion,
                "endpoint_origen": "/teams",
            }
        )

    equipos = pd.DataFrame(filas, columns=COLUMNAS_EQUIPOS)

    if not equipos.empty:
        equipos = equipos.drop_duplicates(subset="equipo_id").reset_index(drop=True)
        equipos["equipo_id"] = equipos["equipo_id"].astype("Int64")
        equipos["anio_fundacion"] = equipos["anio_fundacion"].astype("Int64")
        equipos["competencia_id"] = equipos["competencia_id"].astype("Int64")
        equipos["temporada"] = equipos["temporada"].astype("Int64")

    return equipos


def normalizar_partidos(datos, fecha_extraccion):
    """Convierte la respuesta de /fixtures en una tabla de pandas."""
    filas = []

    for registro in datos:
        fixture = registro.get("fixture", {})
        liga = registro.get("league", {})
        equipos = registro.get("teams", {})
        local = equipos.get("home", {})
        visitante = equipos.get("away", {})
        goles = registro.get("goals", {})
        marcador = registro.get("score", {})
        penales = marcador.get("penalty") or {}
        estado = fixture.get("status", {})
        estadio = fixture.get("venue", {})

        filas.append(
            {
                "partido_id": fixture.get("id"),
                "competencia_id": liga.get("id"),
                "competencia_nombre": liga.get("name"),
                "temporada": liga.get("season"),
                "ronda": liga.get("round"),
                "fecha_partido": fixture.get("date"),
                "zona_horaria": fixture.get("timezone"),
                "estado_partido": estado.get("long"),
                "minuto_transcurrido": estado.get("elapsed"),
                "arbitro": fixture.get("referee"),
                "estadio_id": estadio.get("id"),
                "estadio_nombre": estadio.get("name"),
                "estadio_ciudad": estadio.get("city"),
                "equipo_local_id": local.get("id"),
                "equipo_local_nombre": local.get("name"),
                "equipo_visitante_id": visitante.get("id"),
                "equipo_visitante_nombre": visitante.get("name"),
                "gano_local": local.get("winner"),
                "gano_visitante": visitante.get("winner"),
                "goles_local": goles.get("home"),
                "goles_visitante": goles.get("away"),
                "penales_local": penales.get("home"),
                "penales_visitante": penales.get("away"),
                "fecha_extraccion": fecha_extraccion,
                "endpoint_origen": "/fixtures",
            }
        )

    partidos = pd.DataFrame(filas, columns=COLUMNAS_PARTIDOS)

    if not partidos.empty:
        partidos = partidos.drop_duplicates(subset="partido_id").reset_index(drop=True)
        columnas_numericas = [
            "partido_id", "competencia_id", "temporada", "minuto_transcurrido",
            "estadio_id", "equipo_local_id", "equipo_visitante_id", "goles_local",
            "goles_visitante", "penales_local", "penales_visitante",
        ]
        for columna in columnas_numericas:
            partidos[columna] = pd.to_numeric(
                partidos[columna], errors="coerce"
            ).astype("Int64")
        partidos["fecha_partido"] = pd.to_datetime(
            partidos["fecha_partido"], errors="coerce", utc=True
        )

    return partidos


def normalizar_clasificacion(datos, fecha_extraccion):
    """Convierte la respuesta de /standings en una tabla de pandas."""
    filas = []

    for registro in datos:
        liga = registro.get("league", {})
        grupos = liga.get("standings", [])

        for grupo in grupos:
            for posicion in grupo:
                equipo = posicion.get("team", {})
                partidos = posicion.get("all", {})
                goles = partidos.get("goals", {})

                filas.append(
                    {
                        "grupo": posicion.get("group"),
                        "posicion": posicion.get("rank"),
                        "equipo_id": equipo.get("id"),
                        "nombre_equipo": equipo.get("name"),
                        "puntos": posicion.get("points"),
                        "partidos_jugados": partidos.get("played"),
                        "partidos_ganados": partidos.get("win"),
                        "partidos_empatados": partidos.get("draw"),
                        "partidos_perdidos": partidos.get("lose"),
                        "goles_favor": goles.get("for"),
                        "goles_contra": goles.get("against"),
                        "diferencia_gol": posicion.get("goalsDiff"),
                        "forma_reciente": posicion.get("form"),
                        "estado_clasificacion": posicion.get("status"),
                        "descripcion_clasificacion": posicion.get("description"),
                        "fecha_actualizacion": posicion.get("update"),
                        "competencia_id": liga.get("id", COMPETENCIA_ID),
                        "temporada": liga.get("season", TEMPORADA),
                        "fecha_extraccion": fecha_extraccion,
                        "endpoint_origen": "/standings",
                    }
                )

    clasificacion = pd.DataFrame(filas, columns=COLUMNAS_CLASIFICACION)

    if not clasificacion.empty:
        clasificacion = clasificacion.drop_duplicates(
            subset=["grupo", "equipo_id"]
        ).reset_index(drop=True)
        columnas_numericas = [
            "posicion", "equipo_id", "puntos", "partidos_jugados",
            "partidos_ganados", "partidos_empatados", "partidos_perdidos",
            "goles_favor", "goles_contra", "diferencia_gol",
            "competencia_id", "temporada",
        ]
        for columna in columnas_numericas:
            clasificacion[columna] = pd.to_numeric(
                clasificacion[columna], errors="coerce"
            ).astype("Int64")
        clasificacion["fecha_actualizacion"] = pd.to_datetime(
            clasificacion["fecha_actualizacion"], errors="coerce", utc=True
        )

    return clasificacion


def validar_dataframe(datos, nombre, columnas_esperadas, columnas_clave):
    """Comprueba el esquema, los datos vacios y los registros duplicados."""
    if datos.empty:
        raise Exception(f"El archivo {nombre} no tiene registros")

    if list(datos.columns) != columnas_esperadas:
        raise Exception(f"Las columnas de {nombre} no coinciden con el enunciado")

    if datos[columnas_clave].isnull().any().any():
        raise Exception(f"{nombre} tiene valores nulos en su columna identificadora")

    if datos.duplicated(subset=columnas_clave).any():
        raise Exception(f"{nombre} tiene registros duplicados")


def guardar_parquet(equipos, partidos, clasificacion):
    """Valida y guarda los tres archivos Parquet requeridos."""
    validar_dataframe(
        equipos, "equipos.parquet", COLUMNAS_EQUIPOS, ["equipo_id"]
    )
    validar_dataframe(
        partidos, "partidos.parquet", COLUMNAS_PARTIDOS, ["partido_id"]
    )
    validar_dataframe(
        clasificacion,
        "clasificacion.parquet",
        COLUMNAS_CLASIFICACION,
        ["grupo", "equipo_id"],
    )

    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    equipos.to_parquet(os.path.join(CARPETA_SALIDA, "equipos.parquet"), index=False)
    partidos.to_parquet(os.path.join(CARPETA_SALIDA, "partidos.parquet"), index=False)
    clasificacion.to_parquet(
        os.path.join(CARPETA_SALIDA, "clasificacion.parquet"), index=False
    )


def extraer_datos():
    """Consulta los tres endpoints y devuelve los DataFrames normalizados."""
    if not API_KEY:
        raise Exception("Falta API_SPORTS_KEY en el archivo .env")

    fecha_extraccion = datetime.now(timezone.utc)

    datos_equipos = consultar_api("teams")
    datos_partidos = consultar_api("fixtures")
    datos_clasificacion = consultar_api("standings")

    equipos = normalizar_equipos(datos_equipos, fecha_extraccion)
    partidos = normalizar_partidos(datos_partidos, fecha_extraccion)
    clasificacion = normalizar_clasificacion(
        datos_clasificacion, fecha_extraccion
    )

    return equipos, partidos, clasificacion


def main():
    equipos, partidos, clasificacion = extraer_datos()
    guardar_parquet(equipos, partidos, clasificacion)

    print(f"Equipos normalizados: {len(equipos)}")
    print(f"Partidos normalizados: {len(partidos)}")
    print(f"Registros de clasificacion: {len(clasificacion)}")
    print(f"Archivos Parquet guardados en: {os.path.abspath(CARPETA_SALIDA)}")


if __name__ == "__main__":
    main()
