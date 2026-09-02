# ZMK Config for Charybdis 4x6 — Trackball Acceleration & Caret Mode

ZMK firmware configuration for the **Charybdis 4x6** split ergonomic keyboard with PMW3610 trackball, running on **nice!nano v2** controllers.

**Tested with ZMK main (March 2026) / Zephyr 4.1**

---

## Pointer Acceleration

Plateau-style pointer acceleration for the trackball: slow movements stay precise, fast movements are amplified up to a configurable multiplier. The algorithm has three zones:

```
speed <= low   ->  multiplier = 1.0x  (no acceleration)
low < speed < high ->  ramp from 1.0x to max, shape selectable
speed >= high  ->  multiplier = max   (plateau)
```

The ramp shape is a Kconfig choice — linear, quadratic (default), or smoothstep:

| speed, counts/ms | 3 | 5 | 8 | 12 | 20 | 30 |
|---|---|---|---|---|---|---|
| linear | 1.85 | 2.60 | 3.74 | 5.25 | 6.00 | 6.00 |
| **quadratic** | 1.14 | 1.51 | 2.50 | 4.60 | 6.00 | 6.00 |
| smoothstep | 1.38 | 2.21 | 3.85 | 5.69 | 6.00 | 6.00 |

Quadratic keeps the multiplier near 1.0 well past the low threshold, so slow and medium movements stay honest and only a genuinely fast roll gets the big gain. Smoothstep sits close to linear in the middle but has no kink at either threshold. Set `CONFIG_PMW3610_ACCEL_CURVE_LINEAR=y` / `_QUADRATIC=y` / `_SMOOTHSTEP=y` — exactly one.

Sub-pixel accumulation prevents precision loss on small deltas, and speed is calculated as counts/ms (delta / time between polls) for stable behavior regardless of polling rate.

**Current settings** in [`charybdis_right.conf`](config/boards/shields/charybdis/charybdis_right.conf):

```conf
CONFIG_PMW3610_ACCEL_ENABLED=y
CONFIG_PMW3610_ACCEL_LOW_SPEED=75      # 0.75 counts/ms — below this, no acceleration
CONFIG_PMW3610_ACCEL_HIGH_SPEED=1400   # 14.0 counts/ms — above this, max acceleration
CONFIG_PMW3610_ACCEL_MAX_MULT=600      # 6.0x max multiplier (do not exceed ~15x, see CLAUDE.md)
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

**Implementation:** `caret-layers = <5>` in [`charybdis_right.overlay`](config/boards/shields/charybdis/charybdis_right.overlay). Sensitivity is controlled by `CONFIG_PMW3610_CARET_TICK=20` in [`charybdis_right.conf`](config/boards/shields/charybdis/charybdis_right.conf) (lower = more responsive).

### How to add caret mode to your own ZMK trackball build

The caret mode logic is built into the vendored PMW3610 driver. To port:

1. In your shield's `.overlay`, add `caret-layers = <N>;` to the trackball node (where N is your caret layer index)
2. In your shield's `.conf`, set `CONFIG_PMW3610_CARET_TICK=20` (adjust to taste)
3. Add a layer in your `.keymap` at index N — the layer content doesn't matter for arrow key generation, but you can put extra bindings there
4. Bind a key to `&lt N <key>` to activate the caret layer on hold

---

## Auto Mouse Layer

Moving the trackball automatically raises a mouse layer with click buttons under `H` / `J` / `K` (right / left / middle). It drops again 800 ms after the ball stops, so the keys go back to being letters. No key is held — you roll the ball, click, and keep typing.

Built on ZMK's upstream [`&zip_temp_layer`](https://zmk.dev/docs/keymaps/input-processors/temp-layer) input processor, configured in [`charybdis_right.overlay`](config/boards/shields/charybdis/charybdis_right.overlay):

```dts
&trackball_listener {
    input-processors = <&zip_temp_layer 1 800>;   // layer 1, 800 ms after the ball stops
};

