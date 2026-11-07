"""Validate the packaged Contarina brand PNGs without third-party image libraries.

The 0.2.4b1 brand assets had a valid PNG signature/IHDR but corrupted
palette CRC and missing IEND, so checking only the header is insufficient.
"""

from __future__ import annotations

import struct
import unittest
import zlib
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "contarina" / "brand"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def check_png(data: bytes) -> tuple[int, int]:
    """Verify chunk structure, CRCs, ending and dimensions; reject truncated PNGs."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid PNG signature")
    offset = len(PNG_SIGNATURE)
    chunk_names: list[bytes] = []
    dimensions: tuple[int, int] | None = None

    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError("truncated PNG chunk header")
        length = struct.unpack_from(">I", data, offset)[0]
        payload_start = offset + 8
        payload_end = payload_start + length
        if payload_end + 4 > len(data):
            raise ValueError("truncated PNG chunk payload")
        kind = data[offset + 4 : offset + 8]
        payload = data[payload_start:payload_end]
        stored_crc = struct.unpack_from(">I", data, payload_end)[0]
        computed_crc = zlib.crc32(payload, zlib.crc32(kind)) & 0xFFFFFFFF
        if stored_crc != computed_crc:
            raise ValueError(f"PNG {kind!r} CRC mismatch")

        if not chunk_names:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG must start with a 13-byte IHDR")
            width, height, bit_depth, color_type = struct.unpack_from(">IIBB", payload)
            if width == 0 or height == 0 or bit_depth != 8:
                raise ValueError("invalid PNG dimensions or bit depth")
            if color_type not in (2, 3, 6):
                raise ValueError("unsupported PNG color type")
            dimensions = (width, height)
        elif kind == b"IHDR":
            raise ValueError("duplicate IHDR")

        chunk_names.append(kind)
        offset = payload_end + 4
        if kind == b"IEND":
            if length != 0 or offset != len(data):
                raise ValueError("invalid IEND or trailing data")
            break

    if not chunk_names or chunk_names[-1] != b"IEND":
        raise ValueError("PNG is missing IEND")
    if b"IDAT" not in chunk_names:
        raise ValueError("PNG is missing IDAT")
    assert dimensions is not None
    return dimensions


class BrandPngTest(unittest.TestCase):
    def test_brand_pngs_have_valid_chunks_and_dimensions(self):
        for filename in ("icon.png", "logo.png"):
            with self.subTest(filename=filename):
                self.assertEqual(check_png((BRAND_DIR / filename).read_bytes()), (256, 256))

    def test_detects_corrupted_png_chunk(self):
        damaged = bytearray((BRAND_DIR / "icon.png").read_bytes())
        damaged[42] ^= 0x01
        with self.assertRaises(ValueError):
            check_png(bytes(damaged))

    def test_rejects_truncated_png(self):
        data = (BRAND_DIR / "icon.png").read_bytes()
        with self.assertRaises(ValueError):
            check_png(data[:-8])


if __name__ == "__main__":
    unittest.main()
