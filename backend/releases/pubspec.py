import re
from pathlib import Path


_VERSION_RE = re.compile(r"^version:\s*(\S+)", re.MULTILINE)


def parse_pubspec_version(pubspec_path: str | Path) -> tuple[str, int]:
    text = Path(pubspec_path).read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        raise ValueError(f"Could not find version: in {pubspec_path}")

    raw = match.group(1).strip()
    if "+" not in raw:
        raise ValueError(f"pubspec version must be name+build (e.g. 1.0.0+1), got {raw!r}")

    version_name, build_raw = raw.split("+", 1)
    version_name = version_name.strip()
    build_number = int(build_raw.strip())
    if not version_name or build_number < 1:
        raise ValueError(f"Invalid pubspec version: {raw!r}")
    return version_name, build_number
