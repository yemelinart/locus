"""Build the offline gazetteer from explicitly downloaded public datasets.

Usage: python scripts/build_places.py PATH_TO_INPUTS
Inputs: GeoNames cities15000.zip, admin1CodesASCII.txt, UA.zip; Unicode CLDR
territories-en.json, territories-ru.json, territories-uk.json. No runtime downloads.
"""

import gzip
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def build(source, target):
    def rows(archive, member):
        with zipfile.ZipFile(source / archive) as z:
            return [line.split("\t") for line in z.read(member).decode().splitlines()]

    places = [
        [r[0], r[1], r[8], r[8] + "." + r[10], list(dict.fromkeys([r[1], r[2], *r[3].split(",")]))]
        for r in rows("cities15000.zip", "cities15000.txt")
        if r[6] == "P"
    ]
    admins = {}
    for line in (source / "admin1CodesASCII.txt").read_text().splitlines():
        r = line.split("\t")
        admins[r[0]] = list(dict.fromkeys(r[1:3]))
    for r in rows("UA.zip", "UA.txt"):
        if r[6:8] == ["A", "ADM1"]:
            admins[r[8] + "." + r[10]] = list(dict.fromkeys([r[1], r[2], *r[3].split(",")]))
    countries = {}
    for lang in ("en", "ru", "uk"):
        data = json.loads((source / f"territories-{lang}.json").read_text())
        for key, name in data["main"][lang]["localeDisplayNames"]["territories"].items():
            code = key.split("-")[0]
            if len(code) == 2 and code.isalpha():
                countries.setdefault(code, [code]).append(name)
    countries = {k: list(dict.fromkeys(v)) for k, v in countries.items()}
    manifest = {
        "geonames": "https://download.geonames.org/export/dump/",
        "cldr": "https://github.com/unicode-org/cldr-json",
        "inputs_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.iterdir())
            if p.suffix in {".zip", ".json", ".txt"}
        },
        "place_count": len(places),
    }
    target.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        {"places": places, "admins": admins, "countries": countries},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    (target / "places.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    (target / "places-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {len(places)} places; compressed bytes: {(target / 'places.json.gz').stat().st_size}")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(__file__).resolve().parents[1] / "backend/locus/geodata")
