# Metroid NES performance patch

Development workspace for a BPS patch targeting Metroid (USA) on the stock 128 KiB MMC1 cartridge configuration. The project starts with a read-only ROM fingerprinting tool. Keep game dumps, emulator states, and benchmark captures under the ignored `local/` directory.

## Build and run

Open `MetroidPerformancePatch.xcodeproj` in Xcode and choose the shared `metroid-rom-info` scheme. To build and fingerprint a file from the terminal:

```sh
xcodebuild -project MetroidPerformancePatch.xcodeproj -scheme metroid-rom-info -derivedDataPath DerivedData build
DerivedData/Build/Products/Debug/metroid-rom-info local/metroid-usa.nes
```

The SHA-256 covers the entire file, including its header. Record the exact hash, header format, emulator version, patch revision, and input replay with each benchmark.

## Build the first patch candidate

The builder takes a clean Metroid (USA) NES 2.0 dump and writes a BPS delta. For the combined build, apply [jslepicka's lag-fix 1.0 NES 2.0 BPS](https://github.com/jslepicka/metroid-lag-fix/tree/e9f7927d2b5abe922db81151ad86149dcb633168) to a separate local copy first. The builder checks both input hashes and refuses to overwrite existing outputs.

```sh
python3 tools/build_patch.py local/metroid-usa.nes local/metroid-combined.bps \
  --lag-fix-rom local/metroid-lag-fix.nes
python3 tools/build_patch.py local/metroid-usa.nes local/metroid-freeze-only.bps
```

Apply either output BPS to the clean dump. The combined build inherits upstream performance improvements and adds the Tourian fix. The freeze-only build applies the same change for players who prefer original timing.

| Build | Patched ROM SHA-256 |
| --- | --- |
| Combined | `81691dffe4cdf3877cd4c74eda69f85bca747904cc38a80228379fcb48c71a2e` |
| Freeze only | `adb584eb062dbbc0c8fec4a27c652215ebfba7ed5f9dd64680a8c27ac4ee2f29` |

The first build changes the relative branch operand at CPU address `$DD47`. If a missile drop fails the zero-capacity check at `$DD46`, the branch uses the existing enemy cleanup path at `$DD63` instead of retrying the same Tourian drop indefinitely. Eligible missile drops retain the original path.

## Milestones

- [x] Compare the clean ROM with metroid-lag-fix 1.0 using a Kraid replay, one room transition, and a scrolling flip. Record CPU cycles, missed updates, and the relative motion of Samus and the background.
- [ ] Profile remaining stalls in room loading and the Kraid, Ridley, and Mother Brain fights. Verify room contents, collision outcomes, and boss progression at equivalent game steps.
- [ ] Profile Mother Brain’s life-support workload separately from the boss and approach. Measure routine costs with the encounter active and use matched replays to verify collision, damage, and progression if a change is warranted. [Displaced Gamers Part 2](https://www.youtube.com/watch?v=1oCE-hYT3LY)
- [ ] Trace remaining scrolling jitter during flips, reversals, and room boundaries. Verify camera and sprite timing, input response, and background seams if a fix is needed.
- [ ] Build a reproducible BPS release with supported ROM hashes and before-and-after measurements. Verify a full emulator playthrough and smoke-test on stock NES hardware via flash cartridge.

Sources: [Slack proposal](https://hydeksworkspace.slack.com/archives/C0CL4CBU2TE/p1795615704900279) · [Room loading analysis](https://www.youtube.com/watch?v=3G6vkRz-_0I) · [Boss slowdown and scrolling analysis](https://retrorgb.com/lag-of-bosses-and-scrolling-jitters-in-nes-metroid-behind-the-code.html) · [Existing patch and benchmarks](https://github.com/jslepicka/metroid-lag-fix#readme)

## Optional password fixes

The Tourian freeze fix is available in both first-build variants. Keep the clean-ROM replay as the regression baseline.

- **JUSTIN BAILEY** (`JUSTIN BAILEY / ------ ------`). Keep the original 255-missile behavior. Research did not identify a separate reproducible bug in the canonical password, so there is no planned fix for it.
- [x] **NARPAS SWORD** (`NARPAS SWORD0 / 000000 000000`). Reproduced the freeze on clean ROM using the published [Thelife controller replay](https://tasvideos.org/UserFiles/Info/57364057182140642) with a controller-only branch in Tourian. The freeze-only build passed that same replay from boot. The combined build passed from a transferred Tourian checkpoint with the upstream code initialized. Both completed all 185 updates with zero retries, and the debugger-assisted positive-capacity control still produced a missile drop.
- [x] **First-build regressions.** The combined build matched lag-fix 1.0 across all 652 video frames of the Brinstar replay. Cold-boot password inputs preserved JUSTIN BAILEY’s 255 missiles, NARPAS SWORD debug mode, ordinary password recovery, and invalid-password rejection.


References: [Metroid password disassembly](https://github.com/nmikstas/metroid-disassembly/blob/master/Source_Files/Bank00.asm) · [Annotated password behavior](https://frameadvance.net/techniques/password-save/)
