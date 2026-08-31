# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a ZMK firmware configuration for the Charybdis 4x6 split ergonomic keyboard with a PMW3610 trackball sensor, running on nice!nano v2 (nRF52840) controllers.

## Building

Builds are handled exclusively via **GitHub Actions** — there is no local build setup. Push changes to trigger a build, or use the "Run workflow" button on the Actions tab.

The workflow (`build.yaml`) compiles three firmware artifacts:
- `charybdis_left` — left half
- `charybdis_right` — right half
- `settings_reset` — used to clear pairing data before re-flashing

To flash: put the nice!nano into bootloader mode (double-tap reset), drag the `.uf2` file onto the mounted drive. **Always flash `settings_reset` to both halves first, then flash left/right firmware.**

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
| `zmk-pmw3610-driver-main/` | Vendored PMW3610 driver (local copy, not fetched via west) |

Note: `zmk-for-charybdis-Charybdis_4x6 original/` at the repo root is a frozen copy of the original seller firmware, kept only as a reference for diffing against upstream defaults. It is not built and should not be edited.

Note: `notes/` holds archived historical docs (seller manual, early spec drafts, an old ASCII cheatsheet). They describe earlier keymap revisions and are **not** accurate for the current firmware — see `notes/README.md`. Don't cite them as current behaviour; the hardware sections of `notes/instruction.md` (flashing, switch replacement) do still apply.

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

Plateau-style acceleration is implemented in the vendored PMW3610 driver. The code is guarded by `CONFIG_PMW3610_ACCEL_ENABLED` and only applies to MOVE mode (not Snipe/Scroll/Caret).

Key locations:
- `zmk-pmw3610-driver-main/Kconfig` — `PMW3610_ACCEL_*` config options
- `zmk-pmw3610-driver-main/src/pixart.h` — `accel_remainder_x/y`, `last_move_time` in `struct pixart_data`
- `zmk-pmw3610-driver-main/src/pmw3610.c` — `apply_acceleration()` function, called before HID report in `pmw3610_report_data()`

The ramp shape between LOW and HIGH is selectable via a Kconfig `choice` — `PMW3610_ACCEL_CURVE_LINEAR` / `_QUADRATIC` / `_SMOOTHSTEP`, applied to `t` in `apply_acceleration()`. All three give 1.0x at LOW and MAX_MULT at HIGH; they differ in between. **Default is quadratic** (`t²`), chosen for a wider honest zone — at 5/12/20 counts/ms it gives 1.09/1.78/3.44 versus linear's 1.66/2.98/4.49. Switch it with one line in `charybdis_right.conf`; the options are listed in a comment there.

