"""
Resolución de coordenadas geográficas para provincias y ciudades de República Dominicana.

Convierte el campo `location` extraído del PDF (nombre de clínica/ciudad) en coordenadas
lat/lng aproximadas usando coincidencia parcial de texto.

API pública
-----------
resolve_location(location_str: str) -> tuple[float, float] | None
    Retorna (lat, lng) si encuentra coincidencia, None si no.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tabla de provincias y ciudades principales de República Dominicana
# Coordenadas aproximadas al centroide de cada municipio/provincia
# ---------------------------------------------------------------------------
_DR_LOCATIONS: dict[str, tuple[float, float]] = {
    # Región Cibao
    "santiago": (19.4517, -70.6970),
    "la vega": (19.2196, -70.5300),
    "moca": (19.3922, -70.5233),
    "puerto plata": (19.7930, -70.6911),
    "sosua": (19.7614, -70.5139),
    "cabarete": (19.7648, -70.4096),
    "nagua": (19.3769, -69.8477),
    "san francisco de macoris": (19.3003, -70.2527),
    "cotui": (19.0567, -70.1511),
    "bonao": (18.9397, -70.4081),
    "constanza": (18.9067, -70.7383),
    "jarabacoa": (19.1208, -70.6375),
    "moncion": (19.4078, -71.1519),
    "san jose de las matas": (19.3333, -70.9333),
    "mao": (19.5555, -71.0775),
    "dajabon": (19.5492, -71.7081),
    "monte cristi": (19.8567, -71.6503),
    # Región Este
    "santo domingo": (18.4861, -69.9312),
    "santo domingo este": (18.4800, -69.8600),
    "santo domingo norte": (18.5500, -69.9500),
    "santo domingo oeste": (18.5000, -70.0300),
    "los alcarrizos": (18.5142, -70.0517),
    "san cristobal": (18.4158, -70.1083),
    "san pedro de macoris": (18.4534, -69.3047),
    "la romana": (18.4273, -68.9728),
    "higuey": (18.6153, -68.7078),
    "punta cana": (18.5821, -68.4059),
    "boca chica": (18.4500, -69.6000),
    "san isidro": (18.5028, -69.7711),
    "guerra": (18.5600, -69.8700),
    "pedro brand": (18.5703, -69.9981),
    "villa mella": (18.5700, -69.9700),
    "hato mayor": (18.7622, -69.2597),
    "el seibo": (18.7658, -69.0378),
    # Región Sur
    "bani": (18.2789, -70.3322),
    "azua": (18.4525, -70.7347),
    "san juan de la maguana": (18.8061, -71.2289),
    "barahona": (18.2094, -71.1022),
    "neiba": (18.4883, -71.4200),
    "bahoruco": (18.4900, -71.4100),
    "pedernales": (18.0378, -71.7428),
    "neyba": (18.4883, -71.4200),
    "tamayo": (18.4831, -71.1253),
    # Región Nordeste
    "samana": (19.2097, -69.3356),
    "las terrenas": (19.3061, -69.5328),
    "el limon": (19.2800, -69.4800),
    # Región Noroeste
    "valverde": (19.5872, -70.9950),
    "monte plata": (18.8069, -69.7883),
    "seybo": (18.7658, -69.0378),
}


def resolve_location(location_str: str) -> tuple[float, float] | None:
    """
    Busca coincidencia parcial (case-insensitive) entre `location_str` y las
    entradas del diccionario de provincias/ciudades de RD.

    Retorna (lat, lng) si encuentra coincidencia, None si no.
    """
    if not location_str:
        return None

    normalized = location_str.lower().strip()

    # Búsqueda por subcadena: el nombre de la ciudad aparece dentro del location_str
    for city_key, coords in _DR_LOCATIONS.items():
        if city_key in normalized:
            return coords

    # Búsqueda inversa: alguna palabra del location_str aparece en las claves
    words = [w for w in normalized.split() if len(w) >= 4]
    for word in words:
        for city_key, coords in _DR_LOCATIONS.items():
            if word in city_key:
                return coords

    return None