&zip_temp_layer {
    require-prior-idle-ms = <200>;
    excluded-positions = <30 31 32 36 47 48 53 54>;
};
```

**Tuning:**
- Not enough time to click after aiming -> raise the `800` timeout to 1200–1500
- `H`/`J`/`K` stay clicks too long when you resume typing -> lower it to 400–600
- Layer pops up while touch-typing -> raise `require-prior-idle-ms` to 300

### Two traps worth knowing

**1. The layer index is load-bearing.** The auto mouse layer must sit at a *lower* index than the snipe / scroll / caret layers. The PMW3610 driver selects the trackball mode from `zmk_keymap_highest_layer_active()` — only the topmost active layer. Put the mouse layer above them and holding `D` for scroll leaves the mouse layer on top, so the driver never leaves cursor mode and scroll / snipe / caret quietly stop working while the ball is moving. Nothing fails at build time. That is why the mouse layer is index 1 and everything else shifted up.

**2. `excluded-positions` is inverted.** Listed positions do **not** dismiss the layer; every other key does. And if the list is *empty*, no key dismisses the layer at all — only the timeout. The list here holds the three click keys (so clicking doesn't dismiss the layer under your own finger) plus Shift / GUI / Ctrl / Alt (so shift-click and cmd-click survive). Space and Enter are deliberately left out: pressing space means you're back to typing.

### How to add this to your own ZMK trackball build

1. Add a mouse layer to your keymap at an index **below** your trackball-mode layers — everything on it `&trans` except the click keys
2. Point the processor at it: `input-processors = <&zip_temp_layer N 800>;` on your input listener
3. Set `excluded-positions` to your click keys plus your modifiers, and `require-prior-idle-ms` to ~200
4. Make sure `#include <input/processors.dtsi>` is in your overlay

If your driver has its own automouse (the PMW3610 one does, via `automouse-layer`), leave it disabled — running both at once conflicts.

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

- **8 layers** — QWERTY base, auto mouse, Snipe, Scroll, Bluetooth, Caret, plus two Corne-style auxiliary layers (arrow-key nav and mouse emulation via HJKL, no trackball needed)
- **Pointer acceleration** — plateau-style acceleration in the PMW3610 driver
- **Home-row layer-taps** — `S`/`D`/`F` and `J`/`K`/`L` hold into trackball modes (caret/scroll/snipe); modifiers live on the thumb cluster, not the home row
- **4 trackball modes** — normal cursor, scroll wheel, precision snipe, and text caret control
- **Auto mouse layer** — moving the ball raises a click layer automatically, no key held
- **Vendored PMW3610 driver** — works with the 3-wire SDIO hardware wiring found on this keyboard
- **Combos** for brackets, `=`/`-`, and a ZMK Studio unlock
- **ZMK Studio** support on the right half for live keymap editing over USB
- RGB underglow support (disabled by default)

---

## Keymap

> The keymap is actively edited both by hand and via ZMK Studio (commits from `keymap-editor[bot]`) — `config/charybdis.keymap` is always the source of truth; this section is a snapshot of it.

### Base Layer (QWERTY)

```
┌──────┬──────┬──────┬──────┬──────┬──────┐       ┌──────┬──────┬──────┬──────┬──────┬──────┐
│  `   │  1   │  2   │  3   │  4   │  5   │       │  6   │  7   │  8   │  9   │  0   │ BKSP │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│ TAB  │  Q   │  W   │  E   │  R   │  T   │       │  Y   │  U   │  I   │  O   │  P   │  [   │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│ CAPS │  A   │ S[5] │ D[3] │ F[2] │  G   │       │  H   │ J[2] │ K[3] │ L[5] │  ;   │  '   │
├──────┼──────┼──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┼──────┼──────┼──────┤
│SHIFT │  Z   │  X   │  C   │  V   │ B[4] │       │  N   │  M   │ ,[2] │ .[3] │  /   │SHIFT │
└──────┴──────┴──────┼──────┼──────┼──────┤       ├──────┼──────┼──────┴──────┴──────┴──────┘
                      │ GUI  │SPACE │MO(6) │       │MO(7) │SPACE │
                      └──────┼──────┼──────┤       ├──────┼──────┘
                             │ CTRL │ ALT  │       │ENTER │
                             └──────┴──────┘       └──────┘
```

`[N]` = hold to activate layer N (see [Layer Reference](#layer-reference)). `MO(6)`/`MO(7)` hold into the two Corne-style auxiliary layers.

Layer 1 is missing from this diagram on purpose — it's the auto mouse layer, raised by the trackball rather than by a key.

---

### Home Row & Thumb Keys

Home row carries no modifiers anymore — it's entirely layer-taps into trackball modes:

```
Left hand                     Right hand
┌─────┬─────┬─────┬─────┐    ┌─────┬─────┬─────┬─────┐
│  A  │  S  │  D  │  F  │    │  J  │  K  │  L  │  ;  │
│  —  │Caret│Scrl │Snipe│    │Snipe│Scrl │Caret│  —  │
└─────┴─────┴─────┴─────┘    └─────┴─────┴─────┴─────┘
```

Modifiers instead live on the thumb cluster as plain key presses (not hold-taps): left thumb = `GUI`, `SPACE`, `CTRL`, `ALT`; right thumb = `SPACE`, `ENTER`. The two remaining thumb keys hold into the Corne-nav / Corne-mouse layers below.

Layer-tap keys (`&lt`) are configured with `tap-preferred` flavor, `tapping-term-ms = 200`, `require-prior-idle-ms = 40`.

> Note: the keymap still declares an `&mt` (mod-tap) behavior config block at the top of the file, but no binding uses it anymore — it's dead configuration left over from an earlier layout revision.

---

### Combos (simultaneous keypresses)

| Keys | Output | Notes |
|------|--------|-------|
| `U` + `I` | `-` | |
| `I` + `O` | `=` | |
| `O` + `P` | `]` | |
| `` ` `` + `BKSP` | ZMK Studio unlock | Lets ZMK Studio write keymap changes over USB |

