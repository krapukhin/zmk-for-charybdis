/*
 * Печать уровня заряда в лог на уровне INFO.
 *
 * Зачем: в донгл-варианте хост общается с донглом по USB, а заряд ZMK отдаёт
 * через BAS — сервис Bluetooth. По USB этого канала нет, поэтому ни
 * bluetoothctl, ни upower батарею половин не покажут.
 *
 * Штатные сообщения ZMK про заряд все на уровне LOG_DBG (app/src/battery.c,
 * split/bluetooth/central.c). Включать DBG ради них нельзя: на донгле тогда
 * начнёт логироваться каждое событие указателя, а это 125 раз в секунду.
 *
 * Поэтому подписываемся на события сами и пишем одну строку на изменение,
 * на своём модуле логирования с жёстко заданным уровнем INFO — независимо
 * от того, какой уровень выставлен для zmk.
 *
 * Читать так:  cat /dev/ttyACM0        (или screen /dev/ttyACM0 115200)
 * Строка вида: BATTERY  0:72%  1:68%
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>

/* Уровень задан явно, а не через CONFIG_ZMK_LOG_LEVEL: эти строки должны быть
 * видны при обычном INFO, без включения DBG для всего остального. */
LOG_MODULE_REGISTER(zmk_battery_log, LOG_LEVEL_INF);

/*
 * Сколько половин помним. Событие BAS приходит только при ИЗМЕНЕНИИ уровня,
 * поэтому половина со стабильным зарядом молчала бы часами. Кэшируем последние
 * значения и печатаем все известные разом — так одна строка всегда показывает
 * полную картину.
 */
#define ZMK_BATTERY_LOG_MAX_PERIPHERALS 4

static uint8_t levels[ZMK_BATTERY_LOG_MAX_PERIPHERALS];
static bool known[ZMK_BATTERY_LOG_MAX_PERIPHERALS];

static void zmk_battery_log_print(void) {
    char buf[80];
    size_t off = 0;
    bool any = false;

    for (uint8_t i = 0; i < ZMK_BATTERY_LOG_MAX_PERIPHERALS; i++) {
        if (!known[i]) {
            continue;
        }
        int n = snprintf(buf + off, sizeof(buf) - off, "%s%u:%u%%", any ? "  " : "", i, levels[i]);
        if (n < 0 || (size_t)n >= sizeof(buf) - off) {
            break;
        }
        off += n;
        any = true;
    }

    if (any) {
        LOG_INF("BATTERY  %s", buf);
    }
}

static int zmk_battery_log_listener(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *periph =
        as_zmk_peripheral_battery_state_changed(eh);
    if (periph != NULL) {
        if (periph->source < ZMK_BATTERY_LOG_MAX_PERIPHERALS) {
            levels[periph->source] = periph->state_of_charge;
            known[periph->source] = true;
        }
        zmk_battery_log_print();
        return ZMK_EV_EVENT_BUBBLE;
    }

#if IS_ENABLED(CONFIG_ZMK_BATTERY_LOG_SELF)
    const struct zmk_battery_state_changed *own = as_zmk_battery_state_changed(eh);
    if (own != NULL) {
        LOG_INF("BATTERY self: %u%%", own->state_of_charge);
    }
#endif

    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(zmk_battery_log, zmk_battery_log_listener);
ZMK_SUBSCRIPTION(zmk_battery_log, zmk_peripheral_battery_state_changed);
#if IS_ENABLED(CONFIG_ZMK_BATTERY_LOG_SELF)
/*
 * Подписка на собственную батарею отключается на донгле: он на USB-питании,
 * ADC читает мусор, и строка была бы только шумом. Саму ZMK_BATTERY_REPORTING
 * при этом выключать нельзя — от неё зависит сборка событий заряда.
 */
ZMK_SUBSCRIPTION(zmk_battery_log, zmk_battery_state_changed);
#endif
