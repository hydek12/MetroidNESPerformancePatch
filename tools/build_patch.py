#!/usr/bin/env python3
"""Create a BPS patch from a verified Metroid (USA) NES 2.0 dump."""

import argparse
import hashlib
from pathlib import Path
import struct
import zlib
from itertools import groupby


CLEAN_SHA256 = "88ad02b0b53012712f3c773a62073847551cec191aeda5d3ec19b22b594640eb"
LAG_FIX_SHA256 = "a0c8084976174e55546f3af46b1c57e850a04eaf618ff288ee9e9d69608b1ead"
# Fixed 16 KiB PRG bank 7, mapped at $C000-$FFFF after the 16-byte header.
BRANCH_OFFSET = 16 + 7 * 0x4000 + (0xDD46 - 0xC000)
ORIGINAL_BRANCH = bytes((0xF0, 0x13))  # BEQ $DD5B (reroll in Tourian)
FIXED_BRANCH = bytes((0xF0, 0x1B))     # BEQ $DD63 (discard enemy object)


def read_verified(path, expected_hash):
    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"{path}: expected SHA-256 {expected_hash}, got {actual_hash}")
    return data


def fix_drop_branch(rom):
    end = BRANCH_OFFSET + len(ORIGINAL_BRANCH)
    if rom[BRANCH_OFFSET:end] != ORIGINAL_BRANCH:
        raise ValueError("Expected the original missile-capacity branch at $DD46")
    return rom[:BRANCH_OFFSET] + FIXED_BRANCH + rom[end:]


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
        "--lag-fix-rom", type=Path, help="local ROM with upstream lag-fix 1.0 already applied"
    )
    args = parser.parse_args()

    try:
        source = read_verified(args.clean_rom, CLEAN_SHA256)
        base = read_verified(args.lag_fix_rom, LAG_FIX_SHA256) if args.lag_fix_rom else source
        target = fix_drop_branch(base)
        with args.output.open("xb") as handle:
            handle.write(encode_bps(source, target))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")

    print(f"BPS: {args.output}")
    print(f"Patched ROM SHA-256: {hashlib.sha256(target).hexdigest()}")


if __name__ == "__main__":
    main()
