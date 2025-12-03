# Контекст: Моя клавиатура Charybdis 4x6

## Железо
- Клавиатура: **Charybdis 4x6** (split ergonomic с трекболом)
- Контроллер: **nice!nano v2**
- Прошивка: **ZMK** (Bluetooth)
- Трекбол: **PMW3610** (правая половина)

## Система
- macOS
- Raycast для хоткеев с Hyper Key

## Профиль пользователя
- Программист
- Слепая печать
- Русская + английская раскладки
- Использую Vim

## Текущая конфигурация

### Слои (layers)
- 0: QWERTY — основной
- 1: F_layers — F1-F12, стрелки (активация: MO1 большим пальцем)
- 2: BT_layers — Bluetooth (активация: удержание B)
- 3: scroll-layers — трекбол как прокрутка (активация: удержание X)
- 4: snipe-layers — точный режим трекбола 300 DPI (активация: удержание Z)
- 5: symbols_layer — программистские символы (активация: удержание C)
- 6: hyper_layer — Ctrl+Shift+Option+Cmd+буква (активация: удержание V)

### Home Row Mods
Левая: A=Ctrl, S=Alt, D=Shift, F=GUI
Правая: J=GUI, K=Shift, L=Alt, ;=Ctrl
Настройки: tapping-term-ms=280, require-prior-idle-ms=150

### Combos
- Q+W → [, W+E → ], E+R → (, R+T → )
- A+S → {, S+D → }
- J+K → Cmd+Space (переключение языка)

### Особенности
- CapsLock заменён на Escape
- Глубокий сон отключён (CONFIG_ZMK_SLEEP=n)
- DPI трекбола: 1600 (обычный), 300 (snipe)

## Репозиторий
zmk-for-charybdis/ содержит:
- config/charybdis.keymap — раскладка
- config/charybdis.conf — общие настройки
- config/boards/shields/charybdis/charybdis_right.conf — настройки правой половины с трекболом