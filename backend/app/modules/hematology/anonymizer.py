"""
Censura de datos PII antes de persistir en la base de datos.

Los PDFs de hemograma IDEXX contienen datos personales del propietario,
nombre de la mascota y veterinario tratante. Estos campos se extraen en
el modulo extractor.py (ver HEADER_PATTERNS) pero NO deben almacenarse
en texto plano en la BD.

Campos censurados:
  - patient_name   (nombre de la mascota + apellido del dueno)
  - pet_owner      (nombre completo del propietario)
  - attending_vet  (nombre del veterinario tratante)

Campos conservados (no identificatorios):
  - species, breed, gender, age, date_receipt, date_result, clinic, location

API publica
-----------
censor(data: dict) -> dict
    Retorna una copia del dict con los campos PII reemplazados.
"""

from __future__ import annotations

import copy

# Campos de metadatos que contienen informacion personal identificable.
# Corresponden a las claves de HEADER_PATTERNS en extractor.py.
_PII_FIELDS = frozenset(
    {
        "patient_name",
        "pet_owner",
        "attending_vet",
    }
)

_REDACTED = "[CENSURADO]"


def censor(data: dict) -> dict:
    """
    Retorna una copia profunda del dict con campos PII reemplazados por '[CENSURADO]'.

    Busca campos PII tanto en el nivel raiz como dentro de la clave 'metadata',
    que es donde el formatter coloca los metadatos del paciente.
    """
    out = copy.deepcopy(data)

    # Nivel raiz
    for field in _PII_FIELDS:
        if field in out and out[field] is not None:
            out[field] = _REDACTED

    # Dentro de metadata (estructura usada por ExtractionResult)
    metadata = out.get("metadata")
    if isinstance(metadata, dict):
        for field in _PII_FIELDS:
            if field in metadata and metadata[field] is not None:
                metadata[field] = _REDACTED

    # Censurar el nombre del archivo si contiene nombres propios
    # (los mock usan nombres como "hemograma_luna_2025.csv")
    filename = out.get("filename")
    if isinstance(filename, str):
        out["filename"] = _censor_filename(filename)

    return out


def _censor_filename(filename: str) -> str:
    """
    Reemplaza la parte identificatoria del nombre de archivo.

    Los archivos reales vienen como 'batch_NNN.pdf' (sin PII). Los mock
    usan nombres como 'hemograma_luna_2025.csv'. Para estos ultimos,
    se reemplaza solo si contiene un patron que parezca un nombre propio
    (letras entre guiones bajos que no son palabras tecnicas comunes).
    """
    # Los archivos reales batch_NNN.pdf no tienen PII, dejarlos intactos.
    if filename.startswith("batch_"):
        return filename

    # Para el resto, preservar solo la extension.
    dot_idx = filename.rfind(".")
    if dot_idx > 0:
        ext = filename[dot_idx:]
        return f"hemograma_anonimo{ext}"
    return "hemograma_anonimo"