Parameters (all x100 because Kconfig doesn't support float):
- `ACCEL_LOW_SPEED` (75 = 0.75 counts/ms) — below this, multiplier = 1.0
- `ACCEL_HIGH_SPEED` (1400 = 14.0 counts/ms) — above this, multiplier = max
- `ACCEL_MAX_MULT` (1000 = 10.0x) — maximum multiplier at high speed. Do not exceed ~15x: `apply_acceleration()` stores the result in an `int16_t` and the sensor delta is 12-bit (max 2047), so 16x overflows.

The thresholds were widened deliberately (Aug 2026): acceleration starts on smaller movements and no longer caps out at 20 counts/ms, so a hard flick keeps gaining. Lowering LOW is cheap specifically because the curve is quadratic — `t²` is flat near the lower threshold, so precise pointing barely notices.

Uses sub-pixel accumulation (Q16.16 fixed-point remainders) to avoid precision loss on small deltas. Speed is delta/dt for stability across variable polling rates.

`dt` is measured in **system timer ticks** (`k_uptime_ticks()`, ~30 µs on nRF52840), not whole milliseconds. Polls land ~8 ms apart, so millisecond resolution rounded `dt` to 7/8/9 and the multiplier jittered on perfectly steady movement — worse the faster you moved, because the ramp is steeper there. Switching to ticks cut the multiplier error 4×at low speed and ~13× at high speed. The field storing the timestamp is `last_move_ticks` — the name carries the unit deliberately; do not feed it milliseconds.

### Caret Mode — Trackball as Text Cursor

Caret mode converts trackball movement into arrow key presses — roll to move the text cursor in any editor/terminal. Implemented in the vendored PMW3610 driver (`pmw3610.c`, inside `pmw3610_report_data()` CURSOR branch).

- Activated by layer 5 (`caret_layer`) — declared in overlay: `caret-layers = <5>;`
- Sensitivity: `CONFIG_PMW3610_CARET_TICK=20` in `charybdis_right.conf` (lower = more responsive)
- Runs at `SNIPE_CPI` (200), not the normal cursor CPI
- Accumulates delta X/Y until threshold, then sends arrow key press/release via `raise_zmk_keycode_state_changed_from_encoded()`

The accumulator works exactly like the scroll one: **the threshold is subtracted and the remainder carried**, and one poll can emit several arrows. It used to zero both accumulators and emit at most one arrow per poll, losing 7–13% of travel at normal speed and ~36% on a fast roll. Axis locking is intentional here too — the firing axis zeroes the other one. `PMW3610_CARET_MAX_TICKS_PER_POLL` is 4 rather than the scroll cap of 32, because each tick is a real key press/release pair and far more expensive than a wheel report. See the scroll-mode section for the full rationale; the two branches should be kept in sync if either is ever touched.

### Auto Mouse Layer — layer index is load-bearing

Trackball motion automatically raises layer 1 (`mouse_layer`, clicks on H/J/K), which drops again 800 ms after the ball stops. Implemented with ZMK's upstream `&zip_temp_layer` input processor, wired up in `charybdis_right.overlay`:

```dts
&trackball_listener { input-processors = <&zip_temp_layer 1 800>; };
&zip_temp_layer {
    require-prior-idle-ms = <200>;
    excluded-positions = <30 31 32 36 47 48 53 54>;
};
```

**Invariant — do not break this:** the auto mouse layer's index must stay **lower** than `snipe`/`scroll`/`caret`. The vendored driver picks the trackball mode from `zmk_keymap_highest_layer_active()` (`get_input_mode_for_current_layer()` in `pmw3610.c`) — *only* the topmost active layer. Give the mouse layer a higher index and holding `D` for scroll leaves the mouse layer on top, so the driver never leaves MOVE mode and scroll/snipe/caret silently stop working while the ball is moving. Nothing fails at build time; it only shows up in the hand. The same trap applies to the driver's own `automouse-layer` property, which is deliberately left disabled (`-1`).

`excluded-positions` has **inverted semantics** — verified in ZMK's `app/src/pointing/input_processor_temp_layer.c`: listed positions do *not* dismiss the layer, everything else does, and an *empty* list means no key ever dismisses it (timeout only). The listed positions are the three clicks plus Shift/GUI/Ctrl/Alt, so that shift-click and cmd-click survive.

Tuning: raise the 800 ms timeout for more clicking comfort, lower it if `H`/`J`/`K` stay clicks too long when you resume typing. `require-prior-idle-ms` guards the other direction — brushing the ball mid-sentence.

### Scroll Mode — accumulator carries its remainder

Scroll mode has no acceleration (`apply_acceleration()` is MOVE-only) and no CPI divisor. Movement accumulates into `scroll_delta_x/y`; every `CONFIG_PMW3610_SCROLL_TICK` (70) counts emits one wheel tick.

The accumulator **subtracts the threshold and carries the remainder**, and emits as many ticks as accumulated in one poll. It used to zero the accumulator outright and emit at most one tick per poll, which lost everything above the threshold — the faster you spun the ball, the more was dropped (measured: ~8% lost at moderate speed, ~42% on a flick, ~77% on a hard flick). That is an *inverse* acceleration, the same class of bug as the old `CPI_DIVIDOR=2` truncation.

**Axis locking is deliberate:** the axis that fires zeroes the *other* accumulator, so vertical scrolling suppresses horizontal drift. Do not "fix" this — on a trackball it is very hard to roll straight up without sideways drift. Only the firing axis carries its remainder.

`PMW3610_SCROLL_MAX_TICKS_PER_POLL` (32, in `pmw3610.h`) caps the burst per poll; anything beyond stays in the accumulator for the next poll, so no motion is lost. `PMW3610_SCROLL_TICK` has a Kconfig `range 1 1000` because the accumulator divides by it.

### ZMK Studio

The right shield build includes `snippet: studio-rpc-usb-uart` and `-DCONFIG_ZMK_STUDIO=y` in `build.yaml` (left half does not). This enables live keymap editing via ZMK Studio over USB. A dedicated combo (`combo_studio_unlock` in `charybdis.keymap`, GRAVE + BACKSPACE) calls `&studio_unlock` to allow the Studio connection to write to the keyboard — without it, Studio can view but not modify the keymap.

**The keymap has a second author.** Alongside manual edits, `config/charybdis.keymap` is rewritten by the keymap editor and pushed straight to the branch as commits from `keymap-editor[bot]` (e.g. `similar to corne`, `new position for brackets`, `removed home row`). Consequences to keep in mind:

- **Always `git pull` before touching the keymap.** The remote branch may have moved even if nothing local changed. Re-read `charybdis.keymap` after pulling rather than trusting an earlier read in the same session — layers have been added and thumb keys reassigned this way.
- **The keymap file is the single source of truth.** Layer tables in this file and in `README.md` are hand-maintained snapshots that drift whenever the bot pushes; verify against the actual bindings before relying on them, and treat a mismatch as the docs being stale, not the keymap.
- **Bot commits are formatting-blind.** They rewrite the whole `bindings` block, so hand-written comments and alignment inside a layer may not survive. Put durable explanations outside the layer blocks (or in this file) rather than inline.

### ZMK Board Variant — Breaking Change

ZMK introduced a board variant system. The nice_nano board must be specified as `nice_nano@2.0.0/nrf52840/zmk` in `build.yaml` (not just `nice_nano@2.0.0`). The `/zmk` variant sets `CONFIG_ZMK_BLE=y` which is required for split BLE. Without it, builds fail with linker errors about `ZMK_SPLIT_ROLE_CENTRAL`.

### Layer Map

| Index | Name | Activation |
|-------|------|-----------|
| 0 | QWERTY | Default |
| 1 | mouse_layer | **Automatic** — raised by trackball motion (see Auto Mouse Layer below) |
| 2 | snipe-layers | `lt 2` on F, J, COMMA (snipe trackball mode) |
| 3 | scroll-layers | `lt 3` on D, K, DOT (scroll trackball mode) |
| 4 | BT_layers | `lt 4` on B (Bluetooth channel management) |
| 5 | caret_layer | `lt 5` on S, L (trackball moves text cursor) |
| 6 | corne_1 | `mo 6` on left thumb (3rd key) — HJKL → arrow keys, vim-style |
| 7 | corne_2 | `mo 7` on right thumb (1st key) — HJKL → mouse move/click/scroll, no trackball needed |

Trackball layer modes are declared in the overlay:
```dts
scroll-layers = <3>;
snipe-layers = <2>;
caret-layers = <5>;
```

Layers 6/7 (`corne_1`/`corne_2`) are unrelated to the trackball — they're momentary (`&mo`) layers added later ("similar to corne" commit) that mimic mouse-less navigation/mouse-emulation from the maintainer's Corne keyboard, activated purely from the thumb cluster.

### Home Row & Thumb Keys

Row 2 (home row) is entirely `&lt` (layer-tap) into trackball modes — there are no home-row modifiers:
- Left home row: `A` (plain), `S` → caret (layer 5), `D` → scroll (layer 3), `F` → snipe (layer 2)
- Right home row: `J` → snipe (layer 2), `K` → scroll (layer 3), `L` → caret (layer 5), `;` (plain)
- While the auto mouse layer is up, `J`/`K` are clicks rather than layer-taps — snipe/scroll stay reachable from the left hand (`F`/`D`)
- Thumbs are plain `&kp` (not hold-tap): left = GUI, SPACE, CTRL, ALT; right = SPACE, ENTER — plus `&mo 6`/`&mo 7` on the remaining two thumb keys for the corne_1/corne_2 layers above.

`&lt` is configured with `tapping-term-ms=200`, `quick-tap-ms=130`, `require-prior-idle-ms=40`. The keymap also declares an `&mt` (mod-tap) behavior block with the same tuning, but as of the current keymap no binding actually uses `&mt` — it's dead configuration from an earlier layout revision (thumb mod-taps were replaced with plain keypresses).

### Trackball CPI Settings

**To slow the pointer below what CPI allows, use `&zip_xy_scaler`, never `CPI_DIVIDOR`.** The scaler sits on the input listener in `charybdis_right.overlay` and ships with `track-remainders`, so fractions carry over instead of being discarded. `CPI_DIVIDOR` divides integers inside the driver *before* the remainder accumulator and reintroduces the slow-speed stiction documented above. The scaler also runs after the driver, so the acceleration thresholds (counts/ms) keep firing at the same physical ball speeds — lowering CPI instead shifts the whole curve out of reach. It targets `REL_X`/`REL_Y` only: scroll and caret are unaffected.

Also note `SNIPE_CPI` cannot go below 200 — that is the sensor's floor. Halving snipe is only possible via the scaler.

The keyboard is used through a **DeskHop** USB KVM, which hands the host absolute coordinates. That bypasses the OS pointer-speed sliders on both macOS and Ubuntu, so `CONFIG_PMW3610_CPI` is the *only* place cursor speed can be adjusted — which is why it sits lower than the sensor's default.

Effective cursor speed = `CPI / CPI_DIVIDOR`. CPI range: 200–3200, and the sensor register is `cpi / 200`, so **CPI is quantised to multiples of 200** — a value like 1100 silently becomes 1000.

**Keep `CPI_DIVIDOR` at 1 and set resolution via CPI.** The divisor is an integer division applied to the raw delta *before* `apply_acceleration()` and its Q16.16 remainder accumulator, so the fractional part is discarded rather than carried. With a divisor of 2 a slow roll producing `raw=1` per poll yields `1/2 = 0` — sensitivity drops the slower you move, which is the opposite of what the acceleration curve is for. This was the case until Aug 2026 (`CPI=2200`, `CPI_DIVIDOR=2`).

Current settings in `charybdis_right.conf`:
- Normal: `CPI=600`, `CPI_DIVIDOR=1`, then halved by `&zip_xy_scaler 1 2` → **300 effective**, up to 3000 with acceleration
- Snipe: `SNIPE_CPI=200`, also halved by the scaler → **100 effective**
- Snipe: `SNIPE_CPI=200` (low speed for precision, no acceleration) — 200 is both the range minimum and the real value the old `250` resolved to
- Scroll tick: `35` (~1.5 mm of ball travel per wheel tick at 600 CPI), Caret tick: `20`
- **`ACCEL_LOW_SPEED`/`ACCEL_HIGH_SPEED` are in counts/ms, a sensor unit — so lowering CPI silently moves the acceleration curve in *physical* terms.** At 1200 CPI a 600 mm/s roll hit the 6x ceiling; at 600 CPI the same roll only reaches 2.1x, and the ceiling now needs ~1185 mm/s (11 ball revolutions/s), which is not reachable by hand. The thresholds have deliberately not been rescaled — the goal was a slower pointer overall. To restore the previous *feel* at a lower CPI, scale both thresholds by the same ratio as the CPI change.
- Scroll mode runs at `CONFIG_PMW3610_CPI`, **not** `SNIPE_CPI` — so changing the normal-mode CPI silently rescales scrolling too. Adjust `SCROLL_TICK` proportionally to keep the scroll feel unchanged. Caret mode uses `SNIPE_CPI` and is unaffected.
- `ORIENTATION_90=y`, `INVERT_X=y`

### Bluetooth

- 5 BT channels selectable via `BT_SEL 0–4` in BT layer
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
- **Add/modify a layer**: add a new layer entry in `keymap {}` in `charybdis.keymap` and update the layer index references in the overlay if it's a trackball mode layer
- **Toggle debug logging**: `CONFIG_ZMK_USB_LOGGING` and the log-level configs at the bottom of `charybdis_right.conf` — commented out by default. All three `LOG_DBG` calls in the driver sit inside `pmw3610_report_data()`, i.e. the 125 Hz hot path, so leaving DBG on costs a string format per poll while the ball moves. With `ZMK_LOG_LEVEL_DBG` off they are compiled out entirely. Re-enable only while debugging.
- **Enable RGB underglow**: uncomment the `CONFIG_ZMK_RGB_UNDERGLOW` block in `config/charybdis.conf`
