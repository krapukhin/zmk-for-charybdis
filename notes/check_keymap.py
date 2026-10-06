#!/usr/bin/env python3
"""
Статическая проверка раскладки — без сборки, за долю секунды.

Ловит то, что CI не ловит: сборка зелёная, а режим трекбола молча перестал
работать. Номера слоёв записаны в нескольких местах, и ничто их не сверяет:

  * порядок слоёв в config/charybdis.keymap (индекс = порядковый номер);
  * snipe-/scroll-/caret-layers драйвера и snipe_scaler в charybdis_right.overlay;
  * &zip_temp_layer и layer-scoped процессоры в charybdis_dongle.overlay.

Дополнительно: в каждом слое ровно 56 биндингов, &lt/&mo/&tog/&to/&sl
ссылаются на существующие слои, #define совпадают с display-name слоёв,
буквы базового слоя — чистые &kp, клавиша-держатель слоя прозрачна в нём,
авто-слой мыши ниже режимов трекбола, automouse-layer драйвера выключен,
excluded-positions одинаковы в обоих комплектах прошивки.

Запуск из любого места:  python3 notes/check_keymap.py [корень репозитория]
Код выхода 0 — всё сходится, 1 — есть ошибки (список печатается).
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
KEYMAP = ROOT / "config/charybdis.keymap"
RIGHT = ROOT / "config/boards/shields/charybdis/charybdis_right.overlay"
DONGLE = ROOT / "config/boards/shields/charybdis_dongle/charybdis_dongle.overlay"

KEYS = 56

# Какой слой keymap какую роль играет для трекбола — по имени узла.
# Переименовал слой (или это сделал keymap-editor[bot]) — поправь здесь.
ROLE_LAYERS = {
    "mouse": "mouse_layer",
    "snipe": "snipe_layer",
    "scroll": "scroll_layer",
    "caret": "nav_layer",
}

# Позиции букв и знаков препинания базового слоя: только чистые &kp, без
# &lt/&mt — иначе буква уходит только по отпусканию («ватные» буквы).
LETTER_POSITIONS = list(range(13, 23)) + list(range(25, 35)) + list(range(37, 47))

# Свойства драйвера в charybdis_right.overlay -> роль.
DRIVER_PROPS = {"snipe-layers": "snipe", "scroll-layers": "scroll", "caret-layers": "caret"}

# Дочерние узлы trackball_listener с layers = <...> -> роль. Узел с layers,
# которого здесь нет, считается ошибкой: новый override должен попасть в проверку.
RIGHT_OVERRIDES = {"snipe_scaler": "snipe"}
DONGLE_OVERRIDES = {"snipe_scaler": "snipe", "scroll_mapper": "scroll", "caret_proc": "caret"}

LAYER_BEHAVIORS = ("lt", "mo", "tog", "to", "sl")

errors = []


def strip_comments(text):
    return re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.S)


def block(text, pattern):
    """Содержимое фигурных скобок узла, открывающая скобка — конец pattern."""
    m = re.search(pattern, text)
    if not m:
        return None
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    return None


def children(body):
    """Дочерние узлы верхнего уровня: [(имя, содержимое)]. Метки 'label:' отбрасываются."""
    out, depth, seg, name, start = [], 0, 0, None, 0
    for i, c in enumerate(body):
        if c == "{":
            if depth == 0:
                name = re.search(r"([\w,.@+-]+)\s*$", body[seg:i]).group(1)
                start = i + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                out.append((name, body[start:i]))
                seg = i + 1
        elif c == ";" and depth == 0:
            seg = i + 1
    return out


def top_level(body):
    """Свойства узла без дочерних узлов."""
    out, depth = [], 0
    for c in body:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            out.append(c)
    return "".join(out)


def prop(body, name):
    m = re.search(rf"(?<![\w-]){re.escape(name)}\s*=\s*<([^>]*)>", body)
    return m.group(1).split() if m else None


def resolve(token, defines):
    token = defines.get(token, token)
    try:
        return int(token, 0)
    except ValueError:
        return None


# ---------------------------------------------------------------- keymap

src = strip_comments(KEYMAP.read_text())
defines = dict(re.findall(r"^\s*#define\s+(\w+)\s+(\S+)", src, flags=re.M))

layers = []  # [(имя узла, display-name или None, [биндинги])]
km = block(src, r"(?<![\w,])keymap\s*\{")
if km is None:
    sys.exit(f"{KEYMAP}: узел keymap не найден")
for name, body in children(km):
    m = re.search(r"\bbindings\s*=\s*<(.*?)>\s*;", body, flags=re.S)
    if not m:
        errors.append(f"keymap: у слоя {name} нет bindings")
        continue
    tokens = ["&" + " ".join(t.split()) for t in m.group(1).split("&") if t.strip()]
    dn = re.search(r'display-name\s*=\s*"([^"]*)"', body)
    layers.append((name, dn.group(1) if dn else None, tokens))

names = [n for n, _, _ in layers]
for i, (name, _, tokens) in enumerate(layers):
    if len(tokens) != KEYS:
        errors.append(f"keymap: слой {i} {name} — {len(tokens)} биндингов вместо {KEYS}")
    for pos, tok in enumerate(tokens):
        m = re.match(rf"&({'|'.join(LAYER_BEHAVIORS)})\s+(\S+)", tok)
        if m:
            v = resolve(m.group(2), defines)
            if v is None or not 0 <= v < len(layers):
                errors.append(f"keymap: слой {i} {name}, позиция {pos}: '{tok}' — нет такого слоя")

# #define ИМЯ N должен указывать на слой с display-name ИМЯ на месте N.
display = [dn for _, dn, _ in layers]
for name, value in defines.items():
    if name in display:
        v = resolve(value, {})
        if v is None or v >= len(layers) or display[v] != name:
            got = display[v] if v is not None and v < len(layers) else "—"
            errors.append(f"keymap: #define {name} {value}, но слой {value} — {got}; слой {name} стоит на {display.index(name)}")

if layers:
    base = layers[0][2]
    bad = [f"{p}:{base[p]}" for p in LETTER_POSITIONS if p < len(base) and not base[p].startswith("&kp ")]
    if bad:
        errors.append(f"keymap: на буквенных позициях базового слоя не &kp: {bad}")

# Клавиша, включающая слой, в самом этом слое должна быть &trans.
for i, (name, _, tokens) in enumerate(layers):
    for pos, tok in enumerate(tokens):
        m = re.match(r"&(lt|mo)\s+(\S+)", tok)
        v = resolve(m.group(2), defines) if m else None
        if v is not None and 0 <= v < len(layers) and pos < len(layers[v][2]) and layers[v][2][pos] != "&trans":
            errors.append(f"keymap: {name}[{pos}] '{tok}' включает слой {v}, а там на {pos} не &trans: {layers[v][2][pos]}")

idx = {}
for role, node in ROLE_LAYERS.items():
    if node in names:
        idx[role] = names.index(node)
    else:
        errors.append(f"keymap: не найден слой '{node}' (роль {role}) — переименован? поправь ROLE_LAYERS")

if "mouse" in idx:
    for role in ("snipe", "scroll", "caret"):
        if role in idx and idx["mouse"] >= idx[role]:
            errors.append(
                f"keymap: авто-слой мыши ({idx['mouse']}) должен быть НИЖЕ {role} ({idx[role]}) — "
                "драйвер смотрит только на верхний активный слой"
            )


# ---------------------------------------------------------------- overlays

def expect(where, what, got, role):
    if role not in idx:
        return
    if got is None:
        errors.append(f"{where}: не найдено {what}")
    elif [resolve(t, {}) for t in got] != [idx[role]]:
        errors.append(
            f"{where}: {what} = <{' '.join(got)}>, а слой {ROLE_LAYERS[role]} в keymap — {idx[role]}"
        )


def check_listener(path, overrides):
    text = strip_comments(path.read_text())
    where = path.name
    body = block(text, r"\btrackball_listener\s*\{")
    if body is None:
        errors.append(f"{where}: узел trackball_listener не найден")
        return text
    procs = prop(top_level(body), "input-processors") or []
    m = re.search(r"&zip_temp_layer\s+(\S+)", " ".join(procs))
    expect(where, "&zip_temp_layer <слой>", [m.group(1)] if m else None, "mouse")
    found = {}
    for name, child in children(body):
        layers_val = prop(child, "layers")
        if layers_val is None:
            continue
        if name not in overrides:
            errors.append(f"{where}: override '{name}' не описан в check_keymap.py — добавь в таблицу")
            continue
        found[name] = layers_val
    for name, role in overrides.items():
        expect(where, f"{name} layers", found.get(name), role)
    return text


right = check_listener(RIGHT, RIGHT_OVERRIDES)
for p, role in DRIVER_PROPS.items():
    expect(RIGHT.name, p, prop(right, p), role)
am = prop(right, "automouse-layer")
if am is not None and resolve(am[0], {}) != -1:
    errors.append(f"{RIGHT.name}: automouse-layer = <{am[0]}> — должен оставаться выключенным, AML делает &zip_temp_layer")

dongle = check_listener(DONGLE, DONGLE_OVERRIDES)

excl = {}
for path, text in ((RIGHT, right), (DONGLE, dongle)):
    vals = prop(text, "excluded-positions")
    if vals is None:
        errors.append(f"{path.name}: excluded-positions не найден")
        continue
    excl[path.name] = sorted(resolve(v, {}) for v in vals)
    bad = [v for v in excl[path.name] if not 0 <= v < KEYS]
    if bad:
        errors.append(f"{path.name}: excluded-positions вне 0..{KEYS - 1}: {bad}")
if len(set(map(tuple, excl.values()))) > 1:
    errors.append(f"excluded-positions различаются: {excl}")


# ---------------------------------------------------------------- отчёт

print("Слои:")
for i, (name, dn, tokens) in enumerate(layers):
    role = next((r for r, n in ROLE_LAYERS.items() if n == name), "")
    label = f"{name} ({dn})" if dn else name
    print(f"  {i}  {label:<28} {len(tokens):>2} биндингов  {role}")

if errors:
    print(f"\nОШИБКИ ({len(errors)}):")
    print("\n".join(f"  - {e}" for e in errors))
    sys.exit(1)
print("\nOK: биндинги, ссылки на слои и номера слоёв в обоих overlay'ях сходятся")
