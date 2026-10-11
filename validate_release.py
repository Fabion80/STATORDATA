#!/usr/bin/env python3
"""Validate a complete archive against the last publicly distributed version."""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

from build_data import archive_cutoff, assert_no_regression


def get_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": "STATOR49-DATA/1.1"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read(4_000_001)
    if len(data) > 4_000_000:
        raise RuntimeError("Published archive exceeds size limit")
    return data


def main():
    archive_bytes = Path("dist/loto_draws.json").read_bytes()
    archive = json.loads(archive_bytes)
    manifest = json.loads(Path("dist/manifest.json").read_bytes())
    draws = archive["draws"]
    assert manifest["schemaVersion"] == archive["schemaVersion"] == 1
    assert manifest["archiveVersion"] == archive["archiveVersion"]
    assert manifest["archiveAsset"] == "loto_draws.json"
    assert manifest["drawCount"] == len(draws)
    assert manifest["lastDraw"] == max(d["date"] for d in draws)
    assert manifest["lastDraw"] < archive_cutoff()
    assert manifest["drawCounts"]["loto"] == sum(d["game"] == "loto" for d in draws)
    assert manifest["drawCounts"]["superloto"] == sum(d["game"] == "superloto" for d in draws)
    assert manifest["drawCounts"]["loto"] >= 2814
    assert manifest["drawCounts"]["superloto"] > 0
    assert all(d["id"] == f"{d['game']}:{d['date']}" for d in draws)
    assert len({d["id"] for d in draws}) == len(draws)
    assert manifest["sha256"] == hashlib.sha256(archive_bytes).hexdigest()
    # Resolve the immutable release first, so a concurrent publication cannot mix assets.
    release = json.loads(get_bytes("https://api.github.com/repos/Fabion80/STATORDATA/releases/latest"))
    assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
    previous_manifest = json.loads(get_bytes(assets["manifest.json"]))
    previous_bytes = get_bytes(assets["loto_draws.json"])
    assert hashlib.sha256(previous_bytes).hexdigest() == previous_manifest["sha256"]
    previous = json.loads(previous_bytes)
    assert previous_manifest["archiveVersion"] == previous["archiveVersion"]
    assert_no_regression(draws, previous["draws"])
    changed = manifest["archiveVersion"] != previous_manifest["archiveVersion"]
    print(f"Validated: {manifest['drawCount']} draws through {manifest['lastDraw']}; changed={changed}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"changed={str(changed).lower()}\n")


if __name__ == "__main__":
    main()
