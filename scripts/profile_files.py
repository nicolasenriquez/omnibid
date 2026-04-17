#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover - optional dependency at runtime
    tqdm = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ingestion.contracts import validate_required_columns  # noqa: E402


@dataclass
class FileProfile:
    dataset_type: str
    file_name: str
    path: str
    rows: int
    columns: int
    header: list[str]
    contract_ok: bool
    missing_required_columns: list[str]


def discover_files(dataset_root: Path) -> list[tuple[str, Path]]:
    patterns = {
        "licitacion": "licitacion/*.csv",
        "orden_compra": "orden-compra/*.csv",
    }
    files: list[tuple[str, Path]] = []
    for dataset_type, pattern in patterns.items():
        for path in sorted(dataset_root.glob(pattern)):
            files.append((dataset_type, path))
    return files


def profile_csv(dataset_type: str, path: Path) -> FileProfile:
    with path.open("r", encoding="latin1", newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        header = next(reader)
        rows = sum(1 for _ in reader)
    contract = validate_required_columns(dataset_type, header)
    return FileProfile(
        dataset_type=dataset_type,
        file_name=path.name,
        path=str(path),
        rows=rows,
        columns=len(header),
        header=header,
        contract_ok=contract.ok,
        missing_required_columns=list(contract.missing_required_columns),
    )


def resolve_dataset_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    env_root = os.getenv("DATASET_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / "dataset-mercado-publico").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile ChileCompra CSV files")
    parser.add_argument("--dataset-root", default=None, help="Path to dataset-mercado-publico")
    parser.add_argument("--out", default="data/profiling/file_profiles.json", help="Output JSON path")
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show file-level progress while profiling (default: true)",
    )
    args = parser.parse_args()

    dataset_root = resolve_dataset_root(args.dataset_root)
    if not dataset_root.exists():
        raise SystemExit(f"Dataset root not found: {dataset_root}")

    files = discover_files(dataset_root)
    print(f"Profiling {len(files)} files from: {dataset_root}")
    iterable = files
    if args.progress and tqdm is not None:
        iterable = tqdm(files, desc="profile files", unit="file", dynamic_ncols=True)

    profiles: list[FileProfile] = []
    for dataset_type, path in iterable:
        profile = profile_csv(dataset_type, path)
        profiles.append(profile)
        if args.progress and tqdm is not None:
            tqdm.write(
                f"{profile.dataset_type} | {profile.file_name} | rows={profile.rows:,} | "
                f"cols={profile.columns} | contract_ok={profile.contract_ok}"
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([asdict(p) for p in profiles], ensure_ascii=False, indent=2), encoding="utf-8")

    for profile in profiles:
        if not profile.contract_ok:
            print(f"  missing_required_columns={','.join(profile.missing_required_columns)}")
    print(f"Wrote profile: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
