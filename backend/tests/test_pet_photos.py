from __future__ import annotations

import asyncio
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import queries as db  # noqa: E402
from app.modules.files.storage import PetPhotoStore  # noqa: E402
from app.modules.pets import router as pets_router  # noqa: E402
from app.modules.pets import service as pets_service  # noqa: E402


def _reset_memory_db() -> None:
    os.environ.pop("DATABASE_URL", None)
    db.DATABASE_URL = None
    db._use_db = False
    db._engine = None
    db._memory_users.clear()
    db._memory_pets.clear()
    db._memory_analyses.clear()
    db._memory_breeds.clear()
    db._memory_dashboard_metrics.clear()
    db._memory_epidemiology_events.clear()
    db.init_db()


def _image_bytes(image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 12), color=(12, 85, 140)).save(output, format=image_format)
    return output.getvalue()


class PetPhotoEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_memory_db()
        self.temp_directory = tempfile.TemporaryDirectory()
        self.previous_store = pets_service.photo_store
        pets_service.photo_store = PetPhotoStore(
            Path(self.temp_directory.name), max_bytes=1024
        )
        db.create_user("owner-1", "owner@example.com", "hashed", "Owner")
        db.create_user("other-1", "other@example.com", "hashed", "Other")
        db.create_pet("pet-1", "owner-1", "Luna")

    def tearDown(self) -> None:
        pets_service.photo_store = self.previous_store
        self.temp_directory.cleanup()

    def _upload(
        self, name: str, content: bytes, content_type: str = "image/png"
    ) -> dict:
        source = tempfile.SpooledTemporaryFile()
        source.write(content)
        source.seek(0)
        return asyncio.run(
            pets_router.upload_pet_photo(
                "pet-1",
                file=UploadFile(
                    filename=name, file=source, headers={"content-type": content_type}
                ),
                user_id="owner-1",
            )
        )

    def test_upload_replaces_photo_and_exposes_only_a_public_url(self) -> None:
        payload = self._upload("luna.png", _image_bytes())

        self.assertRegex(
            payload["photo_url"], r"^/api/v1/media/pets/[0-9a-f]{32}\.png$"
        )
        self.assertNotIn("profile_photo_key", payload)
        self.assertTrue(any(Path(self.temp_directory.name).iterdir()))

        replacement = self._upload("luna.webp", _image_bytes("WEBP"), "image/webp")
        self.assertEqual(len(list(Path(self.temp_directory.name).glob("*"))), 1)
        self.assertTrue(replacement["photo_url"].endswith(".webp"))

    def test_rejects_invalid_and_oversized_files(self) -> None:
        with self.assertRaises(HTTPException) as invalid:
            self._upload("not-an-image.png", b"not an image")
        self.assertEqual(invalid.exception.status_code, 400)

        with self.assertRaises(HTTPException) as oversized:
            self._upload("large.png", b"a" * 1025)
        self.assertEqual(oversized.exception.status_code, 413)

        with self.assertRaises(HTTPException) as unsupported:
            self._upload("bitmap.bmp", _image_bytes("BMP"), "image/bmp")
        self.assertEqual(unsupported.exception.status_code, 415)

    def test_remove_photo_and_owner_protection(self) -> None:
        self._upload("luna.jpg", _image_bytes("JPEG"), "image/jpeg")

        with self.assertRaises(HTTPException) as forbidden:
            pets_router.delete_pet_photo("pet-1", user_id="other-1")
        self.assertEqual(forbidden.exception.status_code, 404)

        removed = pets_router.delete_pet_photo("pet-1", user_id="owner-1")
        self.assertIsNone(removed["photo_url"])
        self.assertEqual(list(Path(self.temp_directory.name).glob("*")), [])


if __name__ == "__main__":
    unittest.main()
