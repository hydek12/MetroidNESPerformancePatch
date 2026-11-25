#!/usr/bin/env python3
"""Create the combined performance BPS for Metroid (USA) NES 2.0."""

import argparse
import hashlib
from pathlib import Path
import struct
import zlib
from itertools import groupby

from gameplay import apply_gameplay
from room_fill import optimize_room_fill, reuse_metatile_plan


CLEAN_SHA256 = "88ad02b0b53012712f3c773a62073847551cec191aeda5d3ec19b22b594640eb"
LAG_FIX_SHA256 = "a0c8084976174e55546f3af46b1c57e850a04eaf618ff288ee9e9d69608b1ead"
# The 16-byte header precedes eight 16 KiB PRG banks. Bank 7 is fixed at $C000.
FIXED_BANK_FILE_BIAS = 16 + 7 * 0x4000 - 0xC000
TOURIAN_BRANCH = (
    0xDD46, bytes.fromhex("F0 13"), bytes.fromhex("F0 1B")
)  # BEQ native enemy cleanup at $DD63 when missile capacity is zero.

NMI_EDITS = (
    # Check the main-loop completion flag before sprite DMA. The existing
    # late-frame branch still runs the sound engine and age update.
    (0xC0DF, bytes.fromhex("A9 00 8D 03 20 A9 02 8D 14 40 A5 1A D0 16"),
             bytes.fromhex("A5 1A D0 20 A9 00 8D 03 20 A9 02 8D 14 40")),
    # Branch on the string's mode once. Literals loop over INY/LDA/STA/DEX
    # and fall through to the original string tail at $C308.
    (0xC2FA, bytes.fromhex("90 01 C8 B0 01 C8 B1 00 8D 07 20 CA D0 F5"),
             bytes.fromhex("90 03 4C 3D E0 C8 B1 00 8D 07 20 CA D0 F7")),
    # Lag-fix 1.0 relocated the old sprite code here. The preceding stub
    # at $E038 ends in a JMP. RLE reads its value once and joins $C308.
    (0xE03D, bytes.fromhex("C0 05 6B 85 05 A5 6B 09 80 85 6B 60"),
             bytes.fromhex("C8 B1 00 8D 07 20 CA D0 FA 4C 08 C3")),
)


def read_verified(path, expected_hash):
    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"{path}: expected SHA-256 {expected_hash}, got {actual_hash}")
    return data


def apply_edits(rom, edits):
    target = bytearray(rom)
    for address, original, replacement in edits:
        offset = FIXED_BANK_FILE_BIAS + address
        end = offset + len(original)
        if len(original) != len(replacement) or target[offset:end] != original:
            raise ValueError(f"Unexpected edit layout at CPU ${address:04X}")
        target[offset:end] = replacement
    return target


def bps_number(value):
    result = bytearray()
    while value >= 0x80:
        result.append(value & 0x7F)
        value = (value >> 7) - 1
    result.append(value | 0x80)
    return result


def encode_bps(source, target):
    """Encode equal-size images using BPS SourceRead and TargetRead actions."""
    if len(source) != len(target):
        raise ValueError("Source and target must have the same size")

    patch = bytearray(b"BPS1")
    for value in (len(source), len(target), 0):
        patch.extend(bps_number(value))

    for matches, run in groupby(zip(source, target), lambda pair: pair[0] == pair[1]):
        target_bytes = bytes(after for _, after in run)
        action = 0 if matches else 1
        patch.extend(bps_number(((len(target_bytes) - 1) << 2) | action))
        if not matches:
            patch.extend(target_bytes)

    patch.extend(struct.pack("<II", zlib.crc32(source), zlib.crc32(target)))
    patch.extend(struct.pack("<I", zlib.crc32(patch)))
    return patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_rom", type=Path, help="verified Metroid (USA) NES 2.0 dump")
    parser.add_argument("output", type=Path, help="new BPS file")
    parser.add_argument(
        "--lag-fix-rom",
        type=Path,
        required=True,
        help="verified local ROM with upstream lag-fix 1.0 already applied",
    )
    args = parser.parse_args()

    try:
        source = read_verified(args.clean_rom, CLEAN_SHA256)
        base = read_verified(args.lag_fix_rom, LAG_FIX_SHA256)
        target = apply_edits(base, (TOURIAN_BRANCH,) + NMI_EDITS)
        optimize_room_fill(source, target)
        reuse_metatile_plan(source, target)
        apply_gameplay(target)
        with args.output.open("xb") as handle:
            handle.write(encode_bps(source, target))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")

    print(f"BPS: {args.output}")
    print(f"Patched ROM SHA-256: {hashlib.sha256(target).hexdigest()}")


if __name__ == "__main__":
    main()
