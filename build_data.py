#!/usr/bin/env python3
"""Build STATOR49's public Loto + Super Loto archive from FDJ history ZIP files."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FDJ_DATASETS = {
    "loto": [
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afm6",
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afn6",
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afo6",
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afp6",
    ],
    "superloto": [
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afi6",
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afj6",
        "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afk6",
    ],
}
REQUIRED = ("date_de_tirage", "boule_1", "boule_2", "boule_3", "boule_4", "boule_5", "numero_chance")
OUT = Path(__file__).resolve().parent / "dist"


def download(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "STATOR49-DATA/1.0",
            "Accept": "application/zip, application/octet-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        data = response.read(4_000_001)
    if len(data) > 4_000_000:
        raise RuntimeError("FDJ archive exceeds safety limit")
    return data


def decode_csv(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def parse_zip(raw_zip: bytes, game: str) -> list[dict]:
    rows: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"{game}: ZIP contains no CSV")

        for name in csv_names:
            text = decode_csv(archive.read(name))
            reader = csv.DictReader(io.StringIO(text), delimiter=";")
            fields = set(reader.fieldnames or [])
            missing = set(REQUIRED) - fields
            if missing:
                raise RuntimeError(f"{game}: missing CSV columns {sorted(missing)}")

            for row in reader:
                raw_date = (row.get("date_de_tirage") or "").strip()
                if not raw_date:
                    continue
                date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                numbers = sorted(int(row[f"boule_{i}"]) for i in range(1, 6))
                chance = int(row["numero_chance"])

                if len(set(numbers)) != 5 or any(n < 1 or n > 49 for n in numbers):
                    raise RuntimeError(f"{game}:{date}: invalid main numbers")
                if not 1 <= chance <= 10:
                    raise RuntimeError(f"{game}:{date}: invalid Chance number")

                rows.append(
                    {
                        "id": f"{game}:{date}",
                        "game": game,
                        "date": date,
                        "numbers": numbers,
                        "chance": chance,
                    }
                )
    return rows


def signature(draw: dict) -> tuple:
    return draw["game"], draw["date"], tuple(draw["numbers"]), draw["chance"]


def build() -> tuple[dict, dict]:
    by_id: dict[str, dict] = {}
    counts = {"loto": 0, "superloto": 0}

    for game, urls in FDJ_DATASETS.items():
        for url in urls:
            for draw in parse_zip(download(url), game):
                ident = draw["id"]
                previous = by_id.get(ident)
                if previous is not None and signature(previous) != signature(draw):
                    raise RuntimeError(f"conflicting official rows for {ident}")
                if previous is None:
                    by_id[ident] = draw
                    counts[game] += 1

    draws = sorted(by_id.values(), key=lambda d: (d["date"], 0 if d["game"] == "loto" else 1))
    if not draws:
        raise RuntimeError("empty archive")
    if counts["loto"] < 2814:
        raise RuntimeError(f"LOTO archive unexpectedly short: {counts['loto']}")
    if counts["superloto"] < 1:
        raise RuntimeError("Super Loto archive unexpectedly empty")

    last_draw = max(draw["date"] for draw in draws)
    if last_draw < "2026-09-28":
        raise RuntimeError(f"archive rollback detected: {last_draw}")

    digest = hashlib.sha256()
    for draw in draws:
        digest.update(
            f"{draw['game']}|{draw['date']}|{','.join(map(str, draw['numbers']))}|{draw['chance']}\n".encode()
        )
    archive_version = f"stator49-fdj-{last_draw}-{digest.hexdigest()[:12]}"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    archive = {
        "schemaVersion": 1,
        "archiveVersion": archive_version,
        "source": "Résultats historiques Loto et Super Loto téléchargés depuis les archives FDJ",
        "generatedAt": now,
        "draws": draws,
    }

    archive_bytes = json.dumps(archive, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    manifest = {
        "schemaVersion": 1,
        "archiveVersion": archive_version,
        "lastDraw": last_draw,
        "drawCount": len(draws),
        "drawCounts": counts,
        "archiveAsset": "loto_draws.json",
        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "generatedAt": now,
        "source": "FDJ - archives historiques Loto + Super Loto",
    }
    return archive, manifest


def main() -> int:
    archive, manifest = build()
    OUT.mkdir(parents=True, exist_ok=True)
    archive_path = OUT / "loto_draws.json"
    manifest_path = OUT / "manifest.json"
    archive_bytes = json.dumps(archive, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    archive_path.write_bytes(archive_bytes)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = manifest["drawCounts"]
    print(
        f"{manifest['drawCount']} tirages · {counts['loto']} Loto · "
        f"{counts['superloto']} Super Loto · dernier {manifest['lastDraw']}"
    )
    print(f"archiveVersion={manifest['archiveVersion']}")
    print(f"sha256={manifest['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
