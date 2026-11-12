"""Assemble a PNM image (P4, P5, P6) from a byte stream while it arrives."""

import re

import numpy as np
from numpy.typing import NDArray

_HEADER = re.compile(rb"^(P[456])\s+(?:#[^\n]*\n\s*)*(\d+)\s+(?:#[^\n]*\n\s*)*(\d+)\s+"
                     rb"(?:(?:#[^\n]*\n\s*)*(\d+)\s)?", re.DOTALL)


class PnmAssembler:
    """Collect the bytes of ``scanimage --format=pnm`` and expose finished rows.

    ``scanimage`` writes a short text header (format, width, height, maximum
    value; comments allowed) followed by the raw rows. 16-bit images are not
    produced in the modes scanbench uses.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.data = bytearray()
        self.kind = ""
        self.width = 0
        self.height = 0
        self._offset = -1

    def feed(self, chunk: bytes) -> None:
        """Add received bytes.

        Args:
            chunk: Bytes from the scanner.
        """
        self.data.extend(chunk)
        if self._offset < 0:
            match = _HEADER.match(bytes(self.data[:512]))
            if match is not None and (match[1] == b"P4" or match[4] is not None):
                self.kind = match[1].decode()
                self.width, self.height = int(match[2]), int(match[3])
                self._offset = match.end()

    def _row_bytes(self) -> int:
        """Return the number of bytes per row.

        Returns:
            Bytes per row.
        """
        return {"P4": (self.width + 7) // 8, "P5": self.width, "P6": 3 * self.width}[self.kind]

    def rows(self) -> int:
        """Return the number of complete rows received.

        Returns:
            Rows, 0 before the header is complete.
        """
        if self._offset < 0:
            return 0
        return min(self.height, (len(self.data) - self._offset) // self._row_bytes())

    def image(self) -> NDArray[np.uint8]:
        """Return the received part as RGB image; missing rows are white.

        Returns:
            Height x width x 3 array.
        """
        if self._offset < 0:
            return np.full((1, 1, 3), 255, dtype=np.uint8)
        rows = self.rows()
        raw = np.frombuffer(memoryview(self.data)[self._offset:self._offset
                                                  + rows * self._row_bytes()], dtype=np.uint8)
        if self.kind == "P6" and rows == self.height:
            return raw.reshape(rows, self.width, 3)       # complete: no copy
        result = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        result[:rows] = self._decode(raw, rows)
        return result

    def _decode(self, raw: NDArray[np.uint8], rows: int) -> NDArray[np.uint8]:
        """Turn raw rows into RGB rows.

        Args:
            raw: Bytes of complete rows.
            rows: Number of rows.

        Returns:
            Rows x width x 3 array (grey and line art repeated on the channels).
        """
        if self.kind == "P6":
            return raw.reshape(rows, self.width, 3)
        if self.kind == "P5":
            return np.repeat(raw.reshape(rows, self.width)[:, :, None], 3, axis=2)
        bits = np.unpackbits(raw.reshape(rows, -1), axis=1)[:, :self.width]   # P4: 1 = black
        return np.repeat(((1 - bits) * 255).astype(np.uint8)[:, :, None], 3, axis=2)

    def preview(self, max_side: int = 1600) -> NDArray[np.uint8]:
        """Return a reduced copy of the received part for the live display.

        Only every n-th row is read, so the cost does not grow with the full
        image (a 2400 dpi area can be close to a gigabyte).

        Args:
            max_side: Longest side of the result in pixels.

        Returns:
            Reduced RGB image; missing rows are white.
        """
        if self._offset < 0:
            return np.full((1, 1, 3), 255, dtype=np.uint8)
        step = max(1, -(-max(self.width, self.height) // max_side))
        result = np.full((-(-self.height // step), -(-self.width // step), 3), 255,
                         dtype=np.uint8)
        size, data = self._row_bytes(), memoryview(self.data)
        for index, row in enumerate(range(0, self.rows(), step)):
            start = self._offset + row * size
            line = np.frombuffer(data[start:start + size], dtype=np.uint8)
            result[index] = self._decode(line, 1)[0, ::step]
        return result
