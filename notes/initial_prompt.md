# Контекст: Моя клавиатура Charybdis 4x6

## Железо
- Клавиатура: **Charybdis 4x6** (split ergonomic с трекболом)
- Контроллер: **nice!nano v2** (указывается как `nice_nano@2.0.0` в build.yaml)
- Прошивка: **ZMK** (Bluetooth) на **Zephyr 4.1** (декабрь 2025)
- Трекбол: **PMW3610** (правая половина) — встроенный драйвер Zephyr

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
- 1: F_layers — F1-F12, кнопки мыши (активация: MO1 большим пальцем)
- 2: BT_layers — Bluetooth (активация: удержание B)
- 3: scroll-layers — трекбол как прокрутка (активация: удержание C)
- 4: snipe-layers — точный режим трекбола (активация: удержание V или ,)
- 5: symbols_layer — программистские символы (активация: удержание X или .)
- 6: hyper_layer — Ctrl+Shift+Option+Cmd+буква (активация: удержание DEL)

### Home Row Mods
Левая: A=Ctrl, S=Alt, D=Shift, F=GUI
Правая: J=GUI, K=Shift, L=Alt, ;=Ctrl
Настройки: tapping-term-ms=280, require-prior-idle-ms=150

### Combos
- Q+W → [, W+E → ], E+R → (, R+T → )
- A+S → {, S+D → }
- J+K → Ctrl+Space (переключение языка)
- TAB+Q → Cmd+` (переключение окон приложения)

### Трекбол (PMW3610)
- **Драйвер**: встроенный Zephyr 4.1 (не внешний модуль)
- **CPI**: 2000
- **Scroll режим** (слой 3): скорость ÷32, инверсия Y
- **Snipe режим** (слой 4): скорость ÷4
- **Реализация**: ZMK input processors (`zip_xy_scaler`, `zip_xy_to_scroll_mapper`, `zip_scroll_transform`)

### Особенности
- CapsLock заменён на Escape
- Глубокий сон отключён (CONFIG_ZMK_SLEEP=n)
- Board revision: nice_nano@2.0.0 (Zephyr 4.1 формат)

## Репозиторий
zmk-for-charybdis/ содержит:
- `config/charybdis.keymap` — раскладка
- `config/charybdis.conf` — общие настройки
- `config/boards/shields/charybdis/charybdis_right.conf` — настройки правой половины
- `config/boards/shields/charybdis/charybdis_right.overlay` — devicetree с трекболом и input processors
- `config/west.yml` — манифест зависимостей (только ZMK, без внешних драйверов)
- `build.yaml` — конфигурация сборки GitHub Actions
