"""Battery-backed password slots, password refills, and renewable tube drops."""

from hashlib import sha256

from room_fill import replace


# Bank 0 code replaces unused tile data between the ending and intro music.
# $0110 selects a slot (offset 0 or 32, or $FF for no slot), $0111 requests a refill, and
# $0112 marks a death password already calculated for the screen.
# Each slot stores 24 native password character indices and a version marker.
# The writer clears the marker first and writes it last. The reader checks
# character bounds and calls the original password validator.
TITLE_CODE = bytes.fromhex(
    # Read or erase the selected slot before the native title handling.
    "A5 14 "                         # AF03 LDA $14
    "29 20 "                         # AF05 AND #$20
    "F0 62 "                         # AF07 BEQ NormalTitle
    "A5 12 "                         # AF09 LDA $12
    "29 C0 "                         # AF0B AND #$C0
    "C9 80 "                         # AF0D CMP #$80
    "F0 08 "                         # AF0F BEQ SlotA
    "C9 40 "                         # AF11 CMP #$40
    "D0 56 "                         # AF13 BNE NormalTitle
    "A2 20 "                         # AF15 LDX #$20
    "D0 02 "                         # AF17 BNE SelectSlot
    "A2 00 "                         # AF19 LDX #$00
    "A5 14 "                         # AF1B LDA $14
    "29 08 "                         # AF1D AND #$08
    "D0 26 "                         # AF1F BNE ClearSlot
    "8E 10 01 "                      # AF21 STX $0110
    "BD 18 7F "                      # AF24 LDA $7F18,X
    "C9 A1 "                         # AF27 CMP #$A1
    "D0 3A "                         # AF29 BNE EmptySlot
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
    "90 23 "                         # AF43 BCC Resume
    "B0 0E "                         # AF45 BCS BadSlot
    "A9 00 "                         # AF47 LDA #$00
    "9D 18 7F "                      # AF49 STA $7F18,X
    "A0 18 "                         # AF4C LDY #$18
    "9D 00 7F "                      # AF4E STA $7F00,X
    "E8 "                            # AF51 INX
    "88 "                            # AF52 DEY
    "D0 F9 "                         # AF53 BNE EraseSlot
    "A2 FF "                         # AF55 LDX #$FF
    "8E 10 01 "                      # AF57 STX $0110
    "AD 84 06 "                      # AF5A LDA $0684
    "09 01 "                         # AF5D ORA #$01
    "8D 84 06 "                      # AF5F STA $0684
    "4C FF 90 "                      # AF62 JMP $90FF
    "4C 2B 93 "                      # AF65 JMP $932B
    "4C D4 92 "                      # AF68 JMP $92D4
    "A5 12 "                         # AF6B LDA $12
    "29 30 "                         # AF6D AND #$30
    "4C DB 90 "                      # AF6F JMP $90DB
    # Death saves run only from GameOver, with rendering and NMI disabled.
    "20 9F 90 "                      # AF72 JSR $909F
    "2C 10 01 "                      # AF75 BIT $0110
    "30 26 "                         # AF78 BMI DeathReturn
    "AD B2 69 "                      # AF7A LDA $69B2
    "D0 21 "                         # AF7D BNE DeathReturn
    "20 7A 8C "                      # AF7F JSR $8C7A
    "EE 12 01 "                      # AF82 INC $0112
    "AE 10 01 "                      # AF85 LDX $0110
    "A9 00 "                         # AF88 LDA #$00
    "9D 18 7F "                      # AF8A STA $7F18,X
    "A0 00 "                         # AF8D LDY #$00
    "B9 9A 69 "                      # AF8F LDA $699A,Y
    "9D 00 7F "                      # AF92 STA $7F00,X
    "E8 "                            # AF95 INX
    "C8 "                            # AF96 INY
    "C0 18 "                         # AF97 CPY #$18
    "D0 F4 "                         # AF99 BNE WriteSlot
    "A9 A1 "                         # AF9B LDA #$A1
    "9D 00 7F "                      # AF9D STA $7F00,X
    "60 "                            # AFA0 RTS
    # Use the same generated password on the game-over display.
    "AD 12 01 "                      # AFA1 LDA $0112
    "F0 04 "                         # AFA4 BEQ Calculate
    "CE 12 01 "                      # AFA6 DEC $0112
    "60 "                            # AFA9 RTS
    "4C 7A 8C "                      # AFAA JMP $8C7A
    # Restore ordinary missile capacity now and schedule the health refill.
    "20 12 8D "                      # AFAD JSR $8D12
    "AD B2 69 "                      # AFB0 LDA $69B2
    "D0 17 "                         # AFB3 BNE RefillReturn
    "A2 17 "                         # AFB5 LDX #$17
    "BD 9A 69 "                      # AFB7 LDA $699A,X
    "DD CD AF "                      # AFBA CMP Bailey,X
    "D0 04 "                         # AFBD BNE OrdinaryPassword
    "CA "                            # AFBF DEX
    "10 F5 "                         # AFC0 BPL CompareBailey
    "60 "                            # AFC2 RTS
    "AD 7A 68 "                      # AFC3 LDA $687A
    "8D 79 68 "                      # AFC6 STA $6879
    "EE 11 01 "                      # AFC9 INC $0111
    "60 "                            # AFCC RTS
    "13 1E 1C 1D 12 17 0B 0A 12 15 0E 22 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F 3F "  # AFCD .byte 19,30,28,29,18,23,11,10,18,21,14,34,63,63,63,63,63,63,63,63,63,63,63,63
    # Run the upstream boot hook and install both gameplay helpers.
    "20 3D DE "                      # AFE5 JSR $DE3D
    "A0 4F "                         # AFE8 LDY #$4F
    "B9 35 B1 "                      # AFEA LDA $B135,Y
    "99 00 7E "                      # AFED STA $7E00,Y
    "88 "                            # AFF0 DEY
    "10 F7 "                         # AFF1 BPL CopyByte
    "A0 00 "                         # AFF3 LDY #$00
    "8C 11 01 "                      # AFF5 STY $0111
    "8C 12 01 "                      # AFF8 STY $0112
    "88 "                            # AFFB DEY
    "8C 10 01 "                      # AFFC STY $0110
    "60 "                            # AFFF RTS
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
    replace(target, 7, 0xC06D, bytes.fromhex("20 3D DE"), bytes.fromhex("20 E5 AF"))
    replace(target, 7, 0xC920, bytes.fromhex("A9 00 8D 06 01 A9 03 8D 07 01"),
            bytes.fromhex("4C 2D 7E EA EA EA EA EA EA EA"))
    # At the native energy limit, allow a real energy roll only if an active
    # tube owns this enemy slot. Returning directly leaves that slot occupied
    # by its pickup until collection or expiry. The native no-item path and
    # missile handling (including the Tourian guard) are untouched.
    replace(target, 7, 0xDD4B, bytes.fromhex("A4 94 C4 96 F0 0A"),
            bytes.fromhex("4C 00 7E EA EA EA"))

    replace(target, 0, 0x90D7, bytes.fromhex("A5 12 29 30"), bytes.fromhex("4C 03 AF EA"))
    replace(target, 0, 0x939E, bytes.fromhex("20 9F 90"), bytes.fromhex("20 72 AF"))
    replace(target, 0, 0x936A, bytes.fromhex("20 7A 8C"), bytes.fromhex("20 A1 AF"))
    replace(target, 0, 0x92DA, bytes.fromhex("20 12 8D"), bytes.fromhex("20 AD AF"))

    for address, code, expected in (
        (0xAF03, TITLE_CODE, "f7811c711b9ddba4a78067c19b7a9f84b26cbe09814b2ec899fefadfb1d6fc6c"),
        (0xB135, GAMEPLAY_CODE, "60ad58009b6b939f3a594f9f53d1c6f01b3a2625bd2505cc8ce2d7117e018c36"),
    ):
        start = 16 + address - 0x8000
        original = target[start:start + len(code)]
        if sha256(original).hexdigest() != expected:
            raise ValueError(f"Unexpected bank 0 code space at ${address:04X}")
        replace(target, 0, address, original, code)