---

### Layer Reference

| # | Name | How to activate | Description |
|---|------|----------------|-------------|
| 0 | QWERTY | — | Base layer |
| 1 | **Auto mouse** | **Automatic** — moving the trackball | **Clicks appear under H/J/K; drops 800 ms after the ball stops** |
| 2 | Snipe | Hold `F` / `J` / `,` | Trackball precision mode; F-keys and bracket pairs on top rows |
| 3 | Scroll | Hold `D` / `K` / `.` | Trackball → scroll wheel + arrow keys |
| 4 | Bluetooth | Hold `B` | BT channel management |
| 5 | **Caret** | Hold `S` / `L` | **Trackball moves text cursor**; top row doubles as media/brightness keys |
| 6 | Corne-nav | Hold left thumb, 3rd key (`MO(6)`) | HJKL → arrow keys (vim-style navigation) |
| 7 | Corne-mouse | Hold right thumb, 1st key (`MO(7)`) | HJKL → mouse movement, with click/scroll on the rows above and below |

---

### Trackball Modes

The PMW3610 trackball on the right half has four operating modes, selected by the active layer:

| Mode | Activate | Behavior |
|------|----------|----------|
| **Normal** | default | Mouse cursor with acceleration (600 CPI, up to 3600 on a fast roll); raises the auto mouse layer |
| **Snipe** | Hold `F` / `J` / `,` | Low-speed precision (200 CPI halved to 100 effective) for exact cursor placement |
| **Scroll** | Hold `D` / `K` / `.` | Ball controls scroll wheel; layer also has arrow keys |
| **Caret** | Hold `S` / `L` | **Ball moves the text cursor (arrow keys)** |

---

### Snipe Layer (hold `F`, `J`, or `,`)

```
┌────┬────┬────┬────┬────┬────┐  ┌────┬────┬────┬────┬────┬────┐
│ F1 │ F2 │ F3 │ F4 │ F5 │ F6 │  │ F7 │ F8 │ F9 │F10 │F11 │F12 │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│    │ <  │ {  │ [  │ (  │TAB │  │⌘⌫  │ )  │ ]  │ }  │ >  │ ]  │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│    │    │    │    │    │    │  │RClk│LClk│    │    │    │ \  │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│    │    │    │    │    │    │  │    │    │    │    │    │    │
└────┴────┴────┴────┴────┴────┘  └────┴────┴────┴────┴────┴────┘
                              thumbs: — — —  |  RClk LClk
```

### Scroll Layer (hold `D`, `K`, or `.`)

```
┌──────┬──────┬──────┬──────┬──────┬──────┐  ┌──────┬──────┬──────┬──────┬──────┬──────┐
│      │      │      │      │      │      │  │      │      │      │      │  -   │  =   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │ Home │ PgUp │SCRL↑ │      │      │  ]   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │  ←   │  ↓   │  ↑   │  →   │      │  \   │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │ End  │ PgDn │SCRL↓ │      │      │      │
└──────┴──────┴──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┴──────┴──────┴──────┘
                      │  ↑   │  →   │      │  │      │
                      └──────┼──────┼──────┤  ├──────┘
                             │  ←   │  ↓   │  │
                             └──────┴──────┘  └──────┘
```

### Bluetooth Layer (hold `B`)

| Key combo | Action |
|-----------|--------|
| `B` + `1`-`5` | Switch to BT channel 1-5 |
| `B` + `A` | Clear ALL pairings |
| `B` + `C` | Clear current channel pairing |
| `B` + `N` | Next BT channel |

