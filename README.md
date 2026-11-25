# Metroid NES performance patch

Development workspace for a BPS patch targeting Metroid (USA) on a 128 KiB MMC1 configuration with 8 KiB of battery-backed PRG RAM. The project starts with a read-only ROM fingerprinting tool. Keep game dumps, emulator states, and benchmark captures under the ignored `local/` directory.

## What the patch changes

All of these changes are enabled in the combined BPS.

| Change | In-game effect |
| --- | --- |
| **Lag-fix 1.0 performance base**, by jslepicka | Reduces CPU work in room loading, sprite drawing, collision checks, and the sound engine on the original 128 KiB MMC1 configuration. |
| **VBlank and NMI timing** | Holds the previous sprites and background scroll together when the main loop misses its deadline. The PPU writer also handles each literal or repeated-byte block with one mode check. |
| **Faster room initialization** | Loads the attribute fill value once and skips an extra 64-byte band in 68 rooms where later drawing overwrites that whole band. |
| **Metatile lookup reuse** | Reuses the four tile-table addresses prepared by the preceding room draw when the source matches. Rebuilds them when the graphics or area changes. |
| **NARPAS SWORD Tourian freeze fix** | Discards a missile drop when missile capacity is zero, avoiding the original retry loop. Valid missile drops and the debug code’s benefits are preserved. |
| **Battery-backed password saves** | Stores the active slot’s native checkpoint password on death. The title screen loads or clears either slot independently. |
| **Password refills** | Fills all earned energy tanks and restores missiles to capacity after an ordinary password or save load. |
| **Renewable tube drops** | Lets a tube-generated enemy drop energy even after the room cap is reached. The pickup still occupies that tube’s enemy slot until collected or expired. |

JUSTIN BAILEY still starts with 255 missiles. Room crossings can still miss updates. The patch prepares lookup metadata, while staging a complete room ahead of a crossing remains future work.

## Compatible ROM and file hashes

The combined BPS accepts the exact **clean Metroid (USA), PRG0, NES 2.0** dump listed below. Hash the full extracted `.nes` file, including its 16-byte header. The clean dump is **131,088 bytes**. The older iNES-header dump, other regions, headerless dumps, and already-patched ROMs have different source checksums.

| File | SHA-256 (whole file) | SHA-1 (whole file) | CRC32 (whole file) |
| --- | --- | --- | --- |
| **Clean Metroid (USA), PRG0, NES 2.0** — patch input | `88ad02b0b53012712f3c773a62073847551cec191aeda5d3ec19b22b594640eb` | `2080059bea4563ffff7535e6c0a0f3bc2f34b194` | `D1A02CAB` |
| **Metroid (USA) + lag-fix 1.0, NES 2.0** — builder reference | `a0c8084976174e55546f3af46b1c57e850a04eaf618ff288ee9e9d69608b1ead` | `8fe5cc20fb61791d605cc48fad7ff5c207e69e92` | `14FF0475` |
| **Metroid (USA) - Combined Performance Preview.nes** — patched output | `c1aac71583c70d8104dcb2b10f3e3671b0d9ce1a57a51f2be268929ebdc3fca9` | `08132a9db5ca7716cce0ab2e1f4b4a478e0594e4` | `7AC82547` |

The clean dump's header is `4e45531a080010080000070700000001`. Its PRG-only SHA-1 is `fdbfc7871962f72a1ef57e5a7e456164fb93430b`, which covers a different byte range from the whole-file hashes above. The combined BPS SHA-256 is `b4fa17e6ad0fcffa86cf69b672440730847fa65962109fcd2d4a3a976b0bdb4f`.

## Apply the combined BPS

1. Extract your clean ROM if it is in an archive. Keep the original dump as a backup.
2. Compute the clean ROM's SHA-256 and compare it with the **patch input** row.
3. In a BPS-compatible patcher, choose the clean `.nes` as the source and `metroid-combined.bps` as the patch. Save the result as `Metroid (USA) - Combined Performance Preview.nes`. The combined patch goes on the clean dump in one application.
4. Compute the output's SHA-256 and compare it with the **patched output** row before launching it in an NES emulator. If the patcher reports a source checksum mismatch, check the extracted file and header against the **patch input** row.

On macOS, run these checks from the folder containing your files:

```sh
shasum -a 256 metroid-usa.nes metroid-combined.bps
shasum -a 256 'Metroid (USA) - Combined Performance Preview.nes'
```

