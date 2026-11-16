"""Download the source PDF into pdf_docs/ and verify its SHA-256.

Falls back to DNS-over-HTTPS (curl --doh-url) when the local resolver cannot resolve *.gov.vn.
Usage: python -m advanced.fetch
"""
from __future__ import annotations

import hashlib
import subprocess

from .config import PDF_PATH, SHA256, SOURCE_URL


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PDF_PATH.exists() and sha256(PDF_PATH) == SHA256:
        print("PDF đã có và đúng checksum:", PDF_PATH)
        return
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    base = ["curl", "-sSL", "--fail", "--max-time", "300", "-A", "Mozilla/5.0", "-o", str(PDF_PATH)]
    for extra in ([], ["--doh-url", "https://1.1.1.1/dns-query"]):
        if subprocess.run(base + extra + [SOURCE_URL]).returncode == 0:
            break
    else:
        raise SystemExit("Không tải được PDF; tải thủ công từ " + SOURCE_URL)
    got = sha256(PDF_PATH)
    if got != SHA256:
        raise SystemExit(f"Checksum khác: {got} (mong đợi {SHA256}); nguồn có thể đã đổi phiên bản")
    print("OK:", PDF_PATH)


if __name__ == "__main__":
    main()
