"""
Reescribe `created_at` de los analisis sembrados para distribuirlos
a lo largo de los ultimos 60 dias y dar vida al dashboard temporal.

Diseno:
- Por mascota, se ordenan sus analisis por fecha y se distribuyen
  linealmente entre (hoy - 60 dias) y hoy con jitter de +/- 12h.
- Se actualiza tanto la columna `analyses.created_at` como el campo
  `created_at` dentro del JSON de `analyses.data` (porque el dashboard
  lo consume desde JSON via la API).
- Solo afecta usuarios con dominio @hemovet.demo (los del seed).

Ejecutar dentro del contenedor backend para reutilizar la conexion:
    docker compose exec -T backend python /app/spread_seed_dates.py
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://hemovet:hemovet_dev_2026@db:5432/hemovet",
)

END = datetime(2026, 4, 25, 19, 0, 0)
DAYS = 60
SEED = 20260425


def main() -> None:
    engine = create_engine(DB_URL)
    rng = random.Random(SEED)
    start = END - timedelta(days=DAYS)

    with Session(engine) as s:
        pet_ids = [
            row[0]
            for row in s.execute(text(
                "SELECT DISTINCT a.pet_id FROM analyses a "
                "JOIN users u ON u.id = a.user_id "
                "WHERE u.email LIKE '%@hemovet.demo' AND a.pet_id IS NOT NULL"
            )).all()
        ]
        print(f"mascotas a procesar: {len(pet_ids)}")

        total_updated = 0
        for pid in pet_ids:
            rows = s.execute(text(
                "SELECT id FROM analyses WHERE pet_id = :p ORDER BY created_at"
            ), {"p": pid}).all()
            n = len(rows)
            if n == 0:
                continue
            for i, (aid,) in enumerate(rows):
                frac = i / max(n - 1, 1) if n > 1 else 0.5
                base = start + (END - start) * frac
                jitter = timedelta(hours=rng.uniform(-12, 12),
                                   minutes=rng.randint(0, 59))
                new_dt = base + jitter
                data_str = s.execute(text(
                    "SELECT data FROM analyses WHERE id=:a"
                ), {"a": aid}).scalar()
                try:
                    d = json.loads(data_str)
                except Exception:
                    continue
                d["created_at"] = new_dt.isoformat()
                s.execute(text(
                    "UPDATE analyses SET created_at=:c, data=:d WHERE id=:a"
                ), {
                    "c": new_dt,
                    "d": json.dumps(d, ensure_ascii=False),
                    "a": aid,
                })
                total_updated += 1
            print(f"  pet {pid}: {n} analisis distribuidos")

        # Invalida cualquier metrica cacheada para forzar recomputo
        s.execute(text("DELETE FROM dashboard_metrics"))

        s.commit()
        print(f"Total filas actualizadas: {total_updated}")


if __name__ == "__main__":
    main()
