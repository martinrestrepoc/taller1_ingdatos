# Taller 1 - API-Football

El programa consulta los equipos, partidos y clasificacion de la Copa Mundial
2022 usando `requests`. Luego organiza las respuestas con `pandas`.

## Configuracion

Complete estas variables en el archivo `.env`:

```dotenv
API_SPORTS_KEY=su_clave_privada
BASE_URL=https://v3.football.api-sports.io
TEMPORADA=2022
```

## Ejecucion

```bash
uv run python extractor_api.py
```

Las respuestas quedan guardadas en `.cache/api_football` para no repetir
solicitudes. Despues de validar los datos, el programa crea `equipos.parquet`,
`partidos.parquet` y `clasificacion.parquet`.

La competicion utilizada es `league=1` y la temporada es `season=2022`.
