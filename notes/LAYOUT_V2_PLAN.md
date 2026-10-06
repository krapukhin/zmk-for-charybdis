# План v2: раскладка Charybdis 4x6 для Claude Code

Oct 6, 2026 · @Dmitry Krapukhin

## Как использовать этот план

Положите этот документ в репозиторий как `notes/LAYOUT_V2_PLAN.md` и запустите Claude Code одной командой; план рассчитан на выполнение по шагам с коммитом после каждого.

Команда для Claude Code (в корне репозитория, ветка `Charybdis_4x6`):

```
Прочитай CLAUDE.md, README.md и notes/LAYOUT_V2_PLAN.md. Выполни план шаг за шагом в новой ветке layout-v2. После каждого шага запускай проверку из шага 6, делай отдельный коммит с номером шага в сообщении и кратко отчитывайся. Не трогай zmk-pmw3610-driver-main и настройки ускорения трекбола. Если план противоречит реальному содержимому файлов — остановись и спроси, не додумывай.
```

**Что в репозитории уже есть** (ветка `Charybdis_4x6`, 6 октября 2026):

- `config/charybdis.keymap` — 9 слоёв: 0 QWERTY, 1 mouse (авто), 2 snipe, 3 scroll, 4 BT, 5 caret, 6 corne\_1 (стрелки на HJKL), 7 corne\_2 (эмуляция мыши), 8 layer\_8 (numpad слева + моды справа).
- Домашний ряд — layer-tap в режимы трекбола: A/F/; → caret(5), S/L → scroll(3), D/K → snipe(2), B → BT(4). Глобальный `&lt`: tap-preferred, tapping-term 200, require-prior-idle 40 мс. Это и есть источник «ватных» букв: тап уходит только по отпусканию, а 40 мс меньше типичного интервала между буквами.
- Большие пальцы (позиции матрицы): 48 Space, 49 Alt, 50 Ctrl, 53 Cmd, 54 `mo 7` слева; 51 `lt 8 Backspace`, 52 Space, 55 `mt RAlt Enter` справа.
- Внешние колонки: 12 `mt Ctrl/Tab`, 24 `mt Alt/Esc`, 23 `mt RCtrl/[`, 35 `mt RAlt/'`.
- Комбо: U+I → `-`, I+O → `=`, O+P → `]` (уже даёт «ъ» в русской раскладке), `` ` ``+Backspace → `studio_unlock`.
- Overlay правой половины: `&zip_temp_layer 1 800`, `require-prior-idle-ms 200`, `excluded-positions <30 31 32 36 47 48 53 54>`; индексы режимов трекбола заданы свойствами драйвера в overlay (`caret-layers = <5>` и т.д.).

**Инварианты, которые нельзя нарушать** (из README и CLAUDE.md):

- Авто-слой мыши обязан иметь индекс ниже snipe/scroll/caret: драйвер смотрит только на самый верхний активный слой.
- `excluded-positions` перечисляет клавиши, которые НЕ гасят слой мыши; пустой список — слой гаснет только по таймауту.
- Драйвер вендорный, подключается через `build.yaml` (`ZMK_EXTRA_MODULES`), не через `west.yml`; его собственный `automouse-layer` остаётся выключенным.
- После любой смены числа или порядка слоёв прошивать `settings_reset` на обе половины — иначе сохранённая ZMK Studio карта перекроет новую.

**Нумерация позиций (0–55):** ряд цифр 0–11, ряд Q 12–23, домашний ряд 24–35, ряд Z 36–47; большие пальцы слева 48 49 50 (верхний ряд) и 53 54 (нижний), справа 51 52 (верхний) и 55 (нижний). Claude Code сверяет это с matrix transform в `config/boards/shields/charybdis/charybdis.dtsi` до первой правки и, если нумерация другая, пересчитывает все позиции в плане.

## Целевая раскладка

Буквы, цифровой ряд и шифты на мизинцах остаются как на MacBook; Cmd переезжает под левый большой палец, слои — на остальные большие, а домашний ряд становится чистыми буквами без layer-tap.

**Базовый слой (BASE):**

```
  `      1     2     3     4     5   │   6     7     8     9     0    Bspc
 Tab     Q     W     E     R     T   │   Y     U     I     O     P     [
 Ctl/Esc A     S     D     F     G   │   H     J     K     L     ;     '
 Shift*  Z     X     C     V     B   │   N     M     ,     .     /   Shift*

 левые большие:  48 Space   49 Cmd   50 NAV/Tab
                 53 Alt     54 FUN/Lang
 правые большие: 51 SYM/Bspc   52 Space   55 NUM/Enter
```

