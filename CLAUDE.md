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

Parameters (all x100 because Kconfig doesn't support float):
- `ACCEL_LOW_SPEED` (300 = 3.0 counts/ms) — below this, multiplier = 1.0
- `ACCEL_HIGH_SPEED` (2000 = 20.0 counts/ms) — above this, multiplier = max
- `ACCEL_MAX_MULT` (400 = 4.0x) — maximum multiplier at high speed

Uses sub-pixel accumulation (Q16.16 fixed-point remainders) to avoid precision loss on small deltas. Speed is delta/dt for stability across variable polling rates.

### Caret Mode — Trackball as Text Cursor

Caret mode converts trackball movement into arrow key presses — roll to move the text cursor in any editor/terminal. Implemented in the vendored PMW3610 driver (`pmw3610.c`, inside `pmw3610_report_data()` CURSOR branch).

- Activated by layer 4 (`caret_layer`) — declared in overlay: `caret-layers = <4>;`
- Sensitivity: `CONFIG_PMW3610_CARET_TICK=20` in `charybdis_right.conf` (lower = more responsive)
- Accumulates delta X/Y until threshold, then sends arrow key press/release via `raise_zmk_keycode_state_changed_from_encoded()`

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
| 1 | snipe-layers | `lt 1` on F, J, COMMA (snipe trackball mode) |
| 2 | scroll-layers | `lt 2` on D, K, DOT (scroll trackball mode) |
| 3 | BT_layers | `lt 3` on B (Bluetooth channel management) |
| 4 | caret_layer | `lt 4` on S, L (trackball moves text cursor) |
| 5 | corne_1 | `mo 5` on left thumb (3rd key) — HJKL → arrow keys, vim-style |
| 6 | corne_2 | `mo 6` on right thumb (1st key) — HJKL → mouse move/click/scroll, no trackball needed |

Trackball layer modes are declared in the overlay:
```dts
scroll-layers = <2>;
snipe-layers = <1>;
caret-layers = <4>;
```

Layers 5/6 (`corne_1`/`corne_2`) are unrelated to the trackball — they're momentary (`&mo`) layers added later ("similar to corne" commit) that mimic mouse-less navigation/mouse-emulation from the maintainer's Corne keyboard, activated purely from the thumb cluster.

### Home Row & Thumb Keys

Row 2 (home row) is entirely `&lt` (layer-tap) into trackball modes — there are no home-row modifiers:
- Left home row: `A` (plain), `S` → caret (layer 4), `D` → scroll (layer 2), `F` → snipe (layer 1)
- Right home row: `J` → snipe (layer 1), `K` → scroll (layer 2), `L` → caret (layer 4), `;` (plain)
- Thumbs are plain `&kp` (not hold-tap): left = GUI, SPACE, CTRL, ALT; right = SPACE, ENTER — plus `&mo 5`/`&mo 6` on the remaining two thumb keys for the corne_1/corne_2 layers above.

`&lt` is configured with `tapping-term-ms=200`, `quick-tap-ms=130`, `require-prior-idle-ms=40`. The keymap also declares an `&mt` (mod-tap) behavior block with the same tuning, but as of the current keymap no binding actually uses `&mt` — it's dead configuration from an earlier layout revision (thumb mod-taps were replaced with plain keypresses).

### Trackball CPI Settings

Effective cursor speed = `CPI / CPI_DIVIDOR`. CPI range: 200–3200.

Current settings in `charybdis_right.conf`:
- Normal: `CPI=2200`, `CPI_DIVIDOR=2` → ~1100 effective (with acceleration up to 4x at high speed)
- Snipe: `SNIPE_CPI=250` (low speed for precision, no acceleration)
- Scroll tick: `70`, Caret tick: `20`
- `ORIENTATION_90=y`, `INVERT_X=y`

### Bluetooth

- 5 BT channels selectable via `BT_SEL 0–4` in BT layer
- `BT_CLR` clears current channel, `BT_CLR_ALL` clears all pairings
- Deep sleep disabled: `CONFIG_ZMK_SLEEP=n`
- TX power boosted: `CONFIG_BT_CTLR_TX_PWR_PLUS_8=y`

## Common Edits

- **Change a keybinding**: edit `config/charybdis.keymap`
- **Change trackball sensitivity**: edit `CONFIG_PMW3610_CPI` / `CONFIG_PMW3610_CPI_DIVIDOR` in `config/boards/shields/charybdis/charybdis_right.conf`
- **Tune acceleration**: edit `CONFIG_PMW3610_ACCEL_*` in `config/boards/shields/charybdis/charybdis_right.conf`
- **Disable acceleration**: set `CONFIG_PMW3610_ACCEL_ENABLED=n` in `charybdis_right.conf`
- **Add a combo**: add a `combo_*` block in the `combos` section of `charybdis.keymap`
- **Add/modify a layer**: add a new layer entry in `keymap {}` in `charybdis.keymap` and update the layer index references in the overlay if it's a trackball mode layer
- **Toggle debug logging**: `CONFIG_ZMK_USB_LOGGING` and related log level configs in `charybdis_right.conf` (currently enabled; disable for production builds)
- **Enable RGB underglow**: uncomment the `CONFIG_ZMK_RGB_UNDERGLOW` block in `config/charybdis.conf`
