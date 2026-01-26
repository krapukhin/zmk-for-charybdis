Краткое саммари работ по Charybdis 4x6

  Проблема

  - Клавиатура периодически “зависала” по BT и по проводу. Трекбол иногда отваливался, помогал reset/переподключение.

  Диагностика

  - Выяснилось, что в твоем железе/прошивке MOSI и MISO “склеены” на P0.17, а IRQ/MOTION на P0.06.
  - Стандартный Zephyr драйвер PMW3610 не поддерживает 3‑wire/SDIO и требует отдельные MOSI/MISO + motion-gpios, поэтому с ним
    нестабильно.
  - Оригинальный репозиторий продавца использует отдельный драйвер zmk-pmw3610-driver и irq-gpios (а не motion-gpios), что рассчитано
    на такую разводку.

  Что сделали для “гибрида” (чтобы твоя раскладка сохранилась, но трекбол работал)

  1. Подключили локальный модуль zmk-pmw3610-driver-main и переименовали compatible, чтобы избежать конфликта с Zephyr:
      - zmk-pmw3610-driver-main/dts/bindings/pixart,pmw3610.yml → compatible: "pixart,pmw3610-zmk"
      - zmk-pmw3610-driver-main/src/pmw3610.c → #define DT_DRV_COMPAT pixart_pmw3610_zmk
      - config/boards/shields/charybdis/charybdis_right.overlay → compatible = "pixart,pmw3610-zmk"
  2. Убрали внешний модуль из config/west.yml и подключили локальный модуль в GH Actions:
      - build.yaml добавили -DZMK_EXTRA_MODULES=${GITHUB_WORKSPACE}/zmk-pmw3610-driver-main для left/right.
  3. Оверлей трекбола (важное):
      - MOSI/MISO остаются на P0.17 (как в оригинале)
      - irq-gpios = <&gpio0 6 (GPIO_ACTIVE_LOW | GPIO_PULL_UP)>
      - scroll-layers = <2>, snipe-layers = <1>

  Текущие ключевые настройки трекбола (config/boards/shields/charybdis/charybdis_right.conf)

  - CONFIG_PMW3610_CPI=3200
  - CONFIG_PMW3610_CPI_DIVIDOR=4
  - CONFIG_PMW3610_SNIPE_CPI=1600
  - CONFIG_PMW3610_SNIPE_CPI_DIVIDOR=4
  - CONFIG_PMW3610_SCROLL_TICK=70
  - CONFIG_PMW3610_INVERT_X=y
  - # CONFIG_PMW3610_SMART_ALGORITHM is not set
  - CONFIG_PMW3610_POLLING_RATE_125_SW=y
  - CONFIG_ZMK_EXT_POWER=y

  Слои (важное)

  - Snipe слой = 1 (активация &lt 1 на D/K/Comma)
  - Scroll слой = 2 (активация &lt 2 на F/J/V/Dot)
  - В драйвере используется “верхний активный слой” для режима: если держишь V — это scroll, не snipe.

  Ошибки и их исправления

  - Ошибка в GH Actions: ${{ github.workspace }} → заменили на ${GITHUB_WORKSPACE} в build.yaml.
  - Ошибка “No board named nice_nano” решилась заменой ZEPHYR_EXTRA_MODULES на ZMK_EXTRA_MODULES.
  - Kconfig не принимал SNIPE_CPI=100 (диапазон 200–3200) — вернули в диапазон.

  Текущие файлы, изменённые в результате

  - config/boards/shields/charybdis/charybdis_right.overlay
  - config/boards/shields/charybdis/charybdis_right.conf
  - config/west.yml
  - build.yaml
  - zmk-pmw3610-driver-main/dts/bindings/pixart,pmw3610.yml
  - zmk-pmw3610-driver-main/src/pmw3610.c

  Сборка

  - Используется GitHub Actions (workflow zmkfirmware). Сборка работает с ZMK_EXTRA_MODULES и локальным модулем zmk-pmw3610-driver-
    main.

  Примечания по настройке скорости

  - Итоговая скорость ≈ CPI / DIVIDOR.
  - CPI допустим 200–3200.
  - Snipe можно тонко настроить, например:
      - 3200/8, 1600/4, 800/2, 400/1 → дают одну скорость (400), но разные ощущения (точность/шум).

  Текущий статус

  - После перехода на драйвер продавца трекбол заработал.