# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a ZMK firmware configuration for the Charybdis 4x6 split ergonomic keyboard with a PMW3610 trackball sensor, running on nice!nano v2 (nRF52840) controllers.

## Building

Builds are handled exclusively via **GitHub Actions** — there is no local build setup. Push changes to trigger a build, or use the "Run workflow" button on the Actions tab.

The workflow (`build.yaml`) compiles **seven** artifacts — two mutually exclusive firmware sets plus resets:
- Direct BLE set: `charybdis_left`, `charybdis_right` (right = central)
- Dongle set: `charybdis_left_dongle`, `charybdis_right_dongle`, `charybdis_dongle` (XIAO = central)
- `settings_reset` ×2 — one per board (`nice_nano` for halves, `xiao_ble` for the dongle); **not interchangeable**

To flash: put the board into bootloader mode (double-tap reset), drag the `.uf2` file onto the mounted drive. **Always flash the matching `settings_reset` first.** Never mix halves from the two sets — their split roles differ. See the Dongle Variant section for the pairing order.

## Architecture

### Key Files

| File | Purpose |
|------|---------|
| `config/charybdis.keymap` | All layers and key bindings |
| `config/charybdis.conf` | Global ZMK Kconfig (BT, debounce, combos, sleep) |
| `config/west.yml` | ZMK dependency manifest (points to `zmkfirmware/zmk@main`) |
| `build.yaml` | GitHub Actions matrix — defines which boards/shields to build |
| `config/boards/shields/charybdis/charybdis_right.overlay` | Devicetree for right half: SPI pins, trackball, RGB LEDs |
| `config/boards/shields/charybdis/charybdis_right.conf` | Kconfig for right half: PMW3610 driver + acceleration settings |
| `config/boards/shields/charybdis/charybdis.dtsi` | Shared Devicetree: matrix transform, kscan GPIO rows |
| `config/charybdis.json` | Physical key layout definition consumed by ZMK Studio / keymap editors |
| `zmk-pmw3610-driver-main/` | Vendored PMW3610 driver (local copy, not fetched via west). Also hosts two unrelated pieces that ride along because the module is already injected everywhere: `src/input_processor_caret.c` and `src/battery_log.c` |
| `config/boards/shields/charybdis_dongle/` | Dongle variant shields — deliberately independent copies, see Dongle Variant section |
| `.github/workflows/draw-keymaps.yml`, `keymap_drawer.config.yaml` | Automatic keymap diagram (`keymap-drawer/charybdis.svg`) and its labels, see ZMK Studio section |

Note: `zmk-for-charybdis-Charybdis_4x6 original/` at the repo root is a frozen copy of the original seller firmware, kept only as a reference for diffing against upstream defaults. It is not built and should not be edited.

Note: `notes/` holds archived historical docs (seller manual, early spec drafts, an old ASCII cheatsheet). They describe earlier keymap revisions and are **not** accurate for the current firmware — see `notes/README.md`. Don't cite them as current behaviour; the hardware sections of `notes/instruction.md` (flashing, switch replacement) do still apply. Live files there: `notes/check_keymap.py` (see Known Gotchas), `notes/LAYOUT_V2_PLAN.md` and `notes/LAYOUT_V2_CHANGELOG.md` (layout v2 rationale, what moved where, deviations from the plan), and the cheatsheet `notes/charybdis-cheatsheet.html` — **generated**, edit `charybdis-cheatsheet.template.html` and run `python3 notes/build_cheatsheet.py`. The builder fails on any binding it has no label for (`LABELS` table), so after a keymap change it tells you exactly what to add. It also writes an Artifact fragment with `--fragment PATH`; the published copy is https://claude.ai/artifact/Lp86GkWBMv7LGpzzjMLMCZ (private).

Note: comments in `charybdis.keymap` and the `.conf` files are written in a mix of Russian and (occasionally) Chinese — expect this when grepping for context rather than assuming English-only comments.

### PMW3610 Trackball Driver — Critical Detail

The hardware uses a **3-wire/SDIO SPI bus**: MOSI and MISO are both wired to `P0.17` (shared line). The standard Zephyr `pixart,pmw3610` driver does not support this topology, so the repo uses a **vendored local driver** (`zmk-pmw3610-driver-main/`).

To avoid a naming conflict with the upstream Zephyr driver, the compatible string was renamed:
- `zmk-pmw3610-driver-main/dts/bindings/pixart,pmw3610.yml` → `compatible: "pixart,pmw3610-zmk"`
- `zmk-pmw3610-driver-main/src/pmw3610.c` → `#define DT_DRV_COMPAT pixart_pmw3610_zmk`
- `charybdis_right.overlay` → `compatible = "pixart,pmw3610-zmk"`

The driver is injected at build time via `cmake-args` in `build.yaml`:
```yaml
cmake-args: -DZMK_EXTRA_MODULES=${GITHUB_WORKSPACE}/zmk-pmw3610-driver-main
```
**Do not add the driver to `config/west.yml`** — it must stay as a local module.

### Pointer Acceleration

A double-incline curve with a plateau is implemented in the vendored PMW3610 driver: much slower for a barely moving ball, a stable middle, then a steep rise. The code is guarded by `CONFIG_PMW3610_ACCEL_ENABLED` and applies to the driver's MOVE mode. In the direct-BLE set that excludes Snipe/Scroll/Caret; **in the dongle set the half is always in MOVE, so the whole curve also shapes snipe, scroll and caret**, which are built on the dongle from the already-accelerated deltas. **So changing `ACCEL_MID_MULT` means rescaling the dongle's scroll divisor (18 × MID, now 23) and caret threshold (60 × MID, now 75) in `charybdis_dongle.overlay`**, otherwise they move with the cursor.

Key locations:
- `zmk-pmw3610-driver-main/Kconfig` — `PMW3610_ACCEL_*` config options
- `zmk-pmw3610-driver-main/src/pixart.h` — `accel_remainder_x/y`, `last_move_time` in `struct pixart_data`
- `zmk-pmw3610-driver-main/src/pmw3610.c` — `apply_acceleration()` function, called before HID report in `pmw3610_report_data()`

