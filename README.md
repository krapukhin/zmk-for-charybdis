# ZMK Config for Charybdis 4x6 — Trackball Acceleration & Caret Mode

ZMK firmware configuration for the **Charybdis 4x6** split ergonomic keyboard with PMW3610 trackball, running on **nice!nano v2** controllers.

**Tested with ZMK main (March 2026) / Zephyr 4.1**

---

## Pointer Acceleration

Plateau-style pointer acceleration for the trackball: slow movements stay precise, fast movements are amplified up to a configurable multiplier. The algorithm has three zones:

```
speed <= low   ->  multiplier = 1.0x  (no acceleration)
low < speed < high ->  linear interpolation from 1.0x to max
speed >= high  ->  multiplier = max   (plateau)
```

Sub-pixel accumulation prevents precision loss on small deltas, and speed is calculated as counts/ms (delta / time between polls) for stable behavior regardless of polling rate.

**Current settings** in [`charybdis_right.conf`](config/boards/shields/charybdis/charybdis_right.conf):

```conf
CONFIG_PMW3610_ACCEL_ENABLED=y
CONFIG_PMW3610_ACCEL_LOW_SPEED=300     # 3.0 counts/ms — below this, no acceleration
CONFIG_PMW3610_ACCEL_HIGH_SPEED=2000   # 20.0 counts/ms — above this, max acceleration
CONFIG_PMW3610_ACCEL_MAX_MULT=400      # 4.0x max multiplier
```

