/*
 * Caret mode как input-процессор ZMK.
 *
 * Зачем отдельный процессор, если в драйвере caret уже есть: драйверная версия
 * работает только на central. В донгл-варианте трекбол висит на периферии, где
 * нет ни раскладки, ни возможности слать коды клавиш (src/keymap.c и
 * src/events/keycode_state_changed.c в ZMK собираются только для central).
 * Процессор же выполняется на том устройстве, которое держит раскладку, —
 * значит на донгле caret снова возможен.
 *
 * Логика перенесена из pmw3610.c один в один, включая две вещи, которые там
 * чинились по живому:
 *   - порог ВЫЧИТАЕТСЯ, а не обнуляется: остаток переносится в следующее
 *     событие, иначе каретка отстаёт тем сильнее, чем быстрее ведёшь;
 *   - фиксация оси: сработавшая ось гасит накопитель второй, иначе на трекболе
 *     не провести строго по горизонтали без вертикального дрейфа.
 *
 * Порог задаётся первым параметром в devicetree: <&zip_caret 60>.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_input_processor_caret

#include <stdlib.h>

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/input/input.h>
#include <drivers/input_processor.h>

#include <dt-bindings/zmk/keys.h>
#include <zmk/events/keycode_state_changed.h>

#include <zephyr/logging/log.h>

/*
 * Собственный модуль логирования, а не DECLARE чужого.
 * pmw3610.c регистрирует модуль pmw3610, но на донгле CONFIG_PMW3610 выключен
 * и тот файл не собирается — DECLARE(pmw3610) там не слинковался бы.
 * DECLARE(zmk) тоже ненадёжен: это модуль из другой библиотеки.
 */
LOG_MODULE_REGISTER(zmk_caret, CONFIG_INPUT_LOG_LEVEL);

/*
 * Предохранитель: сколько стрелок максимум отправляем за одно событие.
 * Каждая — полноценная пара press+release, это дороже обычного репорта.
 * 4 при 125 Гц опроса недостижимо рукой; ограничение на случай абсурдного
 * порога. Неотправленное остаётся в накопителе и уйдёт следующим событием.
 */
#define ZMK_CARET_MAX_TICKS_PER_EVENT 4

struct caret_data {
    int32_t delta_x;
    int32_t delta_y;
};

static void caret_send(uint32_t keycode, int32_t count) {
    for (int32_t i = 0; i < count; i++) {
        int64_t timestamp = k_uptime_get();
        raise_zmk_keycode_state_changed_from_encoded(keycode, true, timestamp);
        raise_zmk_keycode_state_changed_from_encoded(keycode, false, timestamp);
    }
}

static int caret_handle_event(const struct device *dev, struct input_event *event, uint32_t param1,
                              uint32_t param2, struct zmk_input_processor_state *state) {
    struct caret_data *data = (struct caret_data *)dev->data;

    ARG_UNUSED(param2);
    ARG_UNUSED(state);

    if (event->type != INPUT_EV_REL) {
        return ZMK_INPUT_PROC_CONTINUE;
    }

    const int32_t tick = (param1 > 0) ? (int32_t)param1 : 1;

    if (event->code == INPUT_REL_X) {
        data->delta_x += event->value;
    } else if (event->code == INPUT_REL_Y) {
        data->delta_y += event->value;
    } else {
        return ZMK_INPUT_PROC_CONTINUE;
    }

    int32_t ticks_y = data->delta_y / tick;
    int32_t ticks_x = data->delta_x / tick;

    if (ticks_y != 0) {
        int32_t n = MIN(abs(ticks_y), ZMK_CARET_MAX_TICKS_PER_EVENT);
        uint32_t keycode = (ticks_y > 0) ? DOWN_ARROW : UP_ARROW;
        LOG_DBG("caret: %s x%d", (ticks_y > 0) ? "DOWN" : "UP", n);
        data->delta_y -= (ticks_y > 0 ? n : -n) * tick;
        caret_send(keycode, n);
        data->delta_x = 0; /* фиксация оси */
    } else if (ticks_x != 0) {
        int32_t n = MIN(abs(ticks_x), ZMK_CARET_MAX_TICKS_PER_EVENT);
        uint32_t keycode = (ticks_x > 0) ? RIGHT_ARROW : LEFT_ARROW;
        LOG_DBG("caret: %s x%d", (ticks_x > 0) ? "RIGHT" : "LEFT", n);
        data->delta_x -= (ticks_x > 0 ? n : -n) * tick;
        caret_send(keycode, n);
        data->delta_y = 0; /* фиксация оси */
    }

    /*
     * Съедаем событие: в режиме каретки курсор двигаться не должен, движение
     * шара целиком превращается в стрелки.
     */
    return ZMK_INPUT_PROC_STOP;
}

static struct zmk_input_processor_driver_api caret_driver_api = {
    .handle_event = caret_handle_event,
};

#define CARET_INST(n)                                                                              \
    static struct caret_data caret_data_##n = {};                                                  \
    DEVICE_DT_INST_DEFINE(n, NULL, NULL, &caret_data_##n, NULL, POST_KERNEL,                        \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &caret_driver_api);

DT_INST_FOREACH_STATUS_OKAY(CARET_INST)
