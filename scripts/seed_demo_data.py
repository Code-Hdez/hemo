"""
Seed de datos demo para HemoVet.

Crea 3 usuarios con sus mascotas, asegura una señal epidemiológica demo por
mascota y sube los hemogramas de `test/` distribuidos entre ellas, usando
exclusivamente la API REST pública. Las mascotas se agrupan en tres zonas
dominicanas con al menos tres mascotas por zona para que el mapa satisfaga su
umbral de privacidad sin reducirlo.

Uso:
    python3 scripts/seed_demo_data.py [--api http://localhost:8000] [--limit N]

Idempotente: reutiliza usuarios y mascotas existentes, actualiza el perfil de
las mascotas demo y omite los PDFs que ya estén en el historial asignado.
Las credenciales son públicas y este script solo debe usarse en desarrollo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "test"

# --- Definicion de usuarios y mascotas demo ----------------------------------

@dataclass
class PetSpec:
    name: str
    breed: str
    birth_year: int
    sex: str
    weight_kg: float
    notes: str = ""
    weight_share: int = 1  # peso relativo en la asignacion de hemogramas
    pet_id: str = ""       # rellenado tras crear


@dataclass
class UserSpec:
    email: str
    password: str
    full_name: str
    profile: str
    residence_zone_code: str
    pets: list[PetSpec] = field(default_factory=list)
    user_id: str = ""
    token: str = ""


USERS: list[UserSpec] = [
    UserSpec(
        email="maria.fernandez@hemovet.demo",
        password="HemoVet2026!",
        full_name="Maria Fernandez",
        profile="Veterinaria de pequeños animales con foco en rescates urbanos (Santo Domingo).",
        residence_zone_code="do-sd-dn",
        pets=[
            PetSpec(
                "Luna",
                "Mestizo",
                2019,
                "Hembra",
                18.0,
                "Rescate. Control trimestral.",
                weight_share=4,
            ),
            PetSpec(
                "Toby",
                "Mestizo",
                2017,
                "Macho",
                22.0,
                "Rescate adulto. Historial alérgico.",
                weight_share=4,
            ),
            PetSpec(
                "Nina",
                "Beagle",
                2021,
                "Hembra",
                12.0,
                "Joven, control de crecimiento.",
                weight_share=3,
            ),
            PetSpec(
                "Rocco",
                "Pitbull",
                2018,
                "Macho",
                28.0,
                "Rescate. Seguimiento cardiológico.",
                weight_share=3,
            ),
            PetSpec(
                "Pepa",
                "Mestizo",
                2014,
                "Hembra",
                15.0,
                "Geriátrica. Monitoreo renal.",
                weight_share=4,
            ),
        ],
    ),
    UserSpec(
        email="carlos.ramirez@hemovet.demo",
        password="HemoVet2026!",
        full_name="Carlos Ramirez",
        profile="Tutor de razas grandes (Pastor Alemán, Labrador, Golden) en Santiago.",
        residence_zone_code="do-stgo-santiago",
        pets=[
            PetSpec(
                "Zeus",
                "Pastor Alemán",
                2016,
                "Macho",
                35.0,
                "Chequeos preventivos.",
                weight_share=4,
            ),
            PetSpec(
                "Hera",
                "Pastor Alemán",
                2019,
                "Hembra",
                30.0,
                "Control veterinario periódico.",
                weight_share=3,
            ),
            PetSpec(
                "Apolo",
                "Labrador Retriever",
                2020,
                "Macho",
                32.0,
                "Activo, dieta deportiva.",
                weight_share=3,
            ),
            PetSpec(
                "Atenea",
                "Golden Retriever",
                2018,
                "Hembra",
                28.0,
                "Predisposición a displasia.",
                weight_share=3,
            ),
        ],
    ),
    UserSpec(
        email="lucia.torres@hemovet.demo",
        password="HemoVet2026!",
        full_name="Lucia Torres",
        profile="Tutora de razas pequeñas residente en La Vega.",
        residence_zone_code="do-vega-la-vega",
        pets=[
            PetSpec(
                "Coco",
                "Chihuahua",
                2019,
                "Hembra",
                3.2,
                "Cardiopatía congénita leve.",
                weight_share=3,
            ),
            PetSpec(
                "Bruno",
                "Pug",
                2017,
                "Macho",
                8.5,
                "Braquicéfalo. Sobrepeso.",
                weight_share=3,
            ),
            PetSpec(
                "Mia",
                "Poodle",
                2022,
                "Hembra",
                6.0,
                "Joven. Controles preventivos.",
                weight_share=2,
            ),
        ],
    ),
]

# --- Cliente HTTP minimo via urllib ------------------------------------------

class ApiClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.token: str | None = None

    def _request(self, method: str, path: str, *, headers: dict | None = None,
                 data: bytes | None = None, expect_json: bool = True):
        url = f"{self.base}{path}"
        req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                return resp.status, json.loads(body) if expect_json and body else body
        except urllib.error.HTTPError as e:
            payload = e.read()
            try:
                payload = json.loads(payload)
            except Exception:
                pass
            return e.code, payload

    def post_json(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        return self._request("POST", path, headers={"Content-Type": "application/json"}, data=data)

    def put_json(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        return self._request("PUT", path, headers={"Content-Type": "application/json"}, data=data)

    def get_json(self, path: str):
        return self._request("GET", path)

    def post_form(self, path: str, fields: dict):
        body = urllib.parse.urlencode(fields).encode("utf-8")
        return self._request(
            "POST", path,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=body,
        )

    def post_multipart(
        self,
        path: str,
        file_path: Path,
        *,
        upload_filename: str | None = None,
    ):
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        with open(file_path, "rb") as f:
            content = f.read()
        safe_filename = upload_filename or file_path.name
        body = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{safe_filename}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        return self._request(
            "POST", path,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            data=body,
        )

# --- Pasos del seed -----------------------------------------------------------

def ensure_user(api: ApiClient, user: UserSpec) -> None:
    api.token = None
    code, body = api.post_json("/api/v1/auth/register", {
        "email": user.email,
        "password": user.password,
        "full_name": user.full_name,
    })
    if code == 201:
        user.user_id = body["id"]
        print(f"  + usuario creado: {user.email} ({user.user_id})")
    elif code == 409:
        print(f"  ~ usuario ya existe: {user.email}, haciendo login")
    else:
        raise RuntimeError(f"Registro fallido para {user.email}: {code} {body}")

    code, body = api.post_form("/api/v1/auth/login", {
        "username": user.email,
        "password": user.password,
        "grant_type": "password",
    })
    if code != 200:
        raise RuntimeError(f"Login fallido para {user.email}: {code} {body}")
    user.token = body["access_token"]

    api.token = user.token
    code, body = api._request("GET", "/api/v1/auth/me")
    if code != 200:
        raise RuntimeError(f"GET /me fallido: {code} {body}")
    user.user_id = body["id"]


def pet_payload(user: UserSpec, pet: PetSpec) -> dict:
    return {
        "name": pet.name,
        "breed": pet.breed,
        "birth_year": pet.birth_year,
        "sex": pet.sex,
        "weight_kg": pet.weight_kg,
        "notes": pet.notes,
        "residence_zone_code": user.residence_zone_code,
        "residence_source": "catalog",
        "residence_consent": True,
    }


def pet_requires_update(existing: dict, payload: dict) -> bool:
    comparable_fields = (
        "name",
        "breed",
        "birth_year",
        "sex",
        "weight_kg",
        "notes",
        "residence_zone_code",
    )
    return any(
        existing.get(field) != payload.get(field) for field in comparable_fields
    ) or not bool(existing.get("residence_consent"))


def ensure_pets(api: ApiClient, user: UserSpec) -> None:
    api.token = user.token
    code, existing = api.get_json("/api/v1/pets")
    if code != 200:
        raise RuntimeError(f"GET /pets fallido: {code} {existing}")
    by_name = {p["name"]: p for p in existing}

    for pet in user.pets:
        payload = pet_payload(user, pet)
        if pet.name in by_name:
            current = by_name[pet.name]
            pet.pet_id = current["id"]
            if pet_requires_update(current, payload):
                code, body = api.put_json(f"/api/v1/pets/{pet.pet_id}", payload)
                if code != 200:
                    raise RuntimeError(f"Actualizar mascota {pet.name} falló: {code} {body}")
                print(f"    ~ mascota actualizada: {pet.name} ({pet.pet_id})")
            else:
                print(f"    ~ mascota existente: {pet.name} ({pet.pet_id})")
            continue
        code, body = api.post_json("/api/v1/pets", payload)
        if code != 201:
            raise RuntimeError(f"Crear mascota {pet.name} falló: {code} {body}")
        pet.pet_id = body["id"]
        print(
            f"    + mascota creada: {pet.name} "
            f"({pet.breed}, {pet.sex}, {pet.birth_year}) -> {pet.pet_id}"
        )


def assign_pdfs_to_pets(pdfs: list[Path], users: list[UserSpec]) -> dict[str, list[Path]]:
    """Reparto estable y ponderado; un límite menor conserva las asignaciones."""
    pets_flat = [(u, p) for u in users for p in u.pets]
    rng = random.Random(20260425)
    cycle: list[tuple[UserSpec, PetSpec]] = []
    for weight_level in range(max(pet.weight_share for _, pet in pets_flat)):
        layer = [
            item for item in pets_flat if item[1].weight_share > weight_level
        ]
        rng.shuffle(layer)
        cycle.extend(layer)

    assignment: dict[str, list[Path]] = {pet.pet_id: [] for _, pet in pets_flat}
    for index, pdf in enumerate(pdfs):
        _, pet = cycle[index % len(cycle)]
        assignment[pet.pet_id].append(pdf)
    return assignment


def existing_analysis_filenames(api: ApiClient, pet_id: str) -> set[str]:
    path = f"/api/v1/history?pet_id={urllib.parse.quote(pet_id)}&limit=200&offset=0"
    code, body = api.get_json(path)
    if code != 200 or not isinstance(body, list):
        raise RuntimeError(f"GET /history falló para mascota {pet_id}: {code} {body}")
    return {
        str(item.get("filename"))
        for item in body
        if isinstance(item, dict) and item.get("filename")
    }


def seed_upload_filename(file_path: Path) -> str:
    """Nombre estable, anónimo y preservado por la política del backend."""
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()[:20]
    suffix = file_path.suffix.lower() or ".bin"
    return f"batch_demo_{digest}{suffix}"


def ensure_map_baseline(
    api: ApiClient,
    users: list[UserSpec],
) -> dict[str, int]:
    """Garantiza tres mascotas con una señal reciente por cada zona demo."""
    cbc = {
        "WBC": 18.6,
        "RBC": 6.18,
        "HGB": 14.6,
        "HCT": 42.8,
        "Platelets": 112.0,
        "Neutrophils": 14.2,
        "Lymphocytes": 0.8,
        "Monocytes": 0.8,
        "Eosinophils": 0.05,
    }
    created = 0
    skipped = 0
    for user in users:
        api.token = user.token
        for pet in user.pets[:3]:
            marker = (
                "batch_map_baseline_v1_"
                f"{hashlib.sha256(pet.pet_id.encode('utf-8')).hexdigest()[:12]}.json"
            )
            if marker in existing_analysis_filenames(api, pet.pet_id):
                skipped += 1
                continue
            code, body = api.post_json(
                "/api/v1/analyze/confirmed",
                {
                    "cbc": cbc,
                    "metadata": {"species": "Canino"},
                    "comments": (
                        "Muestra sintética de demostración para vigilancia comunitaria."
                    ),
                    "extraction_provider": "local",
                    "extraction_mode": "local",
                    "extraction_warnings": [],
                    "filename": marker,
                    "file_size": 0,
                    "pet_id": pet.pet_id,
                },
            )
            if code != 200:
                raise RuntimeError(
                    f"Crear señal demo para {pet.name} falló: {code} {body}"
                )
            if not isinstance(body, dict) or not body.get("findings"):
                raise RuntimeError(
                    f"La señal demo de {pet.name} no produjo hallazgos epidemiológicos."
                )
            created += 1
    return {"created": created, "skipped": skipped}


def upload_hemogramas(
    api: ApiClient,
    users: list[UserSpec],
    assignment: dict[str, list[Path]],
) -> tuple[dict[str, list[str]], dict[str, dict[str, int]]]:
    """Sube PDFs ausentes y retorna IDs nuevos y estadísticas por mascota."""
    out: dict[str, list[str]] = {}
    stats: dict[str, dict[str, int]] = {}
    grand_total = sum(len(v) for v in assignment.values())
    done = 0
    t0 = time.time()
    for user in users:
        api.token = user.token
        for pet in user.pets:
            files = assignment.get(pet.pet_id, [])
            existing = existing_analysis_filenames(api, pet.pet_id)
            ids: list[str] = []
            skipped = 0
            quarantined = 0
            failed = 0
            for fp in files:
                done += 1
                upload_filename = seed_upload_filename(fp)
                if upload_filename in existing:
                    skipped += 1
                    continue
                code, body = api.post_multipart(
                    (
                        f"/api/v1/analyze?pet_id={pet.pet_id}"
                        "&extraction_mode=local"
                    ),
                    fp,
                    upload_filename=upload_filename,
                )
                if code != 200:
                    detail = body.get("detail") if isinstance(body, dict) else None
                    error_code = (
                        detail.get("error_code") if isinstance(detail, dict) else None
                    )
                    if code == 422 and error_code in {
                        "MISSING_FIELD",
                        "RANGE_VIOLATION",
                        "TYPE_ERROR",
                    }:
                        quarantined += 1
                        print(
                            f"  ~ [{done}/{grand_total}] CUARENTENA {fp.name}: "
                            f"{error_code}"
                        )
                        continue
                    failed += 1
                    print(f"  ! [{done}/{grand_total}] FALLO {fp.name}: {code} {str(body)[:200]}")
                    continue
                ids.append(body["id"])
                existing.add(upload_filename)
                if done % 20 == 0 or done == grand_total:
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (grand_total - done) / rate if rate > 0 else 0
                    print(f"  > {done}/{grand_total} hemogramas ({rate:.1f}/s, ETA {eta:.0f}s)")
            out[pet.pet_id] = ids
            stats[pet.pet_id] = {
                "uploaded": len(ids),
                "skipped": skipped,
                "quarantined": quarantined,
                "failed": failed,
            }
            print(
                f"    [{user.full_name} | {pet.name}] "
                f"nuevos={len(ids)} existentes={skipped} "
                f"cuarentena={quarantined} fallidos={failed}"
            )
    return out, stats


# --- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Limita los PDFs para una carga breve. Omitirlo es lo recomendado; "
            "el baseline del mapa se crea siempre."
        ),
    )
    parser.add_argument("--report", default=str(ROOT / "outputs" / "seed_demo_report.json"))
    args = parser.parse_args()

    if not TEST_DIR.exists():
        print(f"No existe {TEST_DIR}", file=sys.stderr)
        return 1

    pdfs = sorted(TEST_DIR.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[:args.limit]
    print(f"Encontrados {len(pdfs)} PDFs en {TEST_DIR}")

    api = ApiClient(args.api)

    print("\n[1/4] Asegurando usuarios y mascotas")
    for user in USERS:
        print(f"- {user.full_name}")
        ensure_user(api, user)
        ensure_pets(api, user)

    print("\n[2/4] Asegurando señales recientes para el mapa")
    map_baseline = ensure_map_baseline(api, USERS)
    print(
        "  señales demo: "
        f"nuevas={map_baseline['created']} existentes={map_baseline['skipped']}"
    )

    assignment = assign_pdfs_to_pets(pdfs, USERS)
    print("\n[3/4] Plan de reparto:")
    for user in USERS:
        for pet in user.pets:
            n = len(assignment.get(pet.pet_id, []))
            print(f"  {user.full_name:22s} {pet.name:8s} ({pet.breed:20s}) -> {n} hemogramas")

    print("\n[4/4] Subiendo hemogramas...")
    ids, upload_stats = upload_hemogramas(api, USERS, assignment)

    failed_total = sum(item["failed"] for item in upload_stats.values())
    report = {
        "users": [
            {
                "id": u.user_id,
                "email": u.email,
                "password": u.password,
                "full_name": u.full_name,
                "profile": u.profile,
                "pets": [
                    {
                        "id": p.pet_id,
                        "name": p.name,
                        "breed": p.breed,
                        "sex": p.sex,
                        "birth_year": p.birth_year,
                        "weight_kg": p.weight_kg,
                        "notes": p.notes,
                        "residence_zone_code": u.residence_zone_code,
                        "uploaded_count": upload_stats[p.pet_id]["uploaded"],
                        "skipped_count": upload_stats[p.pet_id]["skipped"],
                        "quarantined_count": upload_stats[p.pet_id]["quarantined"],
                        "failed_count": upload_stats[p.pet_id]["failed"],
                    }
                    for p in u.pets
                ],
            }
            for u in USERS
        ],
        "totals": {
            "users": len(USERS),
            "pets": sum(len(u.pets) for u in USERS),
            "hemogramas_subidos": sum(len(v) for v in ids.values()),
            "hemogramas_existentes": sum(
                item["skipped"] for item in upload_stats.values()
            ),
            "hemogramas_en_cuarentena": sum(
                item["quarantined"] for item in upload_stats.values()
            ),
            "hemogramas_fallidos": failed_total,
            "pdfs_disponibles": len(pdfs),
            "senales_mapa_creadas": map_baseline["created"],
            "senales_mapa_existentes": map_baseline["skipped"],
        },
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReporte JSON guardado en {args.report}")
    print(f"Totales: {report['totals']}")
    return 1 if failed_total else 0


if __name__ == "__main__":
    sys.exit(main())
