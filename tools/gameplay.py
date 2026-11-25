"""Battery-backed password slots, password refills, and renewable tube drops."""

from hashlib import sha256

from room_fill import replace


# Bank 0 code replaces unused tile data between the ending and intro music.
# $0110 selects the slot (offset 0 or 32), $0111 requests a refill, and
# $0112 marks a death password already calculated for the screen.
# Each slot stores 24 native password character indices and a version marker.
# The writer clears the marker first and writes it last. The reader checks
# character bounds and calls the original password validator.
TITLE_CODE = bytes.fromhex(
    # Read or erase the selected slot before the native title handling.
    "A5 14 "                         # AF03 LDA $14
    "29 20 "                         # AF05 AND #$20
    "F0 5D "                         # AF07 BEQ NormalTitle
    "A5 12 "                         # AF09 LDA $12
    "29 C0 "                         # AF0B AND #$C0
    "C9 80 "                         # AF0D CMP #$80
    "F0 08 "                         # AF0F BEQ SlotA
    "C9 40 "                         # AF11 CMP #$40
    "D0 51 "                         # AF13 BNE NormalTitle
    "A2 20 "                         # AF15 LDX #$20
    "D0 02 "                         # AF17 BNE SelectSlot
    "A2 00 "                         # AF19 LDX #$00
    "A5 14 "                         # AF1B LDA $14
    "29 08 "                         # AF1D AND #$08
    "D0 26 "                         # AF1F BNE ClearSlot
    "8E 10 01 "                      # AF21 STX $0110
    "BD 18 7F "                      # AF24 LDA $7F18,X
    "C9 A1 "                         # AF27 CMP #$A1
    "D0 35 "                         # AF29 BNE EmptySlot
    "A0 00 "                         # AF2B LDY #$00
    "BD 00 7F "                      # AF2D LDA $7F00,X
    "C9 40 "                         # AF30 CMP #$40
    "B0 21 "                         # AF32 BCS BadSlot
    "99 9A 69 "                      # AF34 STA $699A,Y
    "E8 "                            # AF37 INX
    "C8 "                            # AF38 INY
    "C0 18 "                         # AF39 CPY #$18
    "D0 F0 "                         # AF3B BNE ReadSlot
    "20 60 8F "                      # AF3D JSR $8F60
    "20 DE 8D "                      # AF40 JSR $8DDE
    "90 1E "                         # AF43 BCC Resume
    "B0 0E "                         # AF45 BCS BadSlot
    "A9 00 "                         # AF47 LDA #$00
    "9D 18 7F "                      # AF49 STA $7F18,X
    "A0 18 "                         # AF4C LDY #$18
    "9D 00 7F "                      # AF4E STA $7F00,X
    "E8 "                            # AF51 INX
    "88 "                            # AF52 DEY
    "D0 F9 "                         # AF53 BNE EraseSlot
    "AD 84 06 "                      # AF55 LDA $0684
    "09 01 "                         # AF58 ORA #$01
    "8D 84 06 "                      # AF5A STA $0684
    "4C FF 90 "                      # AF5D JMP $90FF
    "4C 2B 93 "                      # AF60 JMP $932B
    "4C D4 92 "                      # AF63 JMP $92D4
    "A5 12 "                         # AF66 LDA $12
    "29 30 "                         # AF68 AND #$30
    "4C DB 90 "                      # AF6A JMP $90DB
    # Death saves run only from GameOver, with rendering and NMI disabled.
    "20 9F 90 "                      # AF6D JSR $909F
    "AD B2 69 "                      # AF70 LDA $69B2
    "D0 21 "                         # AF73 BNE DeathReturn
    "20 7A 8C "                      # AF75 JSR $8C7A
    "EE 12 01 "                      # AF78 INC $0112
    "AE 10 01 "                      # AF7B LDX $0110
    "A9 00 "                         # AF7E LDA #$00
    "9D 18 7F "                      # AF80 STA $7F18,X
    "A0 00 "                         # AF83 LDY #$00
    "B9 9A 69 "                      # AF85 LDA $699A,Y
    "9D 00 7F "                      # AF88 STA $7F00,X
    "E8 "                            # AF8B INX
    "C8 "                            # AF8C INY
    "C0 18 "                         # AF8D CPY #$18
    "D0 F4 "                         # AF8F BNE WriteSlot
    "A9 A1 "                         # AF91 LDA #$A1
    "9D 00 7F "                      # AF93 STA $7F00,X
    "60 "                            # AF96 RTS
    # Use the same generated password on the game-over display.
    "AD 12 01 "                      # AF97 LDA $0112
    "F0 04 "                         # AF9A BEQ Calculate
    "CE 12 01 "                      # AF9C DEC $0112
    "60 "                            # AF9F RTS
    "4C 7A 8C "                      # AFA0 JMP $8C7A
    # Restore ordinary missile capacity now and schedule the health refill.
    "20 12 8D "                      # AFA3 JSR $8D12
    "AD B2 69 "                      # AFA6 LDA $69B2
    "D0 17 "                         # AFA9 BNE RefillReturn
    "A2 17 "                         # AFAB LDX #$17
    "BD 9A 69 "                      # AFAD LDA $699A,X
    "DD C3 AF "                      # AFB0 CMP Bailey,X
    "D0 04 "                         # AFB3 BNE OrdinaryPassword
    "CA "                            # AFB5 DEX
    "10 F5 "                         # AFB6 BPL CompareBailey
    "60 "                            # AFB8 RTS
    "AD 7A 68 "                      # AFB9 LDA $687A
    "8D 79 68 "                      # AFBC STA $6879
    "EE 11 01 "                      # AFBF INC $0111
    "60 "                            # AFC2 RTS
    "13 1E 1C 1D 12 17 0B 0A 12 15 0E 22 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F "  # AFC3 .byte 19,30,28,29,18,23,11,10,18,21,14,34,63,63,63,63,63,63,63,63,63,63,63,63
    # Run the upstream boot hook and install both gameplay helpers.
    "20 3D DE "                      # AFDB JSR $DE3D
    "A0 4F "                         # AFDE LDY #$4F
    "B9 35 B1 "                      # AFE0 LDA $B135,Y
    "99 00 7E "                      # AFE3 STA $7E00,Y
    "88 "                            # AFE6 DEY
    "10 F7 "                         # AFE7 BPL CopyByte
    "A0 00 "                         # AFE9 LDY #$00
    "8C 10 01 "                      # AFEB STY $0110
    "8C 11 01 "                      # AFEE STY $0111
    "8C 12 01 "                      # AFF1 STY $0112
    "60 "                            # AFF4 RTS
)