On Linux, use `sha256sum` in place of `shasum -a 256`. In Windows PowerShell, use `Get-FileHash -Algorithm SHA256 -LiteralPath 'file.nes'`.

## Rebuild the BPS from source

Apply [jslepicka’s lag-fix 1.0 NES 2.0 BPS](https://github.com/jslepicka/metroid-lag-fix/tree/e9f7927d2b5abe922db81151ad86149dcb633168) to a separate copy of the clean ROM to create the **builder reference** above. Then run the builder with both files. It verifies both hashes and requires a fresh output path.

```sh
python3 tools/build_patch.py local/metroid-usa.nes local/metroid-combined.bps \
  --lag-fix-rom local/metroid-lag-fix.nes
```

Keep ROM dumps and generated output under the ignored `local/` directory. For the optional Xcode fingerprinting tool, open `MetroidPerformancePatch.xcodeproj`, build the `metroid-rom-info` scheme, and pass it the extracted `.nes` file. Its SHA-256 covers the full file.

## VBlank and NMI timing

The NMI checks the main-loop completion flag before sprite DMA. On a missed update, sprites and background are held together while audio and the age update run on their original schedule. The PPU string writer selects literal or repeated-byte mode once per block. Both modes share the original pointer and scroll tail.

| Replay | Missed updates, first build → candidate | Minimum VBlank margin, CPU cycles |
| --- | ---: | ---: |
| Brinstar horizontal | 2 → 2 | 755 → 817 |
| Ridley-area vertical | 1 → 1 | 31 → 160 |
| Sustained Kraid | 0 → 0 | 1,331 → 1,337 |
| Sustained Ridley | 5 → 5 | 581 → 646 |

FCEUmm measured the margin from the last NMI PPU write or sprite DMA completion to the end of VBlank. All profiled NMI video writes finished inside VBlank. Audio and other handler work can continue after VBlank, so full NMI duration is a separate measurement. Main-loop work retains the time before the next NMI. Skipping an unused DMA saves about 524 measured CPU cycles on a missed update.

The four routes matched all 3,350 rendered frames at accepted updates. In the first build six missed frames transferred changed sprite data while the background scroll stayed held. The timing build held the previous rendered frame on all eight misses. The zero-lag target remains open for the three replays that still miss updates. The return addresses pushed by late NMIs include room-building code in work RAM and a sprite placement loop during sustained Ridley combat.

## Room-transition fill

The room drawer loads the attribute fill value once per room and reuses it across the fill loop. The tile stores are reordered so 68 rooms can skip one additional 64-byte band that the room structures fully overwrite. Across all 193 rooms, no room adds fill stores. The builder derives the skip table from the clean room structures and verifies the previous table and both fill templates before editing.

In debugger-triggered native FCEUmm tests of all 193 rooms in both destination buffers, all 386 room images, exit registers, and compared scratch values matched the prior timing build. Measured room construction was 117–501 CPU cycles faster per case. The Brinstar, Ridley-area vertical, and sustained Ridley gameplay replays retained 2, 1, and 5 missed updates respectively. All 2,150 accepted rendered frames matched. The host-assisted prefetch result remains the larger opportunity for the zero-lag target.

## On-ROM metatile lookup preparation

Each native room draw prepares four tile-table operands in work RAM. The next room in the same area can reuse those operands. Comparing the full immutable source pointer guards the shortcut, and graphics reloads reset the operands and force the original rebuild. This adds no work during ordinary movement and does not write a future room into a live buffer.

FCEUmm matched all 386 room-buffer, exit-register, and compared scratch cases against the room-fill build. Reusing a prepared plan saved 53 cycles per isolated room draw and 74 cycles in the setup portion of each profiled late update. The Brinstar, vertical, and sustained Ridley replays matched all 2,150 rendered updates and still had 2, 1, and 5 missed updates. This prepares lookup metadata on the cartridge. Staging a complete destination buffer ahead of a crossing is still required for the zero-lag goal.

## Cartridge saves

At the **START / CONTINUE** menu, hold **Select** and press the slot button. Hold **Select + Up** before pressing the slot button to erase that slot.

| Action | Slot A | Slot B |
| --- | --- | --- |
| Load checkpoint or start a fresh game if empty | Select + A | Select + B |
| Clear slot and stay at the menu | Select + Up + A | Select + Up + B |

A slot becomes active when you load it or start from it. **START** and manual **CONTINUE** default to slot A after boot. On death, the active slot receives the password displayed on the game-over screen. Saves restore the same area checkpoint and progression as a manual password. A fresh start has the original starting resources. The emulator or flash cart must persist battery RAM between sessions. On an original NES cartridge, this requires battery-backed hardware.

### Gameplay verification

FCEUmm stored and reloaded both slots through its libretro save-RAM interface in separate processes. Both records came from the native death flow, and the displayed passwords matched the stored characters. Slot B used debugger-staged progression for a distinct test checkpoint. The tests covered independent erasure, fresh starts from cleared slots, corrupt character rejection, a manual password with an energy tank and 150 missile capacity, and loading the two built-in passwords.

A debugger-assisted Brinstar test entered a room with a native tube, saturated its energy counter, and positioned Samus to fire and collect. Over 1,500 frames the prior patch yielded zero energy pickups and this build yielded 12. The test stayed in the room throughout and both builds had zero missed updates there.

| FCEUmm replay | Prior patch missed updates | Gameplay candidate missed updates |
| --- | ---: | ---: |
| Brinstar horizontal | 2 | 2 |
| Ridley-area vertical | 1 | 1 |
| Sustained Kraid | 0 | 0 |
| Sustained Ridley | 5 | 5 |

The boss and vertical tests used matched starting resources to isolate timing from the refill. All 3,350 accepted frames matched the prior patch pixel for pixel. Neither build registered NMI video writes outside VBlank on these routes. The QuickNES Tourian replay used a transferred checkpoint with the new work-RAM routines initialized. Batocera frontend persistence and flash-cart hardware remain untested.

## Milestones

- [x] Compare the clean ROM with metroid-lag-fix 1.0 using a Kraid replay, one room transition, and a scrolling flip. Record CPU cycles, missed updates, and the relative motion of Samus and the background.
- [ ] Profile remaining stalls in room loading and the Kraid, Ridley, and Mother Brain fights. Verify room contents, collision outcomes, and boss progression at equivalent game steps.
- [ ] Profile Mother Brain’s life-support workload separately from the boss and approach. Measure routine costs with the encounter active and use matched replays to verify collision, damage, and progression if a change is warranted. [Displaced Gamers Part 2](https://www.youtube.com/watch?v=1oCE-hYT3LY)
- [ ] Trace remaining scrolling jitter during flips, reversals, and room boundaries. Verify camera and sprite timing, input response, and background seams if a fix is needed.
- [ ] Build a reproducible BPS release with supported ROM hashes and before-and-after measurements. Verify a full emulator playthrough and smoke-test on stock NES hardware via flash cartridge.

Sources: [Slack proposal](https://hydeksworkspace.slack.com/archives/C0CL4CBU2TE/p1795615704900279) · [Room loading analysis](https://www.youtube.com/watch?v=3G6vkRz-_0I) · [Boss slowdown and scrolling analysis](https://retrorgb.com/lag-of-bosses-and-scrolling-jitters-in-nes-metroid-behind-the-code.html) · [Existing patch and benchmarks](https://github.com/jslepicka/metroid-lag-fix#readme)

## Password behavior

The combined patch includes the Tourian freeze fix. The clean-ROM replay is the regression baseline.

- **JUSTIN BAILEY** (`JUSTIN BAILEY / ------ ------`). Keep the original 255-missile behavior. Research did not identify a separate reproducible bug in the canonical password, so there is no planned fix for it.
- [x] **NARPAS SWORD** (`NARPAS SWORD0 / 000000 000000`). Reproduced the freeze on clean ROM using the published [Thelife controller replay](https://tasvideos.org/UserFiles/Info/57364057182140642) with a controller-only branch in Tourian. The freeze-only build passed that same replay from boot. The combined build passed from a transferred Tourian checkpoint with the upstream code initialized. Both completed all 185 updates with zero retries, and the debugger-assisted positive-capacity control still produced a missile drop.
- [x] **First-build regressions.** The combined build matched lag-fix 1.0 across all 652 video frames of the Brinstar replay. Cold-boot password inputs preserved JUSTIN BAILEY’s 255 missiles, NARPAS SWORD debug mode, ordinary password recovery, and invalid-password rejection.


References: [Metroid password disassembly](https://github.com/nmikstas/metroid-disassembly/blob/master/Source_Files/Bank00.asm) · [Annotated password behavior](https://frameadvance.net/techniques/password-save/)