### Caret Layer (hold `S` or `L`)

Top row doubles as media/brightness controls while the trackball drives the text cursor; every other key stays transparent (the keyboard types normally):

```
┌──────┬──────┬──────┬──────┬──────┬──────┐  ┌──────┬──────┬──────┬──────┬──────┬──────┐
│ Bri- │ Bri+ │⇧Home │Search│ Mute │ Vol- │  │ Vol+ │ Prev │ Play │ Next │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┘  └──────┴──────┴──────┴──────┴──────┴──────┘
```

See [Caret Mode](#caret-mode--trackball-as-text-cursor) below for how the trackball itself behaves on this layer.

### Corne-nav Layer (hold left thumb, 3rd key)

HJKL become arrow keys, vim-style — lets you navigate without reaching for the trackball:

```
┌──────┬──────┬──────┬──────┬──────┬──────┐  ┌──────┬──────┬──────┬──────┬──────┬──────┐
│      │      │      │      │      │      │  │  ←   │  ↓   │  ↑   │  →   │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┘  └──────┴──────┴──────┴──────┴──────┴──────┘
                                                          thumbs: — — —  |  ⌥Space —
```

### Corne-mouse Layer (hold right thumb, 1st key)

Mouse emulation without the trackball — HJKL move the cursor, with clicks and scroll on the rows above/below:

```
┌──────┬──────┬──────┬──────┬──────┬──────┐  ┌──────┬──────┬──────┬──────┬──────┬──────┐
│      │      │      │      │      │      │  │ Home │LClk  │SCRL↑ │PgUp  │SCRL←│      │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │  ←   │  ↓   │  ↑   │  →   │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┤  ├──────┼──────┼──────┼──────┼──────┼──────┤
│      │      │      │      │      │      │  │ End  │RClk  │SCRL↓ │PgDn  │SCRL→│      │
└──────┴──────┴──────┴──────┴──────┴──────┘  └──────┴──────┴──────┴──────┴──────┴──────┘
                              thumbs: — ⌘Space —  |  — —
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
CONFIG_PMW3610_CPI=600             # Raw sensor CPI (200-3200, quantised to steps of 200)
CONFIG_PMW3610_CPI_DIVIDOR=1       # Keep at 1 — see the warning below
CONFIG_PMW3610_SNIPE_CPI=200       # Snipe mode CPI (200 = range minimum)
CONFIG_PMW3610_SCROLL_TICK=18      # Scroll sensitivity (higher = slower); ~1.5 mm of ball travel per tick
                                   # note: scroll uses CONFIG_PMW3610_CPI, so rescale this if you change it
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

USB serial logging is **disabled** by default — the block sits commented out at the bottom of `charybdis_right.conf`. Uncomment it when you need to watch what the sensor is doing:

```conf
CONFIG_ZMK_USB_LOGGING=y
CONFIG_LOG=y
CONFIG_ZMK_LOG_LEVEL_DBG=y
CONFIG_SENSOR_LOG_LEVEL_DBG=y
CONFIG_INPUT_LOG_LEVEL_DBG=y
```

Worth keeping off for daily use: every `LOG_DBG` in the driver lives inside `pmw3610_report_data()`, which runs 125 times a second while the ball is moving. With `ZMK_LOG_LEVEL_DBG` off those calls are removed at compile time rather than checked at runtime.

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

Effective cursor speed = `CPI / CPI_DIVIDOR`.

**Prefer changing `CPI` and leaving `CPI_DIVIDOR` at 1.** The divisor is an integer division on the raw delta, applied *before* the acceleration step and its sub-pixel remainder accumulator — so the fraction is thrown away instead of carried over. With `CPI_DIVIDOR=2`, a slow roll that produces `raw=1` per poll becomes `1/2 = 0`: roughly half the motion is lost at low speed and almost none at high speed, so effective sensitivity *falls* the slower you move. Letting the sensor do the scaling avoids this entirely.

Note that CPI is quantised: the driver writes `cpi / 200` to the sensor, so only multiples of 200 are actually reachable. A non-multiple is silently rounded down — `SNIPE_CPI=250` ran at 200, which is why it is now written as 200 outright.

The combinations below yield the same nominal speed but differ in motion character (smoothness vs. noise) — and, per the warning above, in how much slow-speed detail survives:

```
3200/8 = 400  — more filtering, smoother but less responsive
1600/4 = 400  — balanced
 800/2 = 400  — less filtering, more raw
 400/1 = 400  — no filtering
```
