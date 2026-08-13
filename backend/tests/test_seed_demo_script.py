from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_seed_module() -> ModuleType:
    path = PROJECT_ROOT / "scripts" / "seed_demo_data.py"
    spec = importlib.util.spec_from_file_location("seed_demo_data", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


seed = _load_seed_module()


def _assign_pet_ids() -> None:
    for user_index, user in enumerate(seed.USERS):
        for pet_index, pet in enumerate(user.pets):
            pet.pet_id = f"pet-{user_index}-{pet_index}"


def test_demo_profiles_match_the_current_pet_and_map_contracts() -> None:
    zone_pet_counts = Counter()

    for user in seed.USERS:
        zone_pet_counts[user.residence_zone_code] += len(user.pets)
        for pet in user.pets:
            assert pet.sex in {"Hembra", "Macho"}
            payload = seed.pet_payload(user, pet)
            assert payload["residence_consent"] is True
            assert payload["residence_source"] == "catalog"
            assert payload["residence_zone_code"] == user.residence_zone_code

    assert len(zone_pet_counts) == 3
    assert min(zone_pet_counts.values()) >= 3


def test_limited_seed_keeps_assignments_stable_and_covers_every_pet() -> None:
    _assign_pet_ids()
    short = [Path(f"case-{index:03}.pdf") for index in range(12)]
    long = [Path(f"case-{index:03}.pdf") for index in range(36)]

    short_assignment = seed.assign_pdfs_to_pets(short, seed.USERS)
    long_assignment = seed.assign_pdfs_to_pets(long, seed.USERS)
    short_owner = {
        path.name: pet_id
        for pet_id, paths in short_assignment.items()
        for path in paths
    }
    long_owner = {
        path.name: pet_id
        for pet_id, paths in long_assignment.items()
        for path in paths
    }

    assert len(short_owner) == 12
    assert set(short_owner.values()) == set(short_assignment)
    assert all(long_owner[name] == pet_id for name, pet_id in short_owner.items())
    assert min(len(paths) for paths in long_assignment.values()) >= 2


def test_upload_skips_a_filename_already_present_for_the_pet(tmp_path: Path) -> None:
    existing_pdf = tmp_path / "existing.pdf"
    existing_pdf.write_bytes(b"existing hemogram")
    new_pdf = tmp_path / "new.pdf"
    new_pdf.write_bytes(b"new hemogram")
    existing_upload_filename = seed.seed_upload_filename(existing_pdf)

    class FakeApi:
        token: str | None = None

        def __init__(self) -> None:
            self.uploaded: list[tuple[str, str]] = []

        def get_json(self, _path: str):
            return 200, [{"filename": existing_upload_filename}]

        def post_multipart(
            self,
            _path: str,
            file_path: Path,
            *,
            upload_filename: str,
        ):
            self.uploaded.append((file_path.name, upload_filename))
            return 200, {"id": f"analysis-{file_path.stem}"}

    pet = seed.PetSpec(
        name="Luna",
        breed="Mestizo",
        birth_year=2019,
        sex="Hembra",
        weight_kg=18.0,
        pet_id="pet-1",
    )
    user = seed.UserSpec(
        email="demo@hemovet.demo",
        password="known-demo-password",
        full_name="Demo",
        profile="Desarrollo",
        residence_zone_code="do-sd-dn",
        pets=[pet],
        token="token",
    )
    api = FakeApi()

    ids, stats = seed.upload_hemogramas(
        api,
        [user],
        {"pet-1": [existing_pdf, new_pdf]},
    )

    assert api.uploaded == [("new.pdf", seed.seed_upload_filename(new_pdf))]
    assert ids == {"pet-1": ["analysis-new"]}
    assert stats["pet-1"] == {
        "uploaded": 1,
        "skipped": 1,
        "quarantined": 0,
        "failed": 0,
    }
