"""Restore a verified MEGA FAV source bundle during the Docker build."""
import base64
import hashlib
import io
import tarfile
from pathlib import Path

import brotli

ROOT = Path(__file__).resolve().parent
parts = [ROOT / "bundle" / f"part{i:02}.b64" for i in range(1, 6)]
if not all(part.is_file() for part in parts):
    raise SystemExit("Missing runtime bundle part")
encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
payload = base64.b64decode(encoded, validate=True)
expected = "3de41fb6d583e536f4284ce65cc53b9238ab138b4f7c084dc31a45a28afa97dc"
if hashlib.sha256(payload).hexdigest() != expected:
    raise SystemExit("MEGA FAV bundle checksum mismatch")
source_tar = brotli.decompress(payload)
with tarfile.open(fileobj=io.BytesIO(source_tar), mode="r:") as archive:
    for member in archive.getmembers():
        location = Path(member.name)
        if location.is_absolute() or ".." in location.parts or not (member.isfile() or member.isdir()):
            raise SystemExit(f"Unsafe bundle member: {member.name}")
    archive.extractall(ROOT, filter="data")
print("MEGA FAV runtime unpacked and SHA-256 verified")
