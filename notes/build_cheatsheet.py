#!/usr/bin/env python3
"""
Собирает шпаргалку notes/charybdis-cheatsheet.html из реальных данных:

  * слои — из config/charybdis.keymap (каждый биндинг получает подпись из
    таблицы LABELS ниже; биндинг без подписи — ошибка, значит раскладка
    поменялась и таблицу надо дополнить);
  * Hyper-приложения — из ~/.config/run-or-raise/shortcuts.conf.

Вид страницы — в notes/charybdis-cheatsheet.template.html.

Запуск из любого места:
    python3 notes/build_cheatsheet.py              # -> notes/charybdis-cheatsheet.html
    python3 notes/build_cheatsheet.py --fragment X # плюс фрагмент без <html>/<head> для Artifact
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYMAP = ROOT / "config/charybdis.keymap"
TEMPLATE = ROOT / "notes/charybdis-cheatsheet.template.html"
OUT = ROOT / "notes/charybdis-cheatsheet.html"
RUN_OR_RAISE = Path.home() / ".config/run-or-raise/shortcuts.conf"

KEYS = 56
LAYERS = ["BASE", "MOUSE", "NAV", "NUM", "FUN"]   # какие слои рисуются (по display-name)
HOLDERS = {"NAV": 50, "NUM": 55, "FUN": 54}        # позиция клавиши-держателя на BASE

# Подпись клавиши на базовом слое — мелко в углу каждой клавиши.
LEGEND = ("` 1 2 3 4 5 6 7 8 9 0 ⌫ Tab Q W E R T Y U I O P [ Esc A S D F G H J K L ; ' "
          "Shift Z X C V B N M , . / Shift Space Cmd Tab ⌫ Space Alt Язык Enter").split()

# Биндинг -> (подпись, подпись мелко, вид). Виды: key | mod | danger | dual:<слой>.
# LG(x) = Ctrl+x и LC(x) = Super+x на Ubuntu (обмен Ctrl/Win, см. начало keymap).
LABELS = {
    "BASE": {
        "&mt LCTRL ESC": ("Esc", "Ctrl — держать", "mod"),
        "&td_shift_l": ("Shift", "×2 = CAPS", "mod"),
        "&td_shift_r": ("Shift", "×2 = CAPS", "mod"),
        "&kp SPACE": ("Space", "", "key"),
        "&kp LGUI": ("Cmd", "Ctrl в Ubuntu", "mod"),
        "&kp LALT": ("Alt", "", "mod"),
        "&lt 4 TAB": ("Tab", "NAV", "dual:nav"),
        "&hyper_bspc LS(LA(LC(LGUI))) BSPC": ("⌫", "Hyper", "dual:hyper"),
        "&lt 6 LC(SPACE)": ("Язык", "FUN", "dual:fun"),
        "&lt 5 RET": ("Enter", "NUM", "dual:num"),
        "&kp GRAVE": ("`", "", "key"), "&kp BSPC": ("⌫", "", "key"), "&kp TAB": ("Tab", "", "key"),
        "&kp LBKT": ("[", "", "key"), "&kp SEMI": (";", "", "key"), "&kp SQT": ("'", "", "key"),
        "&kp COMMA": (",", "", "key"), "&kp DOT": (".", "", "key"), "&kp FSLH": ("/", "", "key"),
    },
    "MOUSE": {
        "&mkp RCLK": ("ПКМ", "", "key"), "&mkp LCLK": ("ЛКМ", "", "key"), "&mkp MCLK": ("СКМ", "средняя", "key"),
        "&mo 2": ("Snipe", "держать", "dual:mouse"), "&mo 3": ("Scroll", "держать", "dual:mouse"),
    },
    "NAV": {
        "&kp LC(GRAVE)": ("Окна", "Super+`", "key"),
        "&kp LG(PG_UP)": ("← Вкл", "вкладка", "key"), "&kp LG(PG_DN)": ("Вкл →", "вкладка", "key"),
        "&kp HOME": ("Home", "", "key"), "&kp PG_DN": ("PgDn", "", "key"), "&kp PG_UP": ("PgUp", "", "key"), "&kp END": ("End", "", "key"),
        "&kp LG(BSPC)": ("⌫ слово", "Ctrl+⌫", "key"), "&kp LG(DEL)": ("Del слово", "Ctrl+Del", "key"),
        "&kp LG(LA(MINUS))": ("Назад", "VS Code", "key"), "&kp LG(LS(MINUS))": ("Вперёд", "VS Code", "key"),
        "&kp LALT": ("Alt", "", "mod"), "&kp LGUI": ("Ctrl", "", "mod"), "&kp LSHFT": ("Shift", "", "mod"),
        "&kp LEFT": ("←", "", "key"), "&kp DOWN": ("↓", "", "key"), "&kp UP": ("↑", "", "key"), "&kp RIGHT": ("→", "", "key"),
        "&kp DEL": ("Del", "", "key"),
        "&kp LC(LEFT)": ("Окно ←", "половина", "key"), "&kp LA(F10)": ("Макс", "развернуть", "key"),
        "&kp LC(RIGHT)": ("Окно →", "половина", "key"),
        "&kp LC(LS(LEFT))": ("Мон ←", "на левый", "key"), "&kp LC(LS(RIGHT))": ("Мон →", "на правый", "key"),
        "&kp LG(HOME)": ("Начало", "файла", "key"), "&kp LG(LEFT)": ("← слово", "Ctrl+←", "key"),
        "&kp LG(RIGHT)": ("слово →", "Ctrl+→", "key"), "&kp LG(END)": ("Конец", "файла", "key"),
    },
    "NUM": {
        "&kp LEFT_BRACKET": ("[", "", "key"), "&kp RIGHT_BRACKET": ("]", "", "key"), "&kp SEMICOLON": (";", "", "key"),
        "&kp EQUAL": ("=", "", "key"), "&kp TILDE": ("~", "", "key"), "&kp SLASH": ("/", "", "key"),
        "&kp MINUS": ("−", "", "key"), "&kp DOT": (".", "", "key"),
        "&kp RIGHT_SHIFT": ("Shift", "", "mod"), "&kp RIGHT_GUI": ("Super", "", "mod"),
        "&kp RIGHT_ALT": ("Alt", "", "mod"), "&kp RIGHT_CONTROL": ("Ctrl", "", "mod"),
    },
    "FUN": {
        "&kp C_PREV": ("Prev", "трек", "key"), "&kp C_PP": ("Play", "пауза", "key"), "&kp C_NEXT": ("Next", "трек", "key"),
        "&kp C_VOL_DN": ("Vol −", "", "key"), "&kp C_VOL_UP": ("Vol +", "", "key"), "&kp PSCRN": ("PrtSc", "скриншот", "key"),
        "&bt BT_CLR_ALL": ("BT ✕", "все пары!", "danger"), "&bt BT_CLR": ("BT ✕", "текущий", "key"),
        "&bt BT_NXT": ("BT →", "следующий", "key"),
        "&kp C_BRI_DN": ("Ярк −", "", "key"), "&kp C_BRI_UP": ("Ярк +", "", "key"), "&kp K_MUTE": ("Mute", "", "key"),
        "&bootloader": ("Boot", "левая пол.", "danger"), "&studio_unlock": ("Studio", "unlock", "key"),
    },
}

# Команда запуска в run-or-raise -> название в шпаргалке.
APP_NAMES = {
    "code": "VS Code", "google-chrome": "Chrome", "wezterm": "WezTerm", "dbeaver-ce": "DBeaver",
    "claude-desktop": "Claude", "/opt/LOOP/loop-desktop": "LOOP", "/snap/bin/telegram-desktop": "Telegram",
    "nautilus": "Files",
}
HYPER_PREFIX = "<Shift><Ctrl><Alt><Super>"


def read_layers():
    src = re.sub(r"//[^\n]*|/\*.*?\*/", " ", KEYMAP.read_text(), flags=re.S)
    layers = {}
    for m in re.finditer(r"\w+_layer\s*\{[^{}]*?display-name\s*=\s*\"(\w+)\";\s*bindings\s*=\s*<(.*?)>\s*;", src, re.S):
        layers[m.group(1)] = ["&" + " ".join(t.split()) for t in m.group(2).split("&") if t.strip()]
    for name in LAYERS:
        if name not in layers:
            sys.exit(f"в keymap нет слоя с display-name \"{name}\"")
        if len(layers[name]) != KEYS:
            sys.exit(f"слой {name}: {len(layers[name])} биндингов вместо {KEYS}")
    return layers


def label(layer, tok):
    if tok in LABELS.get(layer, {}):
        return list(LABELS[layer][tok])
    m = re.fullmatch(r"&kp (?:N(\d)|NUMBER_(\d))", tok)
    if m:
        return [m.group(1) or m.group(2), "", "key"]
    m = re.fullmatch(r"&kp ([A-Z])", tok)
    if m and layer == "BASE":
        return [m.group(1), "", "key"]
    m = re.fullmatch(r"&kp F(\d+)", tok)
    if m:
        return ["F" + m.group(1), "", "key"]
    m = re.fullmatch(r"&bt BT_SEL (\d)", tok)
    if m:
        return ["BT " + m.group(1), "профиль", "key"]
    sys.exit(f"нет подписи для {layer}: '{tok}' — дополни LABELS в {Path(__file__).name}")


def read_hyper():
    if not RUN_OR_RAISE.exists():
        print(f"предупреждение: нет {RUN_OR_RAISE}, раздел Hyper будет пустым", file=sys.stderr)
        return {}
    apps = {}
    for line in RUN_OR_RAISE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        shortcut, cmd = line.split(",")[:2]
        if not shortcut.startswith(HYPER_PREFIX):
            continue
        apps[shortcut[len(HYPER_PREFIX):].upper()] = APP_NAMES.get(cmd, Path(cmd.split()[0]).name)
    return apps


def build_data():
    layers = read_layers()
    out = {"legend": LEGEND, "layers": {}, "hyper": read_hyper()}
    for name in LAYERS:
        cells = []
        for pos, tok in enumerate(layers[name]):
            if tok == "&trans":
                cells.append(["", "", "held" if HOLDERS.get(name) == pos else "trans"])
            else:
                cells.append(label(name, tok))
        out["layers"][name] = cells
    return out


def main():
    data = json.dumps(build_data(), ensure_ascii=False).replace("</", "<\\/")
    fragment = TEMPLATE.read_text().replace("__DATA__", data)
    fragment = re.sub(r"\A<!--.*?-->\n", "", fragment, flags=re.S)   # служебный комментарий шаблона

    head, body = fragment.split("<main", 1)
    page = ("<!doctype html>\n<html lang=\"ru\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<!-- Сгенерировано notes/build_cheatsheet.py из charybdis-cheatsheet.template.html. Не править руками. -->\n"
            + head.strip() + "\n</head>\n<body>\n<main" + body.rstrip() + "\n</body>\n</html>\n")
    OUT.write_text(page)
    print(f"{OUT.relative_to(ROOT)}: {len(page.encode())} байт")

    if "--fragment" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--fragment") + 1])
        path.write_text(fragment)
        print(f"фрагмент для Artifact: {path}")


if __name__ == "__main__":
    main()
