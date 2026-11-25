# Metroid NES performance patch

Development workspace for a BPS patch targeting Metroid (USA) on the stock 128 KiB MMC1 cartridge configuration. The project starts with a read-only ROM fingerprinting tool. Keep game dumps, emulator states, and benchmark captures under the ignored `local/` directory.

## Build and run

Open `MetroidPerformancePatch.xcodeproj` in Xcode and choose the shared `metroid-rom-info` scheme. To build and fingerprint a file from the terminal:

```sh
xcodebuild -project MetroidPerformancePatch.xcodeproj -scheme metroid-rom-info -derivedDataPath DerivedData build
DerivedData/Build/Products/Debug/metroid-rom-info local/metroid-usa.nes
```

The SHA-256 covers the entire file, including its header. Record the exact hash, header format, emulator version, patch revision, and input replay with each benchmark.

## Milestones

- [ ] Compare the clean ROM with metroid-lag-fix 1.0 using a Kraid replay, one room transition, and a scrolling flip. Record CPU cycles, missed updates, and the relative motion of Samus and the background.
- [ ] Profile remaining stalls in room loading and the Kraid, Ridley, and Mother Brain fights. Verify room contents, collision outcomes, and boss progression at equivalent game steps.
- [ ] Trace remaining scrolling jitter during flips, reversals, and room boundaries. Verify camera and sprite timing, input response, and background seams if a fix is needed.
- [ ] Build a reproducible BPS release with supported ROM hashes and before-and-after measurements. Verify a full emulator playthrough and smoke-test on stock NES hardware via flash cartridge.

Sources: [Slack proposal](https://hydeksworkspace.slack.com/archives/C0CL4CBU2TE/p1795615704900279) · [Room loading analysis](https://www.youtube.com/watch?v=3G6vkRz-_0I) · [Boss slowdown and scrolling analysis](https://retrorgb.com/lag-of-bosses-and-scrolling-jitters-in-nes-metroid-behind-the-code.html) · [Existing patch and benchmarks](https://github.com/jslepicka/metroid-lag-fix#readme)

## Optional password fixes

These goals can ship as an opt-in companion patch after the performance work is verified. First reproduce the suspected defects on the clean Metroid (USA) ROM and record the exact inputs, ROM hash, expected behavior, and observed behavior.

- **JUSTIN BAILEY** (`JUSTIN BAILEY / ------ ------`). Keep the original 255-missile behavior. Research did not identify a separate reproducible bug in the canonical password, so there is no planned fix for it.
- [ ] **NARPAS SWORD** (`NARPAS SWORD0 / 000000 000000`). Investigate the reported Tourian freeze if a defeated Metroid rolls a missile drop while Samus has zero missile capacity. The original fixed-bank routine looped in a debugger-assisted reproduction with zero capacity and returned with capacity five. Confirm the encounter through gameplay, then verify that a fix preserves debug benefits and eligible missile drops. [Documented reproduction](https://tcrf.tiago.zip/wiki/Metroid#debug-features)
- [ ] **Regression checks.** Re-enter both codes on a cold boot, round-trip ordinary game-generated passwords, and confirm that bad-checksum passwords are still rejected. Retest the performance benchmarks with the companion patch applied.

References: [Metroid password disassembly](https://github.com/nmikstas/metroid-disassembly/blob/master/Source_Files/Bank00.asm) · [Annotated password behavior](https://frameadvance.net/techniques/password-save/)
