"""Stand-in for ``scanimage`` that streams slowly, for progress and cancel tests.

Usage: ``python fake_scanimage.py [--batch=PATTERN] [--fail] ...``. Without
``--batch`` it writes a 40 x 30 RGB PNM image to standard output in 10 parts
with progress lines on standard error. With ``--batch`` it writes three PNG
files and the batch messages of the real program. Other arguments are ignored.
"""

import sys
import time
import zlib


def png(width: int, height: int) -> bytes:
    """Return a tiny grey PNG file.

    Args:
        width: Width in pixels.
        height: Height in pixels.

    Returns:
        The file content.
    """
    def chunk(kind: bytes, data: bytes) -> bytes:
        """Build a PNG chunk.

        Args:
            kind: Chunk type.
            data: Chunk data.

        Returns:
            The chunk.
        """
        body = kind + data
        return (len(data).to_bytes(4, "big") + body
                + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big"))
    raw = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x00\x00\x00\x00"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def main() -> int:
    """Pretend to scan.

    Returns:
        Exit status.
    """
    args = sys.argv[1:]
    delay = 0.05
    if "--fail" in args:
        sys.stderr.write("scanimage: open of device failed: Invalid argument\n")
        return 1
    batch = next((a.split("=", 1)[1] for a in args if a.startswith("--batch=")), None)
    if batch is not None:
        for page in (1, 2, 3):
            sys.stderr.write(f"Scanning page {page}\n")
            for percent in (25, 50, 100):
                sys.stderr.write(f"Progress: {percent}.0%\r")
                sys.stderr.flush()
                time.sleep(delay)
            with open(batch % page, "wb") as target:
                target.write(png(8, 8))
            sys.stderr.write(f"Scanned page {page}. (scanner status = 5)\n")
        sys.stderr.write("Scanning page 4\n"
                         "scanimage: sane_start: Document feeder out of documents\n")
        return 7
    width, height = 40, 30
    sys.stdout.buffer.write(f"P6\n# fake\n{width} {height}\n255\n".encode())
    row = bytes([200, 100, 50]) * width
    for part in range(10):
        sys.stdout.buffer.write(row * (height // 10))
        sys.stdout.buffer.flush()
        sys.stderr.write(f"Progress: {(part + 1) * 10}.0%\r")
        sys.stderr.flush()
        time.sleep(delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
