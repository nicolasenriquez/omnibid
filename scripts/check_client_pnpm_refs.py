from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATHS = [
    ROOT / "client" / "README.md",
    ROOT / "docs",
    ROOT / "justfile",
    ROOT / "openspec" / "changes",
]
BAN_RE = re.compile(r"\bnpm(?:\.cmd)?\s+run\b", re.IGNORECASE)


def main() -> int:
    matches: list[tuple[Path, int, str]] = []

    for target in TARGET_PATHS:
        paths = [target] if target.is_file() else target.rglob("*")
        for path in paths:
            if not path.is_file():
                continue

            if path.suffix not in {".md", ".txt", ".yml", ".yaml", ".json"} and path.name != "justfile":
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if BAN_RE.search(line):
                    matches.append((path.relative_to(ROOT), line_number, line.strip()))

    if not matches:
        return 0

    print("Found client verification references that still use legacy npm commands:", file=sys.stderr)
    for rel_path, line_number, line in matches:
        print(f"- {rel_path}:{line_number}: {line}", file=sys.stderr)
    print("Replace them with pnpm run or a pnpm-based just recipe.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
