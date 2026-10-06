# Layout v2 — что ушло и куда

План: [`LAYOUT_V2_PLAN.md`](LAYOUT_V2_PLAN.md). Ветка `layout-v2`, откат — `Charybdis_4x6`.
Источник правды по раскладке — [`config/charybdis.keymap`](../config/charybdis.keymap); эта таблица — снимок на момент перехода (октябрь 2026).

## Слои

| Было | Стало |
|------|-------|
| 0 QWERTY | 0 BASE |
| 1 mouse_layer | 1 MOUSE (+ `&mo` SNIPE на K, SCROLL на L) |
| 2 snipe-layers | 2 SNIPE — только клики H/J/N |
| 3 scroll-layers | 3 SCROLL — только клики H/J/N |
| 4 BT_layers | удалён → Bluetooth в FUN |
| 5 caret_layer | удалён → caret на NAV (4) |
| 6 corne_1 (был недоступен — ни одна клавиша на него не ссылалась) | удалён → стрелки в NAV |
| 7 corne_2 (эмуляция мыши без шара) | удалён |
| 8 layer_8 | 6 NUM, без изменений |
| — | 4 NAV, 5 SYM, 7 FUN — новые |

После прошивки — `settings_reset` на все устройства комплекта: число слоёв изменилось.

## Позиции базового слоя

| Позиция | Клавиша | Было | Стало |
|---------|---------|------|-------|
| 12 | Tab | `&mt LCTRL TAB` | `&kp TAB` |
| 23 | `[` | `&mt RCTRL [` | `&kp LBKT` |
| 24 | Caps-место | `&mt LALT ESC` | `&mt LCTRL ESC` |
| 35 | `'` | `&mt RALT '` | `&kp SQT` |
| 36 / 47 | Shift | `&kp LSHFT` / `RSHFT` | tap-dance: Shift, двойной тап — Caps Word |
| 48 | левый большой | Space | Space |
| 49 | левый большой | Alt | **Cmd** |
| 50 | левый большой | Ctrl | **NAV / Tab** |
| 51 | правый большой | `&lt 8` / Backspace | **SYM** / Backspace |
| 52 | правый большой | Space | Space |
| 53 | левый большой | Cmd | **Alt** |
| 54 | левый большой | `&mo 7` (corne_2) | **FUN / LANG_KEY** (Ctrl+Space) |
| 55 | правый большой | `&mt RALT ENTER` | **NUM** / Enter |
| A F ; | | `&lt 5` (caret) | буквы |
| S L | | `&lt 3` (scroll) | буквы |
| D K | | `&lt 2` (snipe) | буквы |
| B | | `&lt 4` (BT) | буква |

## Куда переехало содержимое старых слоёв

- F1–F12 (snipe) → FUN, те же позиции 0–11.
- Скобки `< { [ ( ) ] } >` (snipe) → SYM.
- Стрелки, Home/End/PgUp/PgDn (scroll, caret, corne_1) → NAV.
- Bluetooth (BT) → FUN, теперь на ряду Q (Q–T = профили 0–4), `BT_CLR_ALL` на A, `BT_CLR` на D, `BT_NXT` на G.
- Медиа, громкость, яркость, Mute (caret) → FUN.
- `\` (snipe/scroll, позиция 35) → комбо `[` + `'` и SYM (I).
- Alt/Cmd/Shift на S/D/F (caret) → NAV, те же позиции.

**Пропало совсем:** Cmd+Z/X/C/V и Shift+Cmd+Z на Y–P (caret), клавиша поиска `C_AC_SEARCH`, CapsLock (вместо него Caps Word), Insert, Shift+Home, вся эмуляция мыши corne_2 (включая клавиши прокрутки), отдельные клавиши Cmd+Space / Ctrl+Alt+Space / Alt+Space (corne_1/corne_2), `-` и `=` на слое scroll (есть комбо).

## Отступления от плана

| # | План | Сделано | Почему |
|---|------|---------|--------|
| 1 | Правится только `charybdis_right.overlay` | И `charybdis_dongle.overlay`: `caret_proc` → 4, тот же `excluded-positions` | Донгл подключает тот же keymap; иначе caret у донгла оказался бы на SYM |
| 2 | Узлы слоёв `BASE { … }` при `#define BASE 0` | Узлы `base_layer` … `fun_layer` + `display-name` | Препроцессор превратил бы `BASE {` в `0 {` |
| 3 | `caret-layers = <4>` на шаге 0 | На этапе 4, вместе с появлением NAV | До этого слой 4 был BT — caret оказался бы на B |
| 4 | Средняя кнопка на M (43) | Осталась на N (42) | План исходил из устаревшего README («клики на H/J/K»); на деле средняя была на N, K свободен |
| 5 | SNIPE и SCROLL целиком `&trans` | Клики H/J/N продублированы | Override snipe без `process-next` не продлевает таймер слоя мыши — после 0.8 с прицеливания J печатал бы `j` |
| 6 | `require-prior-idle-ms = <0>` у `&lt` | Свойство не задано | То же самое (по умолчанию выключено), без пограничного случая с нулём |
| 7 | Чек-лист: «54 + `1` = F1» | F1 на `` ` `` (позиция 0) | Спецификация слоя в плане («ряд 0–11: F1…F12») и старый слой snipe ставят F1 на позицию 0 |
| 8 | Чек-лист: «50 + J/K/L/; = стрелки» | Стрелки на H/J/K/L, `;` = Del | Так в спецификации NAV в самом плане |
| 9 | Скрипт проверки из шага 6 | `check_keymap.py` проверяет больше: роли слоёв в обоих overlay'ях, `#define` ↔ `display-name`, чистые буквы, прозрачность держателя | Номера слоёв продублированы в четырёх местах — это главный риск |
| 10 | Все шаги подряд | Поэтапно: комбо и Caps Word → K/L на MOUSE → моды → слои | Решение пользователя — привыкать по частям |

## Открытые вопросы

- `LANG_KEY` = Ctrl+Space — шорткат macOS. На Ubuntu (через DeskHop) по умолчанию Super+Space.
- Средняя кнопка: N или M.
- Комбо ограничены `layers = <BASE>` — пока поднят авто-слой мыши (0.8 с после движения шара), они не срабатывают.
- `&bootloader` есть только на левой половине (FUN + Z); правую — двойным нажатием reset.
