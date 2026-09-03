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
 *
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>

/* Уровень задан явно, а не через CONFIG_ZMK_LOG_LEVEL: эти строки должны быть
 * видны при обычном INFO, без включения DBG для всего остального. */
LOG_MODULE_REGISTER(zmk_battery_log, LOG_LEVEL_INF);

static int zmk_battery_log_listener(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *periph =
        as_zmk_peripheral_battery_state_changed(eh);
    if (periph != NULL) {
        /* source — индекс периферии в порядке подключения к central.
         * Какая половина под каким номером, надёжнее определить опытом:
         * разрядить одну сильнее и посмотреть, чьё число просело. */
        LOG_INF("BATTERY peripheral %u: %u%%", periph->source, periph->state_of_charge);
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