GAMEPLAY_CODE = bytes.fromhex(
    "A4 94 "                         # 7E00 LDY $94
    "C4 96 "                         # 7E02 CPY $96
    "D0 1D "                         # 7E04 BNE BelowLimit
    "C9 81 "                         # 7E06 CMP #$81
    "D0 16 "                         # 7E08 BNE NoDrop
    "A0 18 "                         # 7E0A LDY #$18
    "8A "                            # 7E0C TXA
    "D9 29 07 "                      # 7E0D CMP $0729,Y
    "D0 07 "                         # 7E10 BNE NextGenerator
    "B9 28 07 "                      # 7E12 LDA $0728,Y
    "C9 FF "                         # 7E15 CMP #$FF
    "D0 0D "                         # 7E17 BNE GeneratorDrop
    "98 "                            # 7E19 TYA
    "38 "                            # 7E1A SEC
    "E9 08 "                         # 7E1B SBC #$08
    "A8 "                            # 7E1D TAY
    "D0 EC "                         # 7E1E BNE FindGenerator
    "4C 5B DD "                      # 7E20 JMP $DD5B
    "4C 51 DD "                      # 7E23 JMP $DD51
    "A4 94 "                         # 7E26 LDY $94
    "A9 81 "                         # 7E28 LDA #$81
    "C9 89 "                         # 7E2A CMP #$89
    "60 "                            # 7E2C RTS
    # Apply the one-shot health refill when Samus is initialized.
    "AD 11 01 "                      # 7E2D LDA $0111
    "F0 13 "                         # 7E30 BEQ NormalHealth
    "CE 11 01 "                      # 7E32 DEC $0111
    "AD 77 68 "                      # 7E35 LDA $6877
    "0A "                            # 7E38 ASL
    "0A "                            # 7E39 ASL
    "0A "                            # 7E3A ASL
    "0A "                            # 7E3B ASL
    "09 09 "                         # 7E3C ORA #$09
    "8D 07 01 "                      # 7E3E STA $0107
    "A9 99 "                         # 7E41 LDA #$99
    "D0 07 "                         # 7E43 BNE StoreHealthLo
    "A9 03 "                         # 7E45 LDA #$03
    "8D 07 01 "                      # 7E47 STA $0107
    "A9 00 "                         # 7E4A LDA #$00
    "8D 06 01 "                      # 7E4C STA $0106
    "60 "                            # 7E4F RTS
)


