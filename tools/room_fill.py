"""Shorten room-buffer initialization for the pinned lag-fix 1.0 layout."""

BANK_SIZE = 0x4000
HEADER_SIZE = 16
ROOM_POINTERS = 0x959A
FILL_TABLE = 0xB9ED
OLD_ORDER = (0, 14, 1, 13, 2, 12, 3, 11, 4, 10, 5, 9, 6, 8, 7)
# Every room keeps at least its old skip count with this order.
NEW_ORDER = (14, 0, 13, 1, 2, 12, 11, 3, 4, 10, 9, 5, 6, 8, 7)


def bank_offset(bank, address):
    return HEADER_SIZE + bank * BANK_SIZE + address - (0xC000 if bank == 7 else 0x8000)


def area_word(rom, bank, address):
    offset = bank_offset(bank, address)
    return int.from_bytes(rom[offset:offset + 2], "little")


def room_coverage(rom, bank, pointer, structure_table):
    """Return tile destinations overwritten by background structures."""
    covered = set()
    offset = bank_offset(bank, pointer) + 1
    while rom[offset] < 0xFD:
        position, structure, _palette = rom[offset:offset + 3]
        offset += 3
        row = bank_offset(bank, area_word(rom, bank, structure_table + 2 * structure))
        base = 64 * (position >> 4) + 2 * (position & 15)
        while rom[row] != 0xFF:
            header = rom[row]
            count = (header & 15) or 16
            start = base + 2 * (header >> 4)
            if start >= 0x3A0:  # The next tile pair would enter the attribute table.
                break
            width = min(2 * count, 32 - start % 32)
            covered.update(range(start, start + width))
            covered.update(range(start + 32, start + 32 + width))
            row += count + 1
            base += 64
    return covered


def fill_tables(rom):
    old, new = bytearray(240), bytearray(240)
    for bank in range(1, 6):
        room_table = area_word(rom, bank, ROOM_POINTERS)
        structure_table = area_word(rom, bank, ROOM_POINTERS + 2)
        for room in range((structure_table - room_table) // 2):
            coverage = room_coverage(rom, bank, area_word(rom, bank, room_table + 2 * room), structure_table)
            full = {
                row for row in range(15)
                if all(tile in coverage for tile in range(64 * row, 64 * (row + 1)))
            }
            index = (bank - 1) * 48 + room
            if len(full) == 15:
                old[index] = 45
            else:
                # Upstream skips the outside-in bands in pairs.
                for i in range(0, 15, 2):
                    if any(row not in full for row in OLD_ORDER[i:i + 2]):
                        old[index] = 3 * i
                        break
            new[index] = 3 * next((i for i, row in enumerate(NEW_ORDER) if row not in full), 15)
            if new[index] < old[index]:
                raise ValueError(f"Room {room:02X} in bank {bank} would add fill stores")
    return old, new


def fill_stores(base, order):
    return b"".join(bytes((0x99,)) + (base + 64 * row).to_bytes(2, "little") for row in order)


def replace(rom, bank, address, old, new):
    offset = bank_offset(bank, address)
    end = offset + len(old)
    if len(old) != len(new) or rom[offset:end] != old:
        raise ValueError(f"Unexpected room-fill layout in bank {bank} at CPU 0x{address:04X}")
    rom[offset:end] = new


def optimize_room_fill(clean_rom, target):
    old, new = fill_tables(clean_rom)
    replace(target, 6, FILL_TABLE, old, new)
    for base, address in ((0x6000, 0x9B8D), (0x6400, 0x9A78)):
        replace(target, 6, address, fill_stores(base, OLD_ORDER), fill_stores(base, NEW_ORDER))

    # Load X with the attribute value once, then use TXA in the fill loop.
    # The lower buffer's template straddles two bank 6 copy segments. Two
    # tail NOPs keep each copied template's footprint intact.
    replace(target, 6, 0x9BBA, bytes.fromhex("AD F4 6F 99"), bytes.fromhex("8A 99 C0 63"))
    replace(target, 6, 0xBE41, bytes.fromhex("C0 63 A9 FF C8 C0 40 D0 C6 4C 22 6F"),
                             bytes.fromhex("A9 FF C8 C0 40 D0 C8 EA EA 4C 22 6F"))
    replace(target, 6, 0x9AA5, bytes.fromhex("AD F4 6F 99 C0 67 A9 FF C8 C0 40 D0 C6 4C 22 6F"),
                             bytes.fromhex("8A 99 C0 67 A9 FF C8 C0 40 D0 C8 EA EA 4C 22 6F"))
    # INY and BNE move two bytes earlier. Update the branch displacement
    # calculation and the stores that patch each relocated branch operand.
    replace(target, 7, 0xCAD6, bytes.fromhex("E9 3A"), bytes.fromhex("E9 38"))
    replace(target, 7, 0xCAE0, bytes.fromhex("8D 35 77 A9 FF 4C 31 77 8D 20 76 A9 FF 4C 1C 76"),
                             bytes.fromhex("8D 33 77 A9 FF 4C 42 EA 8D 1E 76 A9 FF 4C 48 EA"))
    # Lag-fix redirects $EA3F. These entry stubs replace the unreachable
    # instructions after that redirect, then jump into the appropriate fill.
    replace(target, 7, 0xEA42, bytes.fromhex("A8 B1 3B 85 33 C8 B1 3B 85 34 A0 00"),
                             bytes.fromhex("AE F4 6F 4C 2F 77 AE F4 6F 4C 1A 76"))