Обозначения: `A/B` = hold A, tap B. `Shift*` = tap-dance: hold — Shift, двойной тап — Caps Word (для CONSTANT\_NAMES). `Lang` = `LC(SPACE)` (Control-Space на macOS выбирает последний источник ввода); задаётся одним `#define LANG_KEY`, чтобы сменить на `LG(SPACE)` или `CAPS` в одном месте. Левый Cmd (49) + правый Space (52) = Spotlight, как на маке.

**Слои и их индексы** (порядок обязателен: 1 ниже 2–4):

| # | Имя | Как включается | Что делает |
| --- | --- | --- | --- |
| 0 | BASE | — | QWERTY, чистые буквы |
| 1 | MOUSE | авто, движение шара | H/J = ПКМ/ЛКМ, M = средняя, K hold = SNIPE, L hold = SCROLL |
| 2 | SNIPE | hold K на слое MOUSE | трекбол 200 CPI; всё остальное `&trans` |
| 3 | SCROLL | hold L на слое MOUSE | трекбол → колесо; всё остальное `&trans` |
| 4 | NAV | hold 50 (левый большой) | стрелки на HJKL, Home/End/PgUp/PgDn, прыжки по словам и строкам; трекбол в режиме caret |
| 5 | SYM | hold 51 (правый большой) | скобки и операторы под левой рукой, `# @ ! & \|` под правой, макросы `->` и `:=` |
| 6 | NUM | hold 55 (правый большой) | numpad под левой рукой (текущий layer\_8), моды под правой |
| 7 | FUN | hold 54 (левый большой) | F1–F12, медиа, яркость, Bluetooth, bootloader |

Удаляются: BT (уходит в FUN), caret как отдельный слой (режим caret вешается на NAV), corne\_1 (его стрелки — это NAV), corne\_2 (эмуляция мыши без шара не нужна; если жалко — оставить как слой 8, он никому не мешает).