def apply_gameplay(target):
    """Install the gameplay hooks in the verified combined ROM."""
    # Declare 8 KiB of battery-backed PRG RAM in NES 2.0. Boot still clears
    # $6000-$7EFF, leaving the two records in $7F00-$7F38 intact.
    if target[:16] != bytes.fromhex("4e45531a080010080000070700000001"):
        raise ValueError("Unexpected NES 2.0 header for cartridge saves")
    target[6] |= 0x02
    target[10] = 0x70
    replace(target, 7, 0xC058, b"\x7f", b"\x7e")

    # The original boot hook maps bank 0 back in before returning. The
    # wrapper copies the two fixed-bank helpers to otherwise unused WRAM.
    replace(target, 7, 0xC06D, bytes.fromhex("20 3D DE"), bytes.fromhex("20 DB AF"))
    replace(target, 7, 0xC920, bytes.fromhex("A9 00 8D 06 01 A9 03 8D 07 01"),
            bytes.fromhex("4C 2D 7E EA EA EA EA EA EA EA"))
    # At the native energy limit, allow a real energy roll only if an active
    # tube owns this enemy slot. Returning directly leaves that slot occupied
    # by its pickup until collection or expiry. The native no-item path and
    # missile handling (including the Tourian guard) are untouched.
    replace(target, 7, 0xDD4B, bytes.fromhex("A4 94 C4 96 F0 0A"),
            bytes.fromhex("4C 00 7E EA EA EA"))

    replace(target, 0, 0x90D7, bytes.fromhex("A5 12 29 30"), bytes.fromhex("4C 03 AF EA"))
    replace(target, 0, 0x939E, bytes.fromhex("20 9F 90"), bytes.fromhex("20 6D AF"))
    replace(target, 0, 0x936A, bytes.fromhex("20 7A 8C"), bytes.fromhex("20 97 AF"))
    replace(target, 0, 0x92DA, bytes.fromhex("20 12 8D"), bytes.fromhex("20 A3 AF"))

    for address, code, expected in (
        (0xAF03, TITLE_CODE, "bd1cd3b556612b71f58c04a6e2a1e0275305445ddb6e25765a030c28e8d0ed90"),
        (0xB135, GAMEPLAY_CODE, "60ad58009b6b939f3a594f9f53d1c6f01b3a2625bd2505cc8ce2d7117e018c36"),
    ):
        start = 16 + address - 0x8000
        original = target[start:start + len(code)]
        if sha256(original).hexdigest() != expected:
            raise ValueError(f"Unexpected bank 0 code space at ${address:04X}")
        replace(target, 0, address, original, code)
