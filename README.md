# Metroid NES performance patch

Development workspace for a BPS patch targeting Metroid (USA) on the stock 128 KiB MMC1 cartridge configuration. The project starts with a read-only ROM fingerprinting tool. Keep game dumps, emulator states, and benchmark captures under the ignored `local/` directory.

## Build and run

Open `MetroidPerformancePatch.xcodeproj` in Xcode and choose the shared `metroid-rom-info` scheme. To build and fingerprint a file from the terminal:

```sh
xcodebuild -project MetroidPerformancePatch.xcodeproj -scheme metroid-rom-info -derivedDataPath DerivedData build
DerivedData/Build/Products/Debug/metroid-rom-info local/metroid-usa.nes
```

The SHA-256 covers the entire file, including its header. Record the exact hash, header format, emulator version, patch revision, and input replay with each benchmark.

## Build and apply the combined patch

To reproduce the BPS, first apply [jslepicka's lag-fix 1.0 NES 2.0 BPS](https://github.com/jslepicka/metroid-lag-fix/tree/e9f7927d2b5abe922db81151ad86149dcb633168) to a separate local copy of the clean Metroid (USA) dump. The builder checks both input hashes and refuses to overwrite an existing output.

```sh
python3 tools/build_patch.py local/metroid-usa.nes local/metroid-combined.bps \
  --lag-fix-rom local/metroid-lag-fix.nes
```

Apply the resulting BPS directly to the **clean NES 2.0 ROM**. The BPS includes lag-fix 1.0, the VBlank and NMI timing changes, faster room fills, reuse of prepared metatile lookups, and the NARPAS SWORD Tourian freeze fix. Every change is built in and always active. The earlier feature flags and freeze-only build path have been retired.

| File | SHA-256 |
| --- | --- |
| Combined BPS | `8b598da62e821f2b1ab5cf0b67cbf25eba8f53a98f3f0a5b36872ec80076136b` |
| Patched NES ROM | `46964c00c87162302b4cbb3888caa3b66c5a1318237e207d8c16ae211295d54c` |

The Tourian fix changes the relative branch operand at CPU address `$DD47`. If a missile drop fails the zero-capacity check at `$DD46`, the branch uses the existing enemy cleanup path at `$DD63` instead of retrying the same Tourian drop indefinitely. Eligible missile drops retain the original path.

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
