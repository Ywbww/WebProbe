"""Shared output helpers."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def filename_for_target(target_url: str, timestamp: datetime,
                        output_dir: str | Path, ext: str) -> Path:
    """Build webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.<ext> in output_dir.

    Strip URL path — preserve only host+port. Same-second collision →
    append _2, _3, etc. Both the HTML and TXT siblings from one scan share
    the same base name; this helper is called twice from the engine — once
    with ext='html', once with ext='txt'.
    """
    parsed = urlparse(target_url)
    host = parsed.hostname or "unknown"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    stamp = timestamp.strftime("%Y%m%d_%H%M%S")
    base = f"webprobe_{host}_{port}_{stamp}"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate = out_dir / f"{base}.{ext}"
    n = 2
    while candidate.exists():
        candidate = out_dir / f"{base}_{n}.{ext}"
        n += 1
    return candidate
