from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError("Project name needs at least one letter or number.")
    return slug[:80]


def project_root(base: Path, name: str) -> Path:
    return Path(base) / slugify(name)


def create_project(base: Path, name: str) -> Path:
    root = project_root(base, name)
    if root.exists():
        raise FileExistsError(f"A project named '{name}' already exists.")
    (root / "scripts").mkdir(parents=True)
    metadata = {"name": name.strip(), "created_at": datetime.now(timezone.utc).isoformat(), "language": "Hindi", "model": "gemini-3.5-flash-lite"}
    (root / "project.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return root


def list_projects(base: Path) -> list[Path]:
    root = Path(base)
    if not root.exists():
        return []
    return sorted((item for item in root.iterdir() if item.is_dir() and (item / "project.json").exists()), key=lambda item: item.name)


def read_project(root: Path) -> dict:
    return json.loads((Path(root) / "project.json").read_text(encoding="utf-8"))


def update_project(root: Path, **values: str) -> dict:
    data = read_project(root)
    data.update({key: value for key, value in values.items() if value is not None})
    (Path(root) / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def save_scripts(root: Path, uploads: list[object]) -> int:
    scripts = Path(root) / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    written = 0
    for upload in uploads:
        name = Path(str(upload.name)).name
        if name.lower().endswith(".txt"):
            (scripts / name).write_bytes(upload.getvalue())
            written += 1
    return written