The ramp shape between LOW and HIGH is selectable via a Kconfig `choice` — `PMW3610_ACCEL_CURVE_LINEAR` / `_QUADRATIC` / `_SMOOTHSTEP`, applied to `t` in `apply_acceleration()`. All three give MID_MULT at LOW and MAX_MULT at HIGH; they differ in between. **Default is quadratic** (`t²`), chosen for a wider honest zone — at 3/5/8 counts/ms it gives 1.35/2.17/4.93 versus linear's 2.07/3.71/6.16. Switch it with one line in `charybdis_right.conf`; the options are listed in a comment there.

Parameters (all x100 because Kconfig doesn't support float):
- `ACCEL_MIN_MULT` (30 = 0.3x) — the bottom of the slow zone. Equal to MID turns the slow zone off. Range 1–100.
- `ACCEL_MID_MULT` (125 = 1.25x) — the stable middle. Finer than CPI, which only moves in jumps of 200.
- `ACCEL_CRAWL_MULT` (50 = 0.5x) and `ACCEL_CRAWL_SPEED` (14 = 0.14 counts/ms, ~6 mm/s) — a separate interval for the very slowest motion: below CRAWL_SPEED the whole multiplier is scaled by CRAWL_MULT, and the factor fades out smoothly by 2 × CRAWL_SPEED. `100` turns it off. 0.14 sits just above one count per 8 ms poll (0.125), so single-count reports are in full effect. It is separate from MIN_MULT so that ordinary slow aiming above ~12 mm/s is not touched.
- `ACCEL_SLOW_SPEED` (75 = 0.75 counts/ms, ~32 mm/s) — the multiplier reaches MID here. Must not exceed `ACCEL_LOW_SPEED`; `BUILD_ASSERT` also enforces MIN ≤ MID ≤ MAX and 2 × CRAWL_SPEED ≤ SLOW_SPEED.
- `ACCEL_LOW_SPEED` (200 = 2.0 counts/ms, ~85 mm/s) — between SLOW and LOW, multiplier = exactly MID; acceleration starts above it
- `ACCEL_HIGH_SPEED` (zones: 1000 = 10.0 counts/ms, ~423 mm/s; power curve now: 880 = ~373 mm/s) — above this, multiplier = max. The sensor is rated for 30 ips (~760 mm/s), so the ceiling is reachable.
- `ACCEL_MAX_MULT` (zones: 780 = 7.8x; power curve now: 700 = 7.0x) — maximum multiplier at high speed. Do not exceed ~15x: `apply_acceleration()` stores the result in an `int16_t` and the sensor delta is 12-bit (max 2047), so 16x overflows.

Measured by running the real `apply_acceleration()` on steady motion at CPI 600:

| mm/s | 2–5 | 10 | 20 | 32–100 | 150 | 200 | 300 | 400 | 423+ |
|---|---|---|---|---|---|---|---|---|---|
| multiplier | 0.16–0.18 | 0.50 | 0.96 | 1.25 | 1.49 | 2.01 | 3.90 | 6.93 | 7.8 |

**Currently active: `PMW3610_ACCEL_CURVE_POWER`, chosen over the zones after trying it on hardware (Nov 2026).** One formula, no zones: `mult = MAX × (speed / HIGH) ^ POWER_EXP`, limited to `POWER_MIN_MULT`…`MAX`. Current values: `POWER_EXP` 85, `POWER_MIN_MULT` 10, `MAX_MULT` 700, `HIGH_SPEED` 880 (~373 mm/s). **`MAX` scales the whole power curve, not just the ceiling:** to move only the ceiling, also set `HIGH_new = HIGH × (MAX_new / MAX) ^ (1 / EXP)`, which is how 7.8×/1000 became 7×/880 with the curve below it unchanged. The zone-only parameters stay in the config files and do nothing; **to go back, set `CONFIG_PMW3610_ACCEL_CURVE_QUADRATIC=y` instead of `_POWER` and `HIGH_SPEED=1000`, `MAX_MULT=780` in both `charybdis_right*.conf`**. It has no stable middle, so on the dongle set scroll and caret, which are compensated for a constant 1.25×, change with speed (about 1.6× more at 85 mm/s).

| mm/s | 2 | 3 | 5 | 10 | 20 | 50 | 85 | 150 | 200 | 300 | 373+ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| power curve | 0.10 | 0.12 | 0.18 | 0.33 | 0.59 | 1.27 | 1.99 | 3.23 | 4.13 | 5.82 | 7.0 |

The earlier table is the zone curve, measured with `HIGH_SPEED=1000`, `MAX_MULT=780`. The slow zone (Nov 2026) always uses smoothstep regardless of the selected curve: it is flat at both ends, so a crawl has a stable multiplier and there is no kink entering the plateau. Multipliers below 1 rely on the Q16.16 remainder below — fractions carry over, so slow motion does not stick. Goal: make aiming finer without holding the snipe key; whether snipe can go away entirely is still to be judged by hand.

Uses sub-pixel accumulation (Q16.16 fixed-point remainders) to avoid precision loss on small deltas. Speed is delta/dt for stability across variable polling rates.

`dt` is measured in **system timer ticks** (`k_uptime_ticks()`, ~30 µs on nRF52840), not whole milliseconds. Polls land ~8 ms apart, so millisecond resolution rounded `dt` to 7/8/9 and the multiplier jittered on perfectly steady movement — worse the faster you moved, because the ramp is steeper there. Switching to ticks cut the multiplier error 4×at low speed and ~13× at high speed. The field storing the timestamp is `last_move_ticks` — the name carries the unit deliberately; do not feed it milliseconds.

### Caret Mode — Trackball as Text Cursor

Caret mode converts trackball movement into arrow key presses — roll to move the text cursor in any editor/terminal. Implemented in the vendored PMW3610 driver (`pmw3610.c`, inside `pmw3610_report_data()` CURSOR branch).

- Activated by layer 4 (`nav_layer`, NAV — hold left thumb 50) — declared in overlay: `caret-layers = <4>;`. The thumb is a layer-tap, and ball motion is not a key event, so NAV (and caret) engages only after `tapping-term-ms` (200 ms) of holding — press the thumb slightly before rolling.
- Sensitivity: `CONFIG_PMW3610_CARET_TICK=20` in `charybdis_right.conf` (lower = more responsive)
- Runs at `SNIPE_CPI` (200), not the normal cursor CPI
- Accumulates delta X/Y until threshold, then sends arrow key press/release via `raise_zmk_keycode_state_changed_from_encoded()`

The accumulator works exactly like the scroll one: **the threshold is subtracted and the remainder carried**, and one poll can emit several arrows. It used to zero both accumulators and emit at most one arrow per poll, losing 7–13% of travel at normal speed and ~36% on a fast roll. Axis locking is intentional here too — the firing axis zeroes the other one. `PMW3610_CARET_MAX_TICKS_PER_POLL` is 4 rather than the scroll cap of 32, because each tick is a real key press/release pair and far more expensive than a wheel report. See the scroll-mode section for the full rationale; the two branches should be kept in sync if either is ever touched.

### Auto Mouse Layer — layer index is load-bearing

Trackball motion automatically raises layer 1 (`mouse_layer`: H = right click, J = left, N = middle; **hold K = snipe, hold L = scroll** via `&mo`; **both Space keys = `&to 0`**, back to letters without typing a space). **There is no timeout** (second parameter `0`; ZMK schedules the disable only when `param2 > 0`): the layer drops only on Space or a key outside `excluded-positions`. Implemented with ZMK's upstream `&zip_temp_layer` input processor, wired up in `charybdis_right.overlay`:

```dts
&trackball_listener { input-processors = <&zip_temp_layer 1 0>; };
&zip_temp_layer {
    require-prior-idle-ms = <200>;
    excluded-positions = <24 30 31 32 33 36 42 47 48 49 52 53>;
};
```

**Invariant — do not break this:** the auto mouse layer's index must stay **lower** than `snipe`/`scroll`/`caret`. The vendored driver picks the trackball mode from `zmk_keymap_highest_layer_active()` (`get_input_mode_for_current_layer()` in `pmw3610.c`) — *only* the topmost active layer. Give the mouse layer a higher index and holding `L` for scroll (or NAV for caret) leaves the mouse layer on top, so the driver never leaves MOVE mode and scroll/snipe/caret silently stop working while the ball is moving. Nothing fails at build time; it only shows up in the hand. The same trap applies to the driver's own `automouse-layer` property, which is deliberately left disabled (`-1`).

`excluded-positions` has **inverted semantics** — verified in ZMK's `app/src/pointing/input_processor_temp_layer.c`: listed positions do *not* dismiss the layer, everything else does, and an *empty* list means no key ever dismisses it (timeout only). The listed positions are the three clicks (30 H, 31 J, 42 N), the snipe/scroll holders (32 K, 33 L), both Shifts (36, 47) and Ctrl/Esc (24), Cmd (49), Alt (53) — so shift/cmd/ctrl/alt-click survive — plus Space (48, 52), so that its `&to 0` runs rather than a plain space from the base layer. `&to 0` is safe for the processor: it listens to `zmk_layer_state_changed`, clears its own state and cancels its timer when the layer goes away, and the next ball motion raises the layer again. **K and L must stay in the list:** otherwise pressing them dismisses the mouse layer before `&mo` resolves, and the key types a letter. The layer thumbs (50/54/55), Backspace/Hyper (51) and Enter deliberately dismiss it. The list is duplicated in `charybdis_dongle.overlay`; `check_keymap.py` compares the two.

**Clicks are duplicated on SNIPE and SCROLL, deliberately.** The snipe override (and the dongle's scroll/caret overrides) has no `process-next`, so while it is active `&zip_temp_layer` does not run and a timeout, if one is set, is not refreshed — the mouse layer drops during aiming. Without its own H/J/N clicks, J under a held K would then type `j`. With no timeout they are only a safeguard, kept so the timer can come back by changing one number. Do not "simplify" those layers to all-`&trans`.

**What having no timeout costs (Nov 2026, being tried; the 800 ms timer made it unclear whether the layer was still up).** After any ball motion H/J/K/L/N stay mouse keys until Space, also with modifiers (Shift+J is a shift-click rather than «О», Ctrl+L does nothing), and the BASE-only combos do not fire. A brush of the ball raises the layer invisibly and it stays. `require-prior-idle-ms` only watches keycodes and `&to 0` emits none, so ball motion right after Space raises the layer again — which makes the right Space (52, next to the ball) riskier than the left one (48). To go back: `0` → `800` in both overlays.

### Scroll Mode — accumulator carries its remainder

Scroll mode has no acceleration (`apply_acceleration()` is MOVE-only) and no CPI divisor. Movement accumulates into `scroll_delta_x/y`; every `CONFIG_PMW3610_SCROLL_TICK` (18) counts emits one wheel tick.

The accumulator **subtracts the threshold and carries the remainder**, and emits as many ticks as accumulated in one poll. It used to zero the accumulator outright and emit at most one tick per poll, which lost everything above the threshold — the faster you spun the ball, the more was dropped (measured: ~8% lost at moderate speed, ~42% on a flick, ~77% on a hard flick). That is an *inverse* acceleration, the same class of bug as the old `CPI_DIVIDOR=2` truncation.

**Axis locking is deliberate:** the axis that fires zeroes the *other* accumulator, so vertical scrolling suppresses horizontal drift. Do not "fix" this — on a trackball it is very hard to roll straight up without sideways drift. Only the firing axis carries its remainder.

`PMW3610_SCROLL_MAX_TICKS_PER_POLL` (32, in `pmw3610.h`) caps the burst per poll; anything beyond stays in the accumulator for the next poll, so no motion is lost. `PMW3610_SCROLL_TICK` has a Kconfig `range 1 1000` because the accumulator divides by it.

### ZMK Studio

The right shield build includes `snippet: studio-rpc-usb-uart` and `-DCONFIG_ZMK_STUDIO=y` in `build.yaml` (left half does not). This enables live keymap editing via ZMK Studio over USB. A dedicated combo (`combo_studio_unlock` in `charybdis.keymap`, GRAVE + BACKSPACE) calls `&studio_unlock` to allow the Studio connection to write to the keyboard — without it, Studio can view but not modify the keymap.

**The keymap has a second author.** Alongside manual edits, `config/charybdis.keymap` is rewritten by the keymap editor and pushed straight to the branch as commits from `keymap-editor[bot]` (e.g. `similar to corne`, `new position for brackets`, `removed home row`). Consequences to keep in mind:

- **Always `git pull` before touching the keymap.** The remote branch may have moved even if nothing local changed. Re-read `charybdis.keymap` after pulling rather than trusting an earlier read in the same session — layers have been added and thumb keys reassigned this way.
- **The keymap file is the single source of truth.** Layer tables in this file and in `README.md` are hand-maintained snapshots that drift whenever the bot pushes; verify against the actual bindings before relying on them, and treat a mismatch as the docs being stale, not the keymap.
- **Bot commits are formatting-blind.** They rewrite the whole `bindings` block, so hand-written comments and alignment inside a layer may not survive. Put durable explanations outside the layer blocks (or in this file) rather than inline.

**A render bot also commits after keymap pushes.** `draw-keymaps.yml` calls the upstream `caksoylar/keymap-drawer` reusable workflow (not the `hnaderi` fork, which stopped in April 2024 and only adds a Docker image) and commits `keymap-drawer/charybdis.{svg,yaml}` as `keymap-drawer render` when `config/charybdis.keymap`, `config/charybdis.json` or `keymap_drawer.config.yaml` change. So the local branch falls behind: pull before the next push. These commits use `GITHUB_TOKEN`, so they do not start another firmware build. `raw_binding_map` keys in the config must match the binding text exactly, otherwise the label silently falls back to the default one. A local preview needs Python ≥ 3.10 (`python3` here is 3.9): a venv on `/usr/bin/python3.12`, then `keymap -c keymap_drawer.config.yaml parse -z config/charybdis.keymap > out.yaml` and `keymap -c keymap_drawer.config.yaml draw out.yaml -j config/charybdis.json > out.svg`.

### Dongle Variant — Two Mutually Exclusive Firmware Sets

`build.yaml` builds two complete sets from every push: the original direct-BLE pair, and a dongle set (`charybdis_left_dongle`, `charybdis_right_dongle`, `charybdis_dongle` on `xiao_ble/nrf52840/zmk`). Both halves become peripherals in the dongle set; the XIAO is the central. Note there are **two** `settings_reset` artifacts — one per board — and they are not interchangeable.

Dongle shields live in a separate directory, `config/boards/shields/charybdis_dongle/`, with their own `Kconfig.shield`/`Kconfig.defconfig`. The matrix transform and physical layout are **deliberately duplicated** from `charybdis.dtsi` rather than shared, so a mistake in the dongle variant cannot reach the working build. Changing the matrix means changing it in both places.

**Two ZMK facts that shape this whole design — verify against them before touching the trackball:**

1. **`src/keymap.c` is compiled for the central only** (`app/CMakeLists.txt`: the `if ((NOT CONFIG_ZMK_SPLIT) OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL)` block). So is `src/events/keycode_state_changed.c`. Anything in the vendored driver calling `zmk_keymap_*` or `raise_zmk_keycode_state_changed_*` will fail to link on a peripheral.
2. **ZMK does not propagate layer state to peripherals.** So the driver's mode selection cannot work there at all, regardless of linking.

Both are handled with `#if IS_ENABLED(CONFIG_ZMK_SPLIT) && !IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)` guards in `pmw3610.c`: `get_input_mode_for_current_layer()` returns `MOVE` unconditionally on a peripheral, and the whole CURSOR/caret branch is compiled out. The acceleration path is untouched and identical in both variants — it is pure arithmetic with no keymap dependency.

In the dongle set, snipe / scroll / auto-mouse are re-implemented on the central as layer-scoped `input-processors` in `charybdis_dongle.overlay`, so **their layer numbers are duplicated there too** — a third place to update on renumbering, alongside the driver's `*-layers` and the snipe scaler override in `charybdis_right.overlay`. Caret mode is provided by a **custom input processor** rather than the driver: `zmk,input-processor-caret` in the vendored module (`src/input_processor_caret.c`, binding under `dts/bindings/input_processors/`). Processors run on the device holding the keymap, so this works where the driver's caret cannot. It duplicates the driver's logic — threshold subtraction with carried remainder, axis locking, burst cap — and zeroes `event->value` so the cursor does not also move.

**Returning `ZMK_INPUT_PROC_STOP` is not enough for a layer-scoped processor** — a real trap. `filter_with_input_config()` in ZMK's `input_listener.c` does `if (!override->process_next) { return 0; }`, hardcoding `ZMK_INPUT_PROC_CONTINUE` and throwing away whatever the override's processors returned. The event then reaches `handle_rel_code()` and moves the pointer anyway. Zeroing the value is what actually suppresses it; the `STOP` return is kept only for the case where the processor is ever attached to the base chain, where the return value *is* honoured.

There are now **two caret implementations**: the driver's (used by variant 1, gated to central-only) and the processor's (used by the dongle). They are meant to behave identically; if you fix one, fix the other. The processor could eventually replace the driver's caret in both variants — clearing `caret-layers` and adding `&zip_caret` to variant 1's listener would collapse them into one — but that has not been done, since variant 1 works as is.

Threshold differs between the two by design: the driver uses `CARET_TICK=20` at `SNIPE_CPI=200`, the processor uses `75` at the normal 600 CPI (60 sensor counts × `ACCEL_MID_MULT` 1.25, because it receives already-multiplied deltas). Both land near 2.5 mm of ball travel per arrow.

### Battery Level Logging on the Dongle

Over USB there is no way to see the halves' charge: ZMK exposes battery via BAS, a Bluetooth service, so neither `bluetoothctl` nor `upower` show anything when the host talks to the dongle. `zmk-pmw3610-driver-main/src/battery_log.c` (enabled by `CONFIG_ZMK_BATTERY_LOG=y` in `charybdis_dongle.conf`) subscribes to `zmk_peripheral_battery_state_changed` and prints one INFO line per change, caching the last value per half so a single line always shows both: `BATTERY  0:24%  1:97%`. Read it with `cat /dev/ttyACM0` on the host the dongle is plugged into.

Three non-obvious requirements, all documented inline in `charybdis_dongle.conf`:

- **`CONFIG_ZMK_LOGGING_MINIMAL=y` is mandatory.** With USB logging on, ZMK defaults `ZMK_LOG_LEVEL` to DEBUG for everything, and the dongle then logs every pointer event at 125 Hz — the battery lines drown. `LOGGING_MINIMAL` suppresses ZMK's debug output; our module registers with an explicit `LOG_LEVEL_INF` so its lines survive.
- **`ZMK_BATTERY_REPORTING` must stay enabled even though the dongle has no battery.** `app/CMakeLists.txt` gates `src/events/battery_state_changed.c` on it, and that file defines the event types both our logger and ZMK's own `split/central.c` link against. The dongle's own reading is nonsense (USB-powered ADC read 4148 mV → "94%"), so the self-battery subscription is behind `CONFIG_ZMK_BATTERY_LOG_SELF` and left off.
- **`BATTERY_LEVEL_PROXY` is deliberately off.** It republishes charge as a separate BAS service — only useful if the dongle itself connects over BLE — and ZMK issue #3095 reports a build error when FETCHING and PROXY are both on with three or more split parts.

**The right half's reading is bogus — do not act on it.** Verified 2026-09-15: the right half (`0` in the log) has reported 23–25 % continuously since at least Sept 3, through a full charge and through plugging USB straight into it. On USB it jumps to 100 % like the left, but within one 60 s report after unplugging it is back at ~24 % (≈ 3.64 V by ZMK's linear `lithium_ion_mv_to_pct`) — a real cell just off the charger sits at ≥ 4.1 V for hours. So its `VDDH` ADC responds to the charger but is not measuring the battery; most likely the controller in that half is a nice!nano clone whose power path isolates `VDDH` from the cell (the SuperMini family routes its divider to P0.24, a non-analog pin, so there is no firmware fix — only a solder mod). The left half (`1`) is honest: 96–100 % a week after a full charge. Treat the right half as having no charge indication, and charge both halves together. This also retires the earlier worry that `PERIPHERAL_PREF_LATENCY=0` was draining the right half to 24 % — that number was never a measurement.

Index → side mapping is **not** left/right by construction: `zmk_ble_put_peripheral_addr()` in `split/bluetooth/central.c` pins a slot to the first bonded address and persists it in settings, so `0` is whichever half paired first after `settings_reset`. Here it happens to be the right; re-check after any re-pairing by plugging USB into one half and waiting ≥ 90 s (`ZMK_BATTERY_REPORT_INTERVAL=60`, and a line is printed only on change).

Reading the log on this Linux host needs the dongle plugged **directly** into the machine — through a KVM (DeskHop earlier, a plain KVM since Oct 2026) only HID is typically forwarded, the CDC ports never appear. The dongle enumerates two ACM ports (`if00` = log, `if03` = Studio RPC); the user is not in `dialout`, so `sudo timeout 60 cat /dev/ttyACM0`.

### ZMK Board Variant — Breaking Change

ZMK introduced a board variant system. The nice_nano board must be specified as `nice_nano@2.0.0/nrf52840/zmk` in `build.yaml` (not just `nice_nano@2.0.0`). The `/zmk` variant sets `CONFIG_ZMK_BLE=y` which is required for split BLE. Without it, builds fail with linker errors about `ZMK_SPLIT_ROLE_CENTRAL`.

### Layer Map

Layout v2 (Oct 2026). Layer nodes are named `base_layer` … `fun_layer` with `display-name = "BASE"` etc.; layer numbers are written **literally** in bindings (`&lt 4 TAB`), see the no-macros rule below.

| Index | Name | Activation | Content |
|-------|------|-----------|---------|
| 0 | BASE | default | QWERTY, plain letters |
| 1 | MOUSE | **automatic** — ball motion (`&zip_temp_layer 1 0`, no timeout) | H/J/N clicks, `&mo 2` (SNIPE) on K, `&mo 3` (SCROLL) on L, `&to 0` on both Space keys |
| 2 | SNIPE | hold K while MOUSE is up | slow cursor; only H/J/N clicks, rest `&trans` |
| 3 | SCROLL | hold L while MOUSE is up | ball → wheel; only H/J/N clicks, rest `&trans` |
| 4 | NAV | hold 50 (left thumb, tap = Tab) | **Ubuntu-native.** Right: arrows on HJKL, Home/PgDn/PgUp/End above, file start / word ← / word → / file end below, P/[ = delete word left/right, ; = Del. Left: Q next window of the app, W/E tab prev/next, A/G VS Code back/forward, S/D/F = Alt/Ctrl/Shift, Z/X/C window left / toggle maximize / right, V/B window to left/right monitor. **Ball = caret** |
| 5 | NUM | hold 55 (right thumb, tap = Enter) | numpad left (W E R / S D F / X C V = 7 8 9 / 4 5 6 / 1 2 3), mods right |
| 6 | FUN | hold 54 (left thumb, tap = language, `LC(SPACE)`) | F1–F12 on the number row, BT select/clear on the left, media/brightness on the right, Print Screen on `[`, `&bootloader` (Z, left half only), `&studio_unlock` |

**Invariants (all checked by `notes/check_keymap.py`):**
- MOUSE (1) is below SNIPE/SCROLL/NAV — see Auto Mouse Layer.
- Driver `snipe-layers = <2>`, `scroll-layers = <3>`, `caret-layers = <4>` in `charybdis_right.overlay`; the dongle's `snipe_scaler`/`scroll_mapper`/`caret_proc` use the same numbers. Numbers are literal everywhere.
- Layer holders lead where they should (`HOLDER_TARGETS` in the script, matched by `display-name`): BASE 50 → NAV, 55 → NUM, 54 → FUN; MOUSE 32 (K) → SNIPE, 33 (L) → SCROLL.
- **No `#define` in the keymap** (see below).
- **No `&lt`/`&mt` on letter positions of BASE (13–22, 25–34, 37–46).** A hold-tap on a letter emits the tap only on release — that was the "mushy letters" problem layout v2 removed. Layers live on thumbs only.
- The key that activates a layer is `&trans` in that layer.

**No preprocessor macros in `charybdis.keymap` — not even layer-index `#define`s.** The keymap editor (nickcoutsos.github.io/keymap-editor) does not parse them (its author's wiki: "I don't support … parsing keymaps that use these macros") and simply stops displaying the keymap. Layout v2 briefly used `#define BASE 0 …`, `LANG_KEY`, `HYPER`, `U_CTRL()`/`U_SUPER()` and the editor went blank; they were replaced by literal values (preprocessed output verified byte-identical). What they meant is now a comment block at the top of the keymap. ZMK's own modifier functions (`LG()`, `LC()`, `LS()`, `LA()`) are fine — the editor understands those. `check_keymap.py` fails on any `#define`.

### Thumb Keys, Modifiers, Shift

```
left thumbs:  48 Space   49 Cmd   50 NAV/Tab        right thumbs: 51 Bspc/Hyper 52 Space
              53 Alt     54 FUN/Lang                              55 NUM/Enter
outer column: 12 Tab, 24 Ctrl/Esc (&mt), 36/47 Shift (tap-dance); 23 = [, 35 = ' (no right-hand mods)
```

- `&lt` (thumbs only): `balanced`, `tapping-term-ms=200`, `quick-tap-ms=175`, **no `require-prior-idle-ms`** — with it, a layer thumb pressed right after a letter would resolve as its tap (Tab/Enter) instead of the layer. The old value 40 was there for layer-taps on letters, which no longer exist.
- 51 is `hyper_bspc` (own hold-tap): tap = Backspace, hold = **Hyper** (`LS(LA(LC(LGUI)))` = Ctrl+Alt+Shift+Super), used for app-launch shortcuts — Hyper+T etc. through the GNOME extension Run or raise on Ubuntu, BetterTouchTool on the Mac. Not Right Alt: on this Ubuntu `Alt_R` and `Alt_L` are both `mod1`, GNOME cannot tell them apart, so RAlt+T would also fire from the left Alt (53) and clash with Alt+letter menu mnemonics. Unlike the layer thumbs it **does** have `require-prior-idle-ms = 150`: Backspace right after a letter resolves instantly as Backspace (and auto-repeats if held), so a typing roll cannot turn into Hyper+letter and launch an app. A modifier-keycode base (LGUI) makes ZMK treat all four mods as explicit, so they stay held while the next key is pressed.
- **The keyboard is used ~95 % on Ubuntu** (via a plain KVM; macOS the rest). Ubuntu has `ctrl:swap_lwin_lctl` set in GNOME (`dconf /org/gnome/desktop/input-sources/xkb-options`, i.e. Tweaks → additional layout options): the keyboard's LGUI arrives as **Ctrl** and LCTRL as **Super**. So Cmd on 49 is Ctrl on Ubuntu and Cmd on macOS — copy/paste work the same on both. Firmware shortcuts aimed at Ubuntu are therefore written as `LG(k)` for Ctrl+k and `LC(k)` for Super+k (explained in the comment block at the top of the keymap) — **NAV depends on this swap**; if it is ever removed, every `LG(`/`LC(` in NAV has to be swapped. Hyper contains both mods, so it is unaffected.
- `&mt` (only 24 Ctrl/Esc): `balanced`, 200, 175. If Ctrl+C rolls come out as `Esc c`, switch to `hold-preferred`.
- Shifts are `td_shift_l`/`td_shift_r` tap-dances: hold or with another key = Shift (resolves immediately on interrupt), double tap = `&caps_word`. A lone held Shift reaches the host after 200 ms.
- The language key (tap 54) is `LC(SPACE)` and works on **both** systems: macOS sees Ctrl+Space (previous input source); Ubuntu, through the swap, sees Super+Space = its `switch-input-source`.
- Combos (`-` U+I, `=` I+O, `]` O+P, `\` [+', studio unlock `` ` ``+Bspc) are `layers = <0>` (BASE only), so they do not fire while any other layer — including the auto mouse layer — is on top. The four symbol combos have `require-prior-idle-ms = 100`, `timeout-ms = 40`.

### Trackball CPI Settings

**If the pointer ever needs slowing below what CPI allows, use `&zip_xy_scaler`, never `CPI_DIVIDOR`.** It also gives finer steps than CPI's jumps of 200 — any fraction with both parts ≤16. Not currently in use. The scaler sits on the input listener in `charybdis_right.overlay` and ships with `track-remainders`, so fractions carry over instead of being discarded. `CPI_DIVIDOR` divides integers inside the driver *before* the remainder accumulator and reintroduces the slow-speed stiction documented above. The scaler also runs after the driver, so the acceleration thresholds (counts/ms) keep firing at the same physical ball speeds — lowering CPI instead shifts the whole curve out of reach. It targets `REL_X`/`REL_Y` only: scroll and caret are unaffected.

Also note `SNIPE_CPI` cannot go below 200 — that is the sensor's floor. Halving snipe is only possible via the scaler.

**Since Oct 2026 the keyboard goes through a plain KVM, not DeskHop — so the OS pointer settings apply again.** DeskHop handed the host absolute coordinates, which bypassed the OS speed/acceleration. Now Ubuntu sees an ordinary relative mouse, and GNOME's adaptive profile would stack on top of the firmware curve. **Check the OS acceleration before tuning anything here** — it must be flat (Settings → Mouse → Mouse Acceleration off) so the firmware is the only acceleration stage. As of Nov 2026 it is flat with the speed slider at 0. Read the real values with `xinput list-props "ZMK Project Charybdis DGL Mouse"`; `gsettings` in this shell has reported values that do not match. Flat is one constant factor, so the slider scales the whole curve without changing its shape; raising it also makes every firmware count a coarser cursor step at a crawl. The same lesson was learnt once with DeskHop's own acceleration: CPI got dragged 1200 → 600 and a scaler was added to cancel out a second stage that had nothing to do with the keyboard.

Effective cursor speed = `CPI / CPI_DIVIDOR`. CPI range: 200–3200, and the sensor register is `cpi / 200`, so **CPI is quantised to multiples of 200** — a value like 1100 silently becomes 1000.

**Keep `CPI_DIVIDOR` at 1 and set resolution via CPI.** The divisor is an integer division applied to the raw delta *before* `apply_acceleration()` and its Q16.16 remainder accumulator, so the fractional part is discarded rather than carried. With a divisor of 2 a slow roll producing `raw=1` per poll yields `1/2 = 0` — sensitivity drops the slower you move, which is the opposite of what the acceleration curve is for. This was the case until Aug 2026 (`CPI=2200`, `CPI_DIVIDOR=2`).

Current settings in `charybdis_right.conf`:
- Normal: `CPI=600`, `CPI_DIVIDOR=1` → ~60 effective at a crawl, ~760 at 50 mm/s, up to 4200 on a hard flick (power curve)
- Snipe: `SNIPE_CPI=200`, then halved by a layer-scoped `&zip_xy_scaler 1 2` → **100 effective**, no acceleration

200 is the sensor's floor (the register is `cpi / 200`), so slowing snipe further is only possible with a scaler. It is attached as a child node of `trackball_listener` with `layers = <2>` so it applies to the snipe layer only — a global scaler would drag the normal mode down too. **That layer number is duplicated between the override and the driver's `snipe-layers` property; renumbering layers without updating both leaves snipe silently un-scaled, and the build still succeeds.**
- Snipe: `SNIPE_CPI=200` (low speed for precision, no acceleration) — 200 is both the range minimum and the real value the old `250` resolved to
- Scroll tick: `18` (~0.76 mm of ball travel per wheel tick at 600 CPI), Caret tick: `20`
- **`ACCEL_SLOW_SPEED`/`ACCEL_LOW_SPEED`/`ACCEL_HIGH_SPEED` are in counts/ms, a sensor unit — so changing CPI silently moves the acceleration curve in *physical* terms.** To keep the *feel* after a CPI change, scale all three thresholds by the same ratio.
- Scroll mode runs at `CONFIG_PMW3610_CPI`, **not** `SNIPE_CPI` — so changing the normal-mode CPI silently rescales scrolling too. Adjust `SCROLL_TICK` proportionally to keep the scroll feel unchanged. Caret mode uses `SNIPE_CPI` and is unaffected.
- `ORIENTATION_90=y`, `INVERT_X=y`

### Bluetooth

- 5 BT channels selectable via `BT_SEL 0–4` on the FUN layer (Q–T)
- `BT_CLR` clears current channel, `BT_CLR_ALL` clears all pairings
- Deep sleep disabled: `CONFIG_ZMK_SLEEP=n`
- TX power boosted: `CONFIG_BT_CTLR_TX_PWR_PLUS_8=y`

Two non-obvious settings were needed to make BLE usable on Linux (Aug 2026, Intel AX-series adapter, BlueZ 5.72). Both were found by measurement, and neither is guessable from the symptom:

**`CONFIG_BT_CTLR_PHY_2M=n`** (in `charybdis.conf`) — without it, pairing fails outright on Intel AX200/AX201. Documented ZMK workaround for that chipset family. Side effect: the link runs at 1M PHY, so packets take twice as long on air. Not a bottleneck for HID reports (11 bytes), but it is why `LE 2M PHY` is absent from the negotiated feature set. Worth revisiting only if BLE throughput ever becomes the limit.

**`CONFIG_BT_PERIPHERAL_PREF_LATENCY=0`** (in `charybdis_right.conf`, right half only) — ZMK defaults this to 30, which lets the peripheral sleep through connection events. Correct for a keyboard, wrong for a trackball streaming 125 reports/s. Symptom was a cursor that felt like ~30 Hz over BLE while being perfectly smooth over USB.

The diagnosis is worth remembering because the obvious suspects were wrong twice. `btmon` showed the connection interval was already fine (11.25 ms) and *no reports were being dropped* — 131/s arrived, matching the sensor rate. The problem was purely distribution: reports landed in bursts of 6–9 with gaps of exactly 5–6 × the connection interval, i.e. 19 bursts/s. Exact multiples of the interval mean the peripheral is skipping connection events — that fingerprint points at latency, not at bandwidth, interference, or the host's connection parameters.

To re-measure: `sudo btmon -w /tmp/bt.log` while moving the ball, then `btmon -r /tmp/bt.log | grep -B1 "Handle Value Notification" | grep "ACL Data RX"` and look at the gaps between timestamps.

Set against this: latency 0 keeps the right half's radio awake every 11.25 ms, so it costs battery. If that becomes a problem, latency 2–3 is the compromise — shorter bursts rather than none.

## Common Edits

- **Change a keybinding**: edit `config/charybdis.keymap`
- **Change trackball sensitivity**: edit `CONFIG_PMW3610_CPI` / `CONFIG_PMW3610_CPI_DIVIDOR` in `config/boards/shields/charybdis/charybdis_right.conf`
- **Tune acceleration**: edit `CONFIG_PMW3610_ACCEL_*` in `config/boards/shields/charybdis/charybdis_right.conf`
- **Disable acceleration**: set `CONFIG_PMW3610_ACCEL_ENABLED=n` in `charybdis_right.conf`
- **Add a combo**: add a `combo_*` block in the `combos` section of `charybdis.keymap`
- **Add/modify a layer**: add a node `xxx_layer { display-name = "XXX"; bindings = <…>; }` in `keymap {}` (no `#define` — the keymap editor cannot parse macros); if it shifts indices, update the overlays (both sets) and run `notes/check_keymap.py`. Changing the number or order of layers needs `settings_reset` on every device of the set.
- **Toggle debug logging**: `CONFIG_ZMK_USB_LOGGING` and the log-level configs at the bottom of `charybdis_right.conf` — commented out by default. All three `LOG_DBG` calls in the driver sit inside `pmw3610_report_data()`, i.e. the 125 Hz hot path, so leaving DBG on costs a string format per poll while the ball moves. With `ZMK_LOG_LEVEL_DBG` off they are compiled out entirely. Re-enable only while debugging.
- **Enable RGB underglow**: uncomment the `CONFIG_ZMK_RGB_UNDERGLOW` block in `config/charybdis.conf`

## Architecture Decisions

- 2026-11 The pointer curve is a **single power formula in the driver**, not zones and not the OS. Zones with a sub-1× slow zone came first and stay as a switchable option; the power curve won by feel, against the prediction that losing the stable middle would hurt, so judge curves in the hand rather than from the table. OS acceleration stays flat, so there is one curve to tune and it behaves the same on both hosts behind the KVM. (Pointer Acceleration section)
- 2026-11 To type right after moving the ball, the mouse layer has a **`&to 0` on Space** instead of moving the clicks off the home row. The move was tried for a day (J is the frequent Russian «о») and reverted: the clicks belong under the home-row fingers. (Auto Mouse Layer section)
- 2026-10 SYM layer dropped after a day of use — symbols are typed from their touch-typing positions (Shift + number row, NUM). Its thumb (51) became Backspace/**Hyper** for app-launch shortcuts; Hyper rather than Right Alt because Linux cannot tell left and right Alt apart. (Thumb Keys section)
- 2026-10 Layout v2: **layer-taps moved off letters onto the thumbs**; snipe/scroll became `&mo` inside the auto mouse layer (hold K/L), caret moved to NAV. Typing never waits on a hold-tap decision anymore. Rollout was staged (combos/Caps Word → K/L on MOUSE → mods → layers) so each step could be got used to. (Layer Map / Thumb Keys sections)

- 2026-09 Dongle variant lives in a **separate shield directory with duplicated matrix/layout**, not a shared dtsi with conditionals — a broken dongle build must not be able to reach the working direct-BLE build. (Dongle Variant section)
- 2026-09 Caret on the dongle is a **custom input processor**, not the driver's caret — processors run on whichever device holds the keymap, which is the only place keycodes can be raised. Two implementations now coexist and must be kept in sync. (Dongle Variant section)
- 2026-09 Battery visibility over USB is solved by a **tiny event-subscriber logging module** rather than the PROXY option — PROXY only helps over BLE and has a known 3-part build bug. (Battery Level Logging section)
- 2026-08 Pointer speed below CPI's floor goes through **`&zip_xy_scaler` with `track-remainders`**, never `CPI_DIVIDOR` — the divisor truncates before the remainder accumulator and reintroduces slow-speed stiction. (Trackball CPI Settings section)
- 2026-08 All three trackball accumulators (cursor remainder, scroll, caret) **subtract the threshold and carry the remainder** instead of zeroing — zeroing produced inverse acceleration, up to 77% loss on a fast flick. (Scroll Mode / Caret Mode sections)

## Known Gotchas

Most gotchas are documented where they bite, in the topical sections above. The ones most likely to be hit on the next edit:

- **Layer numbers are duplicated in four places** and the build does not check them: driver `*-layers` in `charybdis_right.overlay`, the snipe scaler override in the same file, the four layer overrides in `charybdis_dongle.overlay`, and the keymap order itself. `keymap-editor[bot]` can renumber layers without touching the overlays; the build still passes and a mode silently stops working. **Run `python3 notes/check_keymap.py` after any keymap or overlay edit and after pulling a bot commit** — it cross-checks all four, plus 56 bindings per layer, `&lt`/`&mo` targets, layer holders leading to the right layer by `display-name`, no `#define`, plain letters on BASE, holder keys transparent in their layer, mouse-below-modes and identical `excluded-positions` in both sets. Which keymap layer plays which trackball role is matched by node name (`ROLE_LAYERS` at the top of the script) — update that table if a layer is renamed.
- **A layer-scoped input processor cannot suppress an event by returning `ZMK_INPUT_PROC_STOP`** — `filter_with_input_config()` discards the override's return value. Zero `event->value` instead. (Dongle Variant section)
- **`ZMK_KEYBOARD_NAME` must be ≤15 characters** — `BT_DEVICE_NAME_MAX` is 16 and the Zephyr assert is strict. "Charybdis Dongle" (16) fails to build with an opaque `_Static_assert` in `hci_core.c`.
- **`zmk,input-split` nodes need a `splits { #address-cells=<1>; #size-cells=<0>; }` parent** — a `@0`/`reg=<0>` node directly under `/` fails at cmake with no useful message.
- **CI's board-variant check produces a false error when the build fails earlier** — "board is not set up for ZMK" just means `.config` was never written. Look above `Configuring incomplete` for the real cause.
- **Check the host's own pointer acceleration before tuning firmware** — a whole round of CPI tuning was once spent cancelling out a second acceleration stage that lived in the KVM (DeskHop). Since the switch to a plain KVM, GNOME's acceleration profile is that second stage.

## Current State

- **Last completed (Nov 2026):** trackball tuning on the dongle set. The power curve replaced the zones and felt right on hardware. Floor 0.1× and ceiling 7× are built (CI green) but the user has not yet reported on them. On the mouse layer both Space keys are now `&to 0`.
- **Being tried (Nov 2026):** the mouse layer has no timeout, it drops only on Space or another letter (Auto Mouse Layer section). Not yet judged on hardware; to go back, `0` → `800` in both overlays.
- **keymap-drawer workflow:** added Nov 2026; parse and draw were checked locally with 0.23.0, the workflow itself has not run in CI yet.
- **Trackball tuning currently:** `CPI=600`, **power curve** (EXP `85`, floor `10`, HIGH `880`, MAX `700`). Zone curve kept in the configs for going back: CRAWL `50`/`14`, MIN `30`, MID `125`, SLOW/LOW `75/200`, plus HIGH `1000` and MAX `780` to restore, quadratic. Dongle scroll divisor `23`, `SCROLL_TICK=18`, snipe `200` halved to 100 by scaler (dongle: scaler `1/4`), caret tick `20` (driver) / `75` (dongle processor).
- **Layout v2** is merged into `Charybdis_4x6` and in use on the dongle set, 7 layers; plan in `notes/LAYOUT_V2_PLAN.md`, what moved where in `notes/LAYOUT_V2_CHANGELOG.md`. Rollback point = `6fe26fa` (last commit before v2).
- **Host side (Ubuntu):** Hyper+letter app shortcuts live in the GNOME extension **Run or raise** (`~/.config/run-or-raise/shortcuts.conf`, not in this repo; reload = disable/enable the extension): V VS Code, C Claude desktop, F Files (Nautilus), J Chrome, W WezTerm, D DBeaver, L LOOP, T Telegram. The extension's default example bindings (Super+F/R/Y/E…) were removed; the original file is `shortcuts.conf.bak`.
- **Not confirmed on hardware:** the direct-BLE set since layout v2 (it builds from the same keymap and curve; the user flashes one set at a time). On the dongle set under the power curve, scroll and caret are compensated only for a constant 1.25×, so they change with speed.
- **Printed A5 sheet** `~/Downloads/charybdis-hotkeys-a5.pdf` does not show the Space return. Its source was in the scratchpad and is gone, so a new one has to be made from scratch. The HTML cheatsheet in `notes/` is current.
- **Open question:** F1 sits on the `` ` `` key (plan's layer spec and the old snipe layer) although the plan's checklist says "54 + 1 = F1".
- **Battery:** right half's reported charge is a constant ~24 % and not a measurement (see Battery Level Logging); only the left half's number is real.
- **Working tree:** two old serial logs (`battery_charibdis.txt`, `battery log.txt`) are committed to the repo root and are cleanup candidates for `notes/`. Untracked `new_chat.md` is a September handoff, out of date.
- **Key files:** `build.yaml`, `config/charybdis.keymap`, `config/boards/shields/charybdis/charybdis_right.{overlay,conf}`, `config/boards/shields/charybdis_dongle/charybdis_dongle.overlay`, `config/boards/shields/charybdis_dongle/charybdis_right_dongle.conf`, `zmk-pmw3610-driver-main/src/{pmw3610.c,input_processor_caret.c,battery_log.c}`, `notes/{check_keymap.py,build_cheatsheet.py}`.
