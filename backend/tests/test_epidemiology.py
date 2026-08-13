from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import queries as db  # noqa: E402
from app.modules.population_surveillance.service import (  # noqa: E402
    build_events_for_analysis,
    get_epidemiology_points,
    sync_events_for_pet,
)  # noqa: E402
from app.modules.maps.service import build_pet_residence_fields  # noqa: E402


def _reset_memory_db() -> None:
    os.environ.pop("DATABASE_URL", None)
    db.DATABASE_URL = None
    db._use_db = False
    db._engine = None
    db._memory_analyses.clear()
    db._memory_users.clear()
    db._memory_pets.clear()
    db._memory_breeds.clear()
    db._memory_dashboard_metrics.clear()
    db._memory_epidemiology_events.clear()
    db.init_db()


def _analysis_payload(analysis_id: str, findings: list[dict] | None = None) -> dict:
    return {
        "id": analysis_id,
        "created_at": datetime.now().isoformat(),
        "location": "Distrito Nacional",
        "latitude": 18.4861,
        "longitude": -69.9312,
        "findings": findings
        or [
            {
                "label": "Patron inflamatorio",
                "detail": "Neutrofilia",
                "severity": "danger",
            },
            {"label": "Leucograma de estres", "detail": "Cortisol", "severity": "info"},
        ],
    }


class EpidemiologyTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_memory_db()

    def test_pet_residence_fields_store_zone_not_address(self) -> None:
        fields = build_pet_residence_fields(zone_code="do-stgo-santiago", consent=True)
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
            **fields,
        )

        self.assertEqual(pet["residence_zone_code"], "do-stgo-santiago")
        self.assertEqual(pet["residence_label"], "Santiago")
        self.assertTrue(pet["residence_consent"])
        self.assertNotIn("address", pet)

    def test_pin_residence_fields_store_aggregated_grid_not_exact_coordinates(
        self,
    ) -> None:
        fields = build_pet_residence_fields(
            zone_code=None,
            lat=19.4601,
            lng=-70.6912,
            source="pin",
            consent=True,
        )

        self.assertTrue(fields["residence_zone_code"].startswith("do-grid-"))
        self.assertEqual(fields["residence_precision"], "grid_2km")
        self.assertNotEqual(fields["residence_lat"], 19.4601)
        self.assertNotEqual(fields["residence_lng"], -70.6912)
        self.assertNotIn("address", fields)

    def test_analysis_with_consented_pet_creates_aggregated_points(self) -> None:
        fields = build_pet_residence_fields(zone_code="do-stgo-santiago", consent=True)
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
            **fields,
        )
        analysis = _analysis_payload("analysis-1")
        events = build_events_for_analysis(analysis, pet)
        db.save_epidemiology_events(events)

        points = get_epidemiology_points(period_days=90, min_count=1, min_pet_count=1)

        self.assertEqual(len(points), 1)
        self.assertTrue(points[0].zone_label.startswith("Santiago - zona "))
        self.assertNotEqual(points[0].lat, fields["residence_lat"])
        self.assertNotEqual(points[0].lng, fields["residence_lng"])
        self.assertEqual(points[0].count, 1)
        self.assertEqual(points[0].report_count, 1)
        self.assertEqual(points[0].pet_count, 1)
        self.assertEqual(points[0].intensity_level, "low")
        self.assertIn(
            points[0].finding, {"Patron inflamatorio", "Leucograma de estres"}
        )

    def test_three_reports_from_same_pet_do_not_activate_default_public_map(
        self,
    ) -> None:
        fields = build_pet_residence_fields(zone_code="do-stgo-santiago", consent=True)
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
            **fields,
        )
        for idx, label in enumerate(["PLT bajo", "NEU alto", "HCT limite"], start=1):
            analysis = _analysis_payload(
                f"analysis-{idx}",
                findings=[{"label": label, "detail": label, "severity": "warn"}],
            )
            db.save_epidemiology_events(build_events_for_analysis(analysis, pet))

        points = get_epidemiology_points(period_days=90, min_count=3)

        self.assertEqual(points, [])

    def test_nearby_pet_residences_merge_into_one_public_zone(self) -> None:
        for idx, (lat, lng) in enumerate(
            [(19.4601, -70.6912), (19.4682, -70.6880), (19.4625, -70.6835)], start=1
        ):
            fields = build_pet_residence_fields(
                zone_code=None,
                lat=lat,
                lng=lng,
                source="pin",
                consent=True,
            )
            pet = db.create_pet(
                pet_id=f"pet-{idx}",
                owner_id="user-1",
                name=f"Mascota {idx}",
                **fields,
            )
            analysis = _analysis_payload(
                f"analysis-{idx}",
                findings=[
                    {
                        "label": f"Hallazgo {idx}",
                        "detail": "Detalle",
                        "severity": "warn",
                    }
                ],
            )
            db.save_epidemiology_events(build_events_for_analysis(analysis, pet))

        points = get_epidemiology_points(period_days=90, min_count=3, min_pet_count=3)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].count, 3)
        self.assertEqual(points[0].pet_count, 3)
        self.assertEqual(points[0].intensity_level, "low")

    def test_three_severe_reports_are_not_high_intensity_by_themselves(self) -> None:
        for idx in range(1, 4):
            fields = build_pet_residence_fields(
                zone_code=None,
                lat=19.4601 + (idx * 0.002),
                lng=-70.6912,
                source="pin",
                consent=True,
            )
            pet = db.create_pet(
                pet_id=f"pet-{idx}",
                owner_id="user-1",
                name=f"Mascota {idx}",
                **fields,
            )
            analysis = _analysis_payload(
                f"analysis-{idx}",
                findings=[
                    {
                        "label": "Patron inflamatorio",
                        "detail": "Detalle",
                        "severity": "danger",
                    }
                ],
            )
            db.save_epidemiology_events(build_events_for_analysis(analysis, pet))

        points = get_epidemiology_points(period_days=90, min_count=3, min_pet_count=3)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].intensity_level, "low")

    def test_repeated_reports_from_three_pets_remain_initial_signal(self) -> None:
        for pet_idx in range(1, 4):
            fields = build_pet_residence_fields(
                zone_code=None,
                lat=19.4601 + (pet_idx * 0.001),
                lng=-70.6912,
                source="pin",
                consent=True,
            )
            pet = db.create_pet(
                pet_id=f"pet-{pet_idx}",
                owner_id="user-1",
                name=f"Mascota {pet_idx}",
                **fields,
            )
            for analysis_idx in range(1, 5):
                analysis = _analysis_payload(
                    f"analysis-{pet_idx}-{analysis_idx}",
                    findings=[
                        {
                            "label": "Patron inflamatorio",
                            "detail": "Detalle",
                            "severity": "danger",
                        }
                    ],
                )
                db.save_epidemiology_events(build_events_for_analysis(analysis, pet))

        points = get_epidemiology_points(period_days=90, min_count=3, min_pet_count=3)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].count, 12)
        self.assertEqual(points[0].pet_count, 3)
        self.assertEqual(points[0].intensity_level, "low")

    def test_high_intensity_requires_broad_participation_or_many_reports(self) -> None:
        for idx in range(1, 9):
            fields = build_pet_residence_fields(
                zone_code=None,
                lat=19.4601 + (idx * 0.001),
                lng=-70.6912,
                source="pin",
                consent=True,
            )
            pet = db.create_pet(
                pet_id=f"pet-{idx}",
                owner_id="user-1",
                name=f"Mascota {idx}",
                **fields,
            )
            analysis = _analysis_payload(
                f"analysis-{idx}",
                findings=[
                    {
                        "label": "Patron inflamatorio",
                        "detail": "Detalle",
                        "severity": "warn",
                    }
                ],
            )
            db.save_epidemiology_events(build_events_for_analysis(analysis, pet))

        points = get_epidemiology_points(period_days=90, min_count=3, min_pet_count=3)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].pet_count, 8)
        self.assertEqual(points[0].intensity_level, "high")

    def test_analysis_location_from_scan_does_not_create_map_events_without_residence(
        self,
    ) -> None:
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
        )
        analysis = _analysis_payload("analysis-1")

        events = build_events_for_analysis(analysis, pet)
        db.save_epidemiology_events(events)

        self.assertEqual(events, [])
        self.assertEqual(
            get_epidemiology_points(period_days=90, min_count=1, min_pet_count=1), []
        )

    def test_privacy_threshold_suppresses_low_count_zones(self) -> None:
        fields = build_pet_residence_fields(zone_code="do-stgo-santiago", consent=True)
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
            **fields,
        )
        db.save_epidemiology_events(
            build_events_for_analysis(_analysis_payload("analysis-1"), pet)
        )

        points = get_epidemiology_points(period_days=90, min_count=3, min_pet_count=1)

        self.assertEqual(points, [])

    def test_pet_residence_sync_rebuilds_and_removes_existing_analysis_events(
        self,
    ) -> None:
        pet = db.create_pet(
            pet_id="pet-1",
            owner_id="user-1",
            name="Luna",
        )
        analysis = _analysis_payload("analysis-1")
        db.save_analysis(analysis, user_id="user-1", pet_id="pet-1")
        self.assertEqual(
            sync_events_for_pet(
                pet, db.list_analysis_records_for_user("user-1", pet_id="pet-1")
            ),
            0,
        )

        fields = build_pet_residence_fields(zone_code="do-stgo-santiago", consent=True)
        pet = db.update_pet("pet-1", **fields)
        self.assertEqual(
            sync_events_for_pet(
                pet, db.list_analysis_records_for_user("user-1", pet_id="pet-1")
            ),
            2,
        )
        self.assertEqual(
            len(get_epidemiology_points(period_days=90, min_count=1, min_pet_count=1)),
            1,
        )

        pet = db.update_pet(
            "pet-1", **build_pet_residence_fields(zone_code=None, consent=False)
        )
        self.assertEqual(
            sync_events_for_pet(
                pet, db.list_analysis_records_for_user("user-1", pet_id="pet-1")
            ),
            0,
        )
        self.assertEqual(
            get_epidemiology_points(period_days=90, min_count=1, min_pet_count=1), []
        )


if __name__ == "__main__":
    unittest.main()