(Values are x100 because Kconfig doesn't support floats.)

**Tuning tips:**
- Cursor accelerates too aggressively -> increase `ACCEL_HIGH_SPEED` or decrease `ACCEL_MAX_MULT`
- Slow movements already feel accelerated -> increase `ACCEL_LOW_SPEED`
- Not enough difference between slow and fast -> increase `ACCEL_MAX_MULT`

Acceleration only applies to MOVE mode — Snipe, Scroll, and Caret modes are unaffected.

### How to add acceleration to your own ZMK trackball build

All acceleration code lives in the vendored PMW3610 driver — three files:

| File | What was added |
|------|---------------|
| [`zmk-pmw3610-driver-main/Kconfig`](zmk-pmw3610-driver-main/Kconfig) | `PMW3610_ACCEL_*` config options |
| [`zmk-pmw3610-driver-main/src/pixart.h`](zmk-pmw3610-driver-main/src/pixart.h) | `accel_remainder_x/y`, `last_move_time` fields in `struct pixart_data` |
| [`zmk-pmw3610-driver-main/src/pmw3610.c`](zmk-pmw3610-driver-main/src/pmw3610.c) | `apply_acceleration()` function + call before HID report |

To port to your build:
1. Copy the `#ifdef CONFIG_PMW3610_ACCEL_ENABLED` blocks from those three files
2. Add `CONFIG_PMW3610_ACCEL_ENABLED=y` and tuning parameters to your shield's `.conf`
3. That's it — no overlay or devicetree changes needed

---

## Caret Mode — Trackball as Text Cursor

Caret mode turns the trackball into arrow keys — roll the ball to move the text cursor in any editor, browser input, or terminal. No need to reach for arrow keys or the mouse.

Roll left/right to move character by character, up/down to move line by line. Particularly useful for Vim users or precise text editing.

**Implementation:** `caret-layers = <6>` in [`charybdis_right.overlay`](config/boards/shields/charybdis/charybdis_right.overlay). Sensitivity is controlled by `CONFIG_PMW3610_CARET_TICK=20` in [`charybdis_right.conf`](config/boards/shields/charybdis/charybdis_right.conf) (lower = more responsive).

### How to add caret mode to your own ZMK trackball build

The caret mode logic is built into the vendored PMW3610 driver. To port:

1. In your shield's `.overlay`, add `caret-layers = <N>;` to the trackball node (where N is your caret layer index)
2. In your shield's `.conf`, set `CONFIG_PMW3610_CARET_TICK=20` (adjust to taste)
3. Add a layer in your `.keymap` at index N — the layer content doesn't matter for arrow key generation, but you can put extra bindings there
4. Bind a key to `&lt N <key>` to activate the caret layer on hold

---

## Breaking Change: ZMK Board Variant System

ZMK introduced a board variant system that **broke existing builds**. The nice_nano board must now be specified as:

```yaml
# build.yaml — OLD (broken)
board: nice_nano@2.0.0

# build.yaml — NEW (working)
board: nice_nano@2.0.0/nrf52840/zmk
```

The `/nrf52840/zmk` variant loads ZMK-specific defconfig that sets `CONFIG_ZMK_BLE=y`. Without it, the split BLE role detection fails entirely — you get linker errors for keymap/event functions, and the firmware won't compile.

If you see errors about `ZMK_SPLIT_ROLE_CENTRAL` or missing `keymap.c` symbols after updating ZMK, this is likely the cause.

---

## Features

- **7 layers** — QWERTY base, Snipe, Scroll, F-keys, Bluetooth, Windows/app shortcuts, Caret
- **Pointer acceleration** — plateau-style acceleration in the PMW3610 driver
- **Home Row Mods** — modifiers on the home row, no dedicated modifier keys needed
- **4 trackball modes** — normal cursor, scroll wheel, precision snipe, and text caret control
- **Vendored PMW3610 driver** — works with the 3-wire SDIO hardware wiring found on this keyboard
- **Combos** for brackets and language switching
- RGB underglow support (disabled by default)

---

## Keymap

### Base Layer (QWERTY)

```
┌──────┬──────┬──────┬──────┬──────┬──────┐       ┌──────┬──────┬──────┬──────┬──────┬──────┐
│  `   │  1   │  2   │  3   │  4   │  5   │       │  6   │  7   │  8   │  9   │  0   │ BKSP │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│ TAB  │  Q   │  W   │  E   │  R   │  T   │       │  Y   │  U   │  I   │  O   │  P   │  [   │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│ CAPS │  A   │  S   │  D   │  F   │  G   │       │  H   │  J   │  K   │  L   │  ;   │  '   │
│      │ Ctrl │ Alt  │ GUI  │Shift │      │       │      │Shift │ GUI  │ Alt  │ Ctrl │      │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│SHIFT │  Z   │  X   │  C   │  V   │  B   │       │  N   │  M   │  ,   │  .   │  /   │SHIFT │
│      │      │      │      │[SCR] │[BT]  │       │      │      │[SNP] │[SCR] │      │      │
└──────┴──────┴──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┴──────┴──────┴──────┘
                     │SPACE │  ↑   │  →   │       │ DEL  │SPACE │
                     │[SNP] │      │      │       │[CAR] │      │
                     └──────┼──────┼──────┤       └──────┴──────┘
                            │  ←   │  ↓   │
                            │[CAR] │[F]   │
                            └──────┴──────┘
```

Layer hold keys: `[SCR]` = Scroll, `[SNP]` = Snipe, `[BT]` = Bluetooth, `[CAR]` = Caret, `[F]` = F-keys

---

### Home Row Mods

Hold any home row key to activate the modifier. Tap for the letter.

```
Left hand                     Right hand
┌─────┬─────┬─────┬─────┐    ┌─────┬─────┬─────┬─────┐
│  A  │  S  │  D  │  F  │    │  J  │  K  │  L  │  ;  │
│Ctrl │ Alt │ GUI │Shift│    │Shift│ GUI │ Alt │Ctrl │
└─────┴─────┴─────┴─────┘    └─────┴─────┴─────┴─────┘
```

**Examples:** `Ctrl+C` -> hold A, tap C &nbsp;|&nbsp; `Cmd+V` -> hold F, tap V &nbsp;|&nbsp; `Ctrl+Shift+S` -> hold A+F, tap S

Configured with `tap-preferred` flavor, `tapping-term-ms = 200`, `require-prior-idle-ms = 40` — feels natural at typing speed.

---

### Combos (simultaneous keypresses)

| Keys | Output | Notes |
|------|--------|-------|
| `U` + `I` | `-` | |
| `I` + `O` | `=` | |
| `O` + `P` | `]` | |

---

### Layer Reference

| # | Name | How to activate | Description |
|---|------|----------------|-------------|
| 0 | QWERTY | — | Base layer |
| 1 | Snipe | Hold `,` or `SPACE` | Trackball precision mode |
| 2 | Scroll | Hold `V`, `.`, or `↑` | Trackball -> scroll wheel + arrow keys |
| 3 | F-keys | Hold `↓` (right thumb) | F1-F12, mouse buttons |
| 4 | Bluetooth | Hold `B` | BT channel management |
| 5 | Windows | Hold `←` (right thumb) | App-specific shortcuts (Ctrl+Alt+key) |
| 6 | **Caret** | Hold `DEL` or `←` (left thumb) | **Trackball moves text cursor** |

---

### Trackball Modes

The PMW3610 trackball on the right half has four operating modes, selected by the active layer:

| Mode | Activate | Behavior |
|------|----------|----------|
| **Normal** | default | Mouse cursor with plateau acceleration (~1100 effective CPI, up to 4x at high speed) |
| **Snipe** | Hold `,` or `SPACE` | Low-speed precision (~250 CPI) for exact cursor placement |
| **Scroll** | Hold `V`, `.`, or `↑` | Ball controls scroll wheel; layer also has arrow keys |
| **Caret** | Hold `DEL` or `←` | **Ball moves the text cursor (arrow keys)** |

---

### F-keys Layer (hold `↓`)

```
┌────┬────┬────┬────┬────┬────┐  ┌────┬────┬────┬────┬────┬────┐
│ F1 │ F2 │ F3 │ F4 │ F5 │ F6 │  │ F7 │ F8 │ F9 │F10 │F11 │F12 │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│    │    │    │    │    │    │  │    │    │    │    │    │    │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│    │    │    │    │    │    │  │RClk│LClk│    │    │    │    │
└────┴────┴────┴────┴────┴────┘  └────┴────┴────┴────┴────┴────┘
                                   RClk LClk  (thumbs)
```

### Bluetooth Layer (hold `B`)

| Key combo | Action |
|-----------|--------|
| `B` + `1`-`5` | Switch to BT channel 1-5 |
| `B` + `Z` | Clear ALL pairings |
| `B` + `C` | Clear current channel pairing |
| `B` + `N` | Next BT channel |

### Scroll Layer (hold `V`, `.`, or `↑`)

```
┌──────┬──────┬──────┬──────┬──────┬──────┐  ┌──────┬──────┬──────┬──────┬──────┬──────┐
│      │      │      │      │      │      │  │      │      │      │      │  -   │  =   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │ Home │ PgUp │SCRL↑ │      │      │  ]   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │  ←   │  ↓   │  ↑   │  →   │      │  \   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │ End  │ PgDn │SCRL↓ │      │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┘  └──────┴──────┴──────┴──────┴──────┴──────┘
```

### Snipe Layer (hold `,` or `SPACE`)

Trackball slows to ~250 CPI for precise cursor placement. Layer also provides media keys and bracket pairs on the left half:

```
Left half top row:  Bri- | Bri+ | App switch | Search | Mute | Vol-
Left half row 2:    <    |  {   |    [       |   (    |  )   | Tab
Left half row 3:    (all transparent)
```

---

## File Structure

```
config/
├── charybdis.keymap                         # All layers and key bindings
├── charybdis.conf                           # Global settings (BT, debounce, sleep)
├── west.yml                                 # ZMK dependency manifest
└── boards/shields/charybdis/
    ├── charybdis.dtsi                       # Shared: matrix transform, kscan rows
    ├── charybdis_left.overlay               # Left half: columns, RGB
    ├── charybdis_left.conf                  # Left half config
    ├── charybdis_right.overlay              # Right half: SPI pins, trackball, RGB
    ├── charybdis_right.conf                 # Right half: PMW3610 + acceleration settings
    ├── charybdis.zmk.yml                    # Shield metadata
    ├── Kconfig.shield / Kconfig.defconfig   # Kconfig shield definitions
zmk-pmw3610-driver-main/                    # Vendored PMW3610 driver (local copy)
├── Kconfig                                 #   acceleration config options here
├── src/pixart.h                            #   data structures (accel state)
├── src/pmw3610.c                           #   driver + acceleration logic
build.yaml                                  # GitHub Actions build matrix
.github/workflows/build.yml                 # CI workflow
```

---

## Building & Flashing

Builds run on **GitHub Actions** — no local toolchain needed.

1. Push changes to trigger a build, or use **Actions -> Run workflow**
2. Download the artifacts from the completed workflow run
3. **Flash order (important!):**
   - Flash `settings_reset` to **both halves** first
   - Then flash `charybdis_left` to the left half
   - Then flash `charybdis_right` to the right half

To enter bootloader: double-tap the reset button. The controller appears as a USB drive — drag the `.uf2` file onto it.

---

## Customization

### Trackball Sensitivity

Edit [`config/boards/shields/charybdis/charybdis_right.conf`](config/boards/shields/charybdis/charybdis_right.conf):

```conf
CONFIG_PMW3610_CPI=2200            # Raw sensor CPI (200-3200)
CONFIG_PMW3610_CPI_DIVIDOR=2       # Effective CPI = 2200/2 = 1100
CONFIG_PMW3610_SNIPE_CPI=250       # Snipe mode CPI
CONFIG_PMW3610_SCROLL_TICK=70      # Scroll sensitivity (higher = slower)
CONFIG_PMW3610_CARET_TICK=20       # Caret mode sensitivity (lower = more responsive)
```

### Adding Combos

In [`config/charybdis.keymap`](config/charybdis.keymap), add a block inside `combos { }`:

```dts
combo_name {
    timeout-ms = <50>;
    key-positions = <X Y>;   // key indices from the matrix
    bindings = <&kp KEYCODE>;
};
```

### Enabling RGB Underglow

Uncomment the RGB block in [`config/charybdis.conf`](config/charybdis.conf):

```conf
CONFIG_ZMK_RGB_UNDERGLOW=y
CONFIG_WS2812_STRIP=y
CONFIG_LED_STRIP=y
```

Left half has 29 LEDs, right half has 27 LEDs (set in the respective overlays).

### Debug Logging

USB serial logging is currently **enabled** in `charybdis_right.conf`. Disable for production to save power and reduce latency:

```conf
# CONFIG_ZMK_USB_LOGGING=y   <- comment out these lines
# CONFIG_LOG=y
# CONFIG_ZMK_LOG_LEVEL_DBG=y
# CONFIG_SENSOR_LOG_LEVEL_DBG=y
# CONFIG_INPUT_LOG_LEVEL_DBG=y
```

---

## Hardware Notes

### PMW3610 Wiring

This keyboard uses a **3-wire SDIO SPI bus** — MOSI and MISO share the same pin (`P0.17`). The standard Zephyr `pixart,pmw3610` driver requires separate MOSI/MISO lines and does not work with this wiring.

This config uses a **vendored local driver** (`zmk-pmw3610-driver-main/`) with the compatible string renamed to `pixart,pmw3610-zmk` to avoid conflict with the upstream driver. It is injected via:

```yaml
# build.yaml
cmake-args: -DZMK_EXTRA_MODULES=${GITHUB_WORKSPACE}/zmk-pmw3610-driver-main
```

Do **not** add it to `config/west.yml`.

| Signal | Pin |
|--------|-----|
| SCK | P0.08 |
| MOSI/MISO | P0.17 (shared) |
| CS | P0.20 |
| IRQ/MOTION | P0.06 |

### Compatibility

| Component | Version |
|-----------|---------|
| ZMK | main branch (Mar 2026) |
| Zephyr | 4.1.0 |
| Board | `nice_nano@2.0.0/nrf52840/zmk` |

---

## Development Notes

### Why the vendored driver exists

**Problem:** The keyboard periodically froze over Bluetooth and USB. The trackball would drop connection, and only a reset/reconnect restored it.

**Diagnosis:** The hardware has MOSI and MISO wired together on `P0.17` (3-wire SDIO SPI bus). The standard Zephyr `pixart,pmw3610` driver requires separate MOSI/MISO pins and does not support this topology — causing instability. The original seller's firmware uses a separate driver (`zmk-pmw3610-driver`) with `irq-gpios` instead of `motion-gpios`, which is designed for exactly this wiring.

**Solution:** A hybrid approach — keep the custom keymap but use the seller's driver for trackball stability:

1. Vendored `zmk-pmw3610-driver` as a local module (`zmk-pmw3610-driver-main/`)
2. Renamed the compatible string to avoid conflict with the built-in Zephyr driver:
   - `zmk-pmw3610-driver-main/dts/bindings/pixart,pmw3610.yml` -> `compatible: "pixart,pmw3610-zmk"`
   - `zmk-pmw3610-driver-main/src/pmw3610.c` -> `#define DT_DRV_COMPAT pixart_pmw3610_zmk`
   - `charybdis_right.overlay` -> `compatible = "pixart,pmw3610-zmk"`
3. Removed the external module from `config/west.yml`; injected it via `build.yaml` instead:
   ```yaml
   cmake-args: -DZMK_EXTRA_MODULES=${GITHUB_WORKSPACE}/zmk-pmw3610-driver-main
   ```

### Pitfalls encountered

| Error | Fix |
|-------|-----|
| GH Actions: `${{ github.workspace }}` not expanded in `cmake-args` | Use `${GITHUB_WORKSPACE}` (shell variable, not Actions expression) |
| "No board named nice_nano" during build | Use `ZMK_EXTRA_MODULES`, not `ZEPHYR_EXTRA_MODULES` |
| `CONFIG_PMW3610_SNIPE_CPI=100` rejected by Kconfig | Valid CPI range is 200-3200; set a value within range |
| Build broke after ZMK update — missing `ZMK_SPLIT_ROLE_CENTRAL` | Board must be `nice_nano@2.0.0/nrf52840/zmk` (new variant system requires `/zmk` suffix) |

### CPI tuning notes

Effective cursor speed = `CPI / CPI_DIVIDOR`. Multiple combinations can yield the same effective speed but with different motion characteristics (smoothness vs. noise):

```
3200/8 = 400  — more filtering, smoother but less responsive
1600/4 = 400  — balanced
 800/2 = 400  — less filtering, more raw
 400/1 = 400  — no filtering
```
