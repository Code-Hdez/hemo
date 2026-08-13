"""Almacenamiento y validacion segura de fotos de perfil de mascotas."""

from __future__ import annotations

import io
import os
import re
import tempfile
import uuid
import warnings
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


class PetPhotoError(Exception):
    """Error controlado que puede exponerse como respuesta HTTP."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class PetPhotoStore:
    """Normaliza y persiste imagenes en un directorio aislado de la aplicacion."""

    _FORMAT_CONFIG = {
        "JPEG": ("jpg", "JPEG"),
        "PNG": ("png", "PNG"),
        "WEBP": ("webp", "WEBP"),
    }
    _SAFE_KEY = re.compile(r"^[0-9a-f]{32}\.(?:jpg|png|webp)$")
    _MAX_PIXELS = 20_000_000

    def __init__(self, directory: Path, max_bytes: int) -> None:
        self.directory = directory.resolve()
        self.max_bytes = max_bytes
        self.directory.mkdir(parents=True, exist_ok=True)

    async def save(self, upload: UploadFile) -> str:
        """Valida, normaliza y guarda una imagen; retorna una clave publica opaca."""
        content = await upload.read(self.max_bytes + 1)
        if len(content) > self.max_bytes:
            raise PetPhotoError(
                413,
                f"La foto supera el límite de {self.max_bytes // (1024 * 1024)} MiB.",
            )
        if not content:
            raise PetPhotoError(400, "La foto está vacía.")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as probe:
                    detected_format = (probe.format or "").upper()
                    probe.verify()
                if detected_format not in self._FORMAT_CONFIG:
                    raise PetPhotoError(
                        415,
                        "Formato no permitido. Usa una imagen JPG, PNG o WebP.",
                    )
                with Image.open(io.BytesIO(content)) as source:
                    source.load()
                    if source.width * source.height > self._MAX_PIXELS:
                        raise PetPhotoError(400, "La imagen tiene demasiados píxeles.")
                    normalized = ImageOps.exif_transpose(source)
                    encoded = self._encode(normalized, detected_format)
        except PetPhotoError:
            raise
        except (
            Image.DecompressionBombError,
            UnidentifiedImageError,
            OSError,
            ValueError,
        ):
            raise PetPhotoError(400, "El archivo no contiene una imagen válida.")

        extension, _ = self._FORMAT_CONFIG[detected_format]
        key = f"{uuid.uuid4().hex}.{extension}"
        destination = self._path_for(key)
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=".upload-", suffix=f".{extension}", dir=self.directory
        )
        try:
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, destination)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return key

    def delete(self, key: str | None) -> None:
        """Elimina una foto conocida sin permitir traversal de rutas."""
        if not key or not self._SAFE_KEY.fullmatch(key):
            return
        try:
            self._path_for(key).unlink(missing_ok=True)
        except OSError:
            # El registro ya no debe quedar bloqueado por un archivo huerfano.
            return

    def public_url(self, key: str | None) -> str | None:
        return (
            f"/api/v1/media/pets/{key}"
            if key and self._SAFE_KEY.fullmatch(key)
            else None
        )

    def _path_for(self, key: str) -> Path:
        path = (self.directory / key).resolve()
        if path.parent != self.directory:
            raise PetPhotoError(400, "Referencia de foto inválida.")
        return path

    def _encode(self, image: Image.Image, detected_format: str) -> bytes:
        buffer = io.BytesIO()
        _, pillow_format = self._FORMAT_CONFIG[detected_format]
        if pillow_format == "JPEG":
            image.convert("RGB").save(
                buffer, format=pillow_format, quality=90, optimize=True
            )
        elif pillow_format == "PNG":
            image.convert("RGBA").save(buffer, format=pillow_format, optimize=True)
        else:
            mode = "RGBA" if "A" in image.getbands() else "RGB"
            image.convert(mode).save(buffer, format=pillow_format, quality=90, method=4)
        return buffer.getvalue()