Русская раскладка: все буквы ЙЦУКЕН на своих местах, `ъ` — уже существующее комбо O+P, `ё` — клавиша `` ` `` (раскладка «Русская — ПК») или новое комбо `[`+`'` → `\` (раскладка «Русская»).

## Шаг 0 — ветка, defines, инварианты

Вся работа идёт в ветке `layout-v2`; `Charybdis_4x6` остаётся рабочей прошивкой для отката.

- [ ] `git checkout -b layout-v2` от `Charybdis_4x6`.
- [ ] Открыть `config/boards/shields/charybdis/charybdis.dtsi` и выписать реальную нумерацию позиций матрицы; сверить с таблицей из раздела «Как использовать». Расхождение — пересчитать позиции в плане и сказать об этом.
- [ ] В `config/charybdis.keymap` сразу после `#include` добавить:

```
#include <input/processors.dtsi>   // если ещё не подключён здесь или в overlay

#define BASE   0
#define MOUSE  1
#define SNIPE  2
#define SCROLL 3
#define NAV    4
#define SYM    5
#define NUM    6
#define FUN    7

#define LANG_KEY LC(SPACE)   // Control-Space; заменить на LG(SPACE) или CAPS при необходимости
```

- [ ] В overlay правой половины (`charybdis_right.overlay`) найти узел трекбола и выставить `snipe-layers = <2>; scroll-layers = <3>; caret-layers = <4>;` (точные имена свойств взять из `zmk-pmw3610-driver-main/dts/bindings/*.yml`, не из памяти). Старое `caret-layers = <5>` убрать.
- [ ] Проверить, что `automouse-layer` драйвера не задан, а `&zip_temp_layer 1 800` остаётся как есть.

Критерий готовности: сборка по-прежнему проходит (шаг 6), поведение не изменилось — это только подготовка.

## Шаг 1 — behaviors

Все tap-hold сводятся к двум профилям: «большой палец → слой» и «мизинец → Ctrl/Esc»; с домашнего ряда tap-hold исчезают полностью, поэтому отдельного HRM-профиля нет.

- [ ] Заменить глобальные блоки `&mt { … }` и `&lt { … }` в начале keymap на:

```
&lt {
    flavor = "balanced";        // hold, если другая клавиша нажата И отпущена во время удержания
    tapping-term-ms = <200>;
    quick-tap-ms = <175>;       // тап + повтор в окне = автоповтор (Backspace, Enter)
    require-prior-idle-ms = <0>; // НЕ ставить 150: иначе Sym сразу после буквы даст Backspace
};

&mt {
    flavor = "balanced";
    tapping-term-ms = <200>;
    quick-tap-ms = <175>;
};
```

- [ ] Добавить в `/ { behaviors { … } }`:

```
td_shift_l: td_shift_l {
    compatible = "zmk,behavior-tap-dance";
    #binding-cells = <0>;
    tapping-term-ms = <200>;
    bindings = <&kp LSHFT>, <&caps_word>;
};
td_shift_r: td_shift_r {   // то же с RSHFT
    compatible = "zmk,behavior-tap-dance";
    #binding-cells = <0>;
    tapping-term-ms = <200>;
    bindings = <&kp RSHFT>, <&caps_word>;
};
```

- [ ] Настроить `&caps_word { continue-list = <UNDERSCORE MINUS BSPC DEL N1 N2 N3 N4 N5 N6 N7 N8 N9 N0>; };` — подчёркивание и цифры не сбрасывают Caps Word, пробел сбрасывает.
- [ ] Добавить два макроса в `/ { macros { … } }`: `m_arrow` печатает `->` (`&kp MINUS &kp GT`), `m_walrus` печатает `:=` (`&kp COLON &kp EQUAL`); `wait-ms = <0>; tap-ms = <5>;`.
- [ ] Удалить комментарий про «неустранимую отложенность тапа» у `&mt` — он описывал старую конструкцию с Enter.

Критерий готовности: keymap компилируется; `td_shift_l`, `td_shift_r`, `m_arrow`, `m_walrus` определены, но ещё не используются (это шаг 2).

## Шаг 2 — базовый слой

Слой 0 переписывается целиком: 56 биндингов, из них все 26 букв — чистые `&kp`, никаких `&lt` и `&mt` на буквах.

- [ ] Заменить блок `QWERTY { bindings = < … > }` на:

```
BASE {
    bindings = <
&kp GRAVE      &kp N1 &kp N2 &kp N3 &kp N4 &kp N5    &kp N6 &kp N7 &kp N8 &kp N9 &kp N0 &kp BSPC
&kp TAB        &kp Q  &kp W  &kp E  &kp R  &kp T     &kp Y  &kp U  &kp I  &kp O  &kp P  &kp LBKT
&mt LCTRL ESC  &kp A  &kp S  &kp D  &kp F  &kp G     &kp H  &kp J  &kp K  &kp L  &kp SEMI &kp SQT
&td_shift_l    &kp Z  &kp X  &kp C  &kp V  &kp B     &kp N  &kp M  &kp COMMA &kp DOT &kp FSLH &td_shift_r
          &kp SPACE  &kp LGUI  &lt NAV TAB          &lt SYM BSPC  &kp SPACE
          &kp LALT   &lt FUN LANG_KEY               &lt NUM RET
    >;
};
```

- [ ] Порядок биндингов в двух последних строках = порядок позиций 48 49 50 51 52 и 53 54 55 в matrix transform. Если в `charybdis.dtsi` верхний ряд больших пальцев перечислен иначе (например правые раньше левых), переставить строго по transform, а не по картинке.
- [ ] Убедиться, что слои ниже по файлу идут строго в порядке MOUSE, SNIPE, SCROLL, NAV, SYM, NUM, FUN — индекс слоя в ZMK равен его порядковому номеру в `keymap {}`.

Что пропадает из базового слоя по сравнению с текущим и куда уходит: Ctrl с 12 → на 24 (hold); Alt с 24 → на 53; RCtrl/RAlt с 23/35 → не нужны (на маке правые моды не используются); Backspace с 51 остаётся тапом; Enter с 55 остаётся тапом; BT с B → FUN.

Критерий готовности: сборка проходит; при простом наборе текста ни одна буква не задерживается до отпускания (нет ни одного `&lt`/`&mt` в позициях 13–22, 25–34, 37–46).

## Шаг 3 — слои трекбола и overlay

Режимы трекбола уходят с букв базового слоя внутрь авто-слоя MOUSE: шар поднял слой — под правой рукой клики, удержание K/L переключает snipe/scroll, слой гаснет сам.

- [ ] Слой 1 `MOUSE` (сразу после BASE): всё `&trans`, кроме позиций 30 `&mkp RCLK`, 31 `&mkp LCLK`, 32 `&mo SNIPE`, 33 `&mo SCROLL`, 43 `&mkp MCLK` (клавиша M). Расположение ПКМ/ЛКМ на H/J оставить как есть — оно уже в мышечной памяти.
- [ ] Слой 2 `SNIPE`: 56 × `&trans`. Его единственная задача — чтобы драйвер увидел индекс 2 наверху стека. F-клавиши и скобки, которые жили на нём, уходят в FUN и SYM.
- [ ] Слой 3 `SCROLL`: 56 × `&trans`. Стрелки, которые жили на нём, уходят в NAV.
- [ ] В `charybdis_right.overlay` обновить `&zip_temp_layer { … excluded-positions = <30 31 32 33 43 24 36 47 49 53>; }`: клики и держатели режимов (30–33, 43) плюс Ctrl/Esc (24), оба Shift (36, 47), Cmd (49), Alt (53). Space (48, 52) и Enter (55) намеренно не в списке — пробел значит «вернулся к набору».
- [ ] `require-prior-idle-ms` у `&zip_temp_layer` оставить 200; таймаут 800 оставить и тюнить после недели (раздел в конце).
- [ ] Проверить, что `caret-layers = <4>` в overlay указывает на NAV (шаг 0): удержание левого большого 50 + прокрутка шара двигает текстовый курсор, авто-слой при этом ниже и не мешает.

Почему так, а не layer-tap на буквах: `&mo` внутри слоя MOUSE не влияет на набор вообще — пока шар не крутили, K и L это буквы без оговорок. Цена — чтобы прокрутить, шар уже должен быть под пальцем, что и так всегда верно.

Критерий готовности: движение шара → клики на H/J работают; шар + удержание L → колесо; шар + удержание K → медленный курсор; удержание 50 + шар → стрелки. Через \~0.8 с после остановки шара H/J/K/L снова буквы.

## Шаг 4 — NAV, SYM, NUM, FUN

Четыре слоя на больших пальцах по правилу «держу одной рукой — печатаю другой»; позиция самой удерживаемой клавиши в её слое всегда `&trans`.

**NAV (слой 4, hold 50).** Левая рука: 13 Q `&kp LG(GRAVE)` (следующее окно), 14 W `&kp LG(LS(LBKT))`, 15 E `&kp LG(LS(RBKT))` (вкладки назад/вперёд), 26 S `&kp LALT`, 27 D `&kp LGUI`, 28 F `&kp LSHFT` (моды под пальцами, чтобы выделять текст шаром в режиме caret). Правая рука:

```
 ряд Q:   18 HOME     19 PG_DN     20 PG_UP     21 END       22 LA(BSPC)   23 LG(BSPC)
 домашний: 30 LEFT     31 DOWN      32 UP        33 RIGHT     34 DEL        35 &trans
 ряд Z:   42 LG(LEFT) 43 LA(LEFT)  44 LA(RIGHT) 45 LG(RIGHT) 46 &trans
```

Мнемоника: Home над ←, End над →, PgDn над ↓, PgUp над ↑; в ряду ниже — прыжки: Cmd+← (начало строки), Opt+← (слово назад), Opt+→, Cmd+→. `LA(BSPC)` удаляет слово, `LG(BSPC)` — строку до курсора. Всё остальное `&trans`.

**SYM (слой 5, hold 51).** Левая рука по частоте символов в Python, скобки парами под перекат:

```
 ряд Q:    13 TILDE  14 LBRC   15 LBKT   16 RBKT   17 RBRC
 домашний: 25 COLON  26 UNDER  27 LPAR   28 RPAR   29 EQUAL
 ряд Z:    37 PIPE   38 LT     39 GT     40 STAR   41 PLUS
```

Правая рука на SYM: 18 AMPS, 19 PIPE, 20 BSLH, 21 PRCNT, 22 GRAVE; 30 MINUS, 31 HASH, 32 AT, 33 EXCL, 34 DLLR; 42 `&m_arrow`, 43 `&m_walrus`. Внешние колонки (12, 24, 36, 23, 35, 47) и 51 — `&trans`.

**NUM (слой 6, hold 55).** Взять содержимое текущего `layer_8` без изменений: numpad слева (7 8 9 / 4 5 6 / 1 2 3 на W E R, S D F, X C V), `[ ] ; = ~ /` по краям, моды RSHFT RGUI RALT RCTRL на J K L ;. Большие пальцы: 48 `&kp N0`, 49 `&kp MINUS`, 53 `&kp DOT`, 55 `&trans`.

**FUN (слой 7, hold 54).** Ряд цифр 0–11: `F1 … F12`. Ряд Q слева 13–17: `&bt BT_SEL 0 … 4`; справа 18–22: `C_PREV C_PP C_NEXT C_VOL_DN C_VOL_UP`. Домашний ряд: 25 `&bt BT_CLR_ALL`, 27 `&bt BT_CLR`, 29 `&bt BT_NXT`; справа 30 `C_BRI_DN`, 31 `C_BRI_UP`, 32 `K_MUTE`. Ряд Z: 37 `&bootloader`, 47 `&studio_unlock`. Остальное `&trans`, 54 `&trans`.

- [ ] Написать четыре слоя в этом порядке сразу после SCROLL; удалить BT\_layers, caret\_layer, corne\_1, corne\_2, layer\_8 (содержимое layer\_8 живёт теперь в NUM).
- [ ] Пересчитать: в файле ровно 8 слоёв, каждый 56 биндингов (шаг 6).

Критерий готовности: hold 50 + J/K/L/; = стрелки; hold 51 + D/F = `()`; hold 51 + S = `_`; hold 55 + R = `9`; hold 54 + `1` = F1.

## Шаг 5 — комбо

Существующие три комбо сохраняются; добавляются `ё`-запасной и защита от срабатывания при быстром наборе.

- [ ] Оставить `combo_minus` (19 20 → `-`), `combo_equal` (20 21 → `=`), `combo_rbrace` (21 22 → `]`, даёт «ъ»), `combo_studio_unlock` (0 11).
- [ ] Добавить `combo_bslh`: `key-positions = <23 35>` (вертикально `[` + `'`) → `&kp BSLH`. В раскладке «Русская» это `ё`; в «Русская — ПК» просто обратный слэш.
- [ ] Всем комбо на буквенных/символьных позициях добавить `require-prior-idle-ms = <100>;` и `timeout-ms = <40>;` — комбо не стреляет, если 100 мс назад была нажата другая клавиша, то есть во время набора «ио» или «оп» в русском тексте.
- [ ] Комбо `combo_studio_unlock` оставить без `require-prior-idle-ms`.
- [ ] Все комбо ограничить `layers = <BASE>;` — на слоях NAV/SYM они не нужны.

Что НЕ добавлять: комбо J+K для языка (в русском «ол» — частый бигram, будет стрелять); язык живёт на 54.

## Шаг 6 — проверка, сборка, прошивка

Локального тулчейна нет, поэтому проверка делится на быструю статическую (скрипт в репо, гоняется после каждого шага) и настоящую сборку в GitHub Actions.

- [ ] Создать `notes/check_keymap.py` и запускать его после каждого шага:

```python
#!/usr/bin/env python3
"""Статическая проверка config/charybdis.keymap: 8 слоёв по 56 биндингов, порядок слоёв, чистые буквы на базе."""
import re, sys, pathlib

src = pathlib.Path("config/charybdis.keymap").read_text()
src = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)        # убрать комментарии
keymap = src[src.index('compatible = "zmk,keymap"'):]
layers = re.findall(r"(\w+)\s*\{\s*bindings\s*=\s*<(.*?)>\s*;", keymap, flags=re.S)
expected = ["BASE", "MOUSE", "SNIPE", "SCROLL", "NAV", "SYM", "NUM", "FUN"]
errors = []
names = [n for n, _ in layers]
if names != expected:
    errors.append(f"порядок слоёв {names}, ожидался {expected}")
for name, body in layers:
    tokens = re.findall(r"&\w+(?:\s+[A-Za-z0-9_()]+)*?(?=\s*&|\s*$)", body.strip())
    if len(tokens) != 56:
        errors.append(f"{name}: {len(tokens)} биндингов вместо 56")
    if name == "BASE":
        letters = tokens[13:23] + tokens[25:35] + tokens[37:47]
        bad = [t for t in letters if not t.startswith("&kp ")]
        if bad:
            errors.append(f"BASE: на буквенных позициях не &kp: {bad}")
print("\n".join(errors) or "OK: 8 слоёв x 56, порядок верный, буквы чистые")
sys.exit(1 if errors else 0)
```

- [ ] Если регулярка биндингов спотыкается на `&lt NAV TAB` или `&mt LCTRL ESC`, починить скрипт, а не keymap: считать биндингом токен от `&` до следующего `&`.
- [ ] Проверить overlay: `grep -n "zip_temp_layer\|excluded-positions\|snipe-layers\|scroll-layers\|caret-layers" config/boards/shields/charybdis/charybdis_right.overlay` — индексы 1, 2, 3, 4 соответственно.
- [ ] `git push -u origin layout-v2`, дождаться зелёного `build.yml` в Actions; красный лог читать целиком — ошибки devicetree называют строку keymap.
- [ ] Прошивка (порядок из README): `settings_reset` на обе половины → `charybdis_left` → `charybdis_right`. Без `settings_reset` сохранённая ZMK Studio карта перекроет новые слои.
- [ ] Ручной smoke-тест по чек-листу: критерии готовности шагов 2–5 плюс Cmd+Tab (49 + 12), Cmd+Space (49 + 52), Ctrl+C (hold 24 + C), двойной тап Shift → Caps Word → `MY_CONST` → пробел сбрасывает.

Критерий готовности: скрипт печатает OK, Actions зелёный, smoke-тест пройден, ветка `Charybdis_4x6` не тронута.

## Шаг 7 — документация

README и CLAUDE.md сейчас описывают layer-tap на домашнем ряду и 9 слоёв; после шага 6 они врут, и следующий сеанс Claude Code будет чинить несуществующее.

- [ ] README: переписать разделы «Features», «Keymap», «Home Row & Thumb Keys», «Combos», «Layer Reference», «Trackball Modes» и ASCII-схемы слоёв по новой карте; «Auto Mouse Layer» дополнить тем, что snipe/scroll теперь `&mo` внутри слоя MOUSE, а caret привязан к NAV.
- [ ] README: в «Two traps» добавить третью ловушку — `require-prior-idle-ms` на `&lt` больших пальцев ломает слой SYM сразу после буквы (тап-Backspace вместо hold), поэтому там стоит 0.
- [ ] CLAUDE.md: обновить список слоёв и индексов, инварианты (MOUSE=1 ниже 2–4; `caret-layers`=NAV), запрет `&lt`/`&mt` на буквенных позициях базового слоя, упоминание `notes/check_keymap.py` как обязательной проверки перед коммитом.
- [ ] `notes/`: положить этот план как `LAYOUT_V2_PLAN.md` и короткий `LAYOUT_V2_CHANGELOG.md` — что ушло, куда (таблица «было → стало» по позициям 12, 23, 24, 35, 48–55).
- [ ] Коммит `docs: layout v2`; открыть PR `layout-v2 → Charybdis_4x6` с чек-листом smoke-теста в описании; мержить после недели использования.

Критерий готовности: `grep -n "lt 5\|lt 3\|lt 2\|corne_\|layer_8" README.md CLAUDE.md` ничего не находит.

## Тюнинг после первой недели

Менять по одному параметру за раз и носить изменение не меньше двух дней; у каждого симптома одна ручка.

- Буква после удержания слоя иногда проскакивает как тап (например `lt NAV TAB` печатает Tab вместо стрелки): поднять `tapping-term-ms` у `&lt` до 250 или перейти на `flavor = "hold-preferred"` только для 50 и 51 через отдельные behaviors.
- Backspace (51) срабатывает как слой при быстрых двойных тапах: увеличить `quick-tap-ms` до 200.
- H/J превращаются в клики, когда уже вернулся к набору: таймаут `&zip_temp_layer 1 800` → 500; наоборот, не успеваешь кликнуть после прицеливания → 1200.
- Слой мыши всплывает при наборе от дрожания шара: `require-prior-idle-ms` у `&zip_temp_layer` 200 → 300.
- Комбо `-`/`=`/`]` стреляют в русском тексте: `require-prior-idle-ms` у комбо 100 → 150; не стреляют вообще — `timeout-ms` 40 → 50.
- Ctrl+C через 24 даёт `Esc c`: сменить `&mt` на `flavor = "hold-preferred"` (цена — редкий `Ctrl+буква` вместо `Esc буква` при перекате с Esc).
- Caps Word сбрасывается на цифрах или `_`: расширить `continue-list`.
- Через месяц, если захочется убрать Alt/Ctrl с больших пальцев и мизинца: добавить частичные HRM только на S/D и K/L с `flavor = "balanced"`, `tapping-term-ms = <280>`, `quick-tap-ms = <175>`, `require-prior-idle-ms = <150>`, `hold-trigger-key-positions` = позиции противоположной руки, `hold-trigger-on-release`. Shift и Cmd при этом остаются физическими.

Что не трогать без причины: `CONFIG_PMW3610_*` в `charybdis_right.conf`, порядок слоёв 1 < 2 < 3 < 4, `excluded-positions`.
