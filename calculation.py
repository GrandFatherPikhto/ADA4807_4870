"""
Модуль расчёта номиналов выходного каскада ADA4870.

Содержит ряд E96, функцию округления до стандартных значений и основной алгоритм
подбора резисторов Ra, Rf, Rb и конденсатора Cf.

Формулы и логика описаны в Технической записке TN-2024-01.
"""

import math
from logger_config import logger

# 1% ряд E96 (только мантиссы). Полный набор для округления до ближайшего номинала.
E96_VALUES = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24,
    1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58,
    1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00,
    2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55,
    2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24,
    3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23,
    5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
    6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
    8.66, 8.87, 9.09, 9.31, 9.53, 9.76
]

def nearest_e96(value: float) -> float:
    """
    Возвращает ближайшее стандартное значение из ряда E96 (1%).
    Если value <= 0, возвращает 0.0.
    """
    if value <= 0:
        return 0.0
    exponent = math.floor(math.log10(value))
    mantissa = value / 10**exponent
    closest = min(E96_VALUES, key=lambda x: abs(x - mantissa))
    return round(closest * 10**exponent, 2)


def _compute_for_ra(Ra: float, A_v_required: float, params: dict) -> dict | None:
    """
    Рассчитывает Rf, Rb, Cf для заданного Ra.
    Возвращает словарь с номиналами или None, если Rf > Rf_max.
    """
    C_in_parasitic = params["C_in_parasitic"]
    Rf = A_v_required * Ra
    if Rf > params["Rf_max"]:
        return None
    
    Rb = (Ra * Rf) / (Ra + Rf)
    Rf_e96 = nearest_e96(Rf)
    Rb_e96 = nearest_e96(Rb)
    
    # Более точная Cf: учитывает реальное округлённое усиление Rf_e96 / Ra
    Cf_farad = C_in_parasitic * (Ra / Rf_e96)
    Cf_pf = round(Cf_farad * 1e12, 1)
    
    return {
        "Ra": Ra,
        "Rf": round(Rf, 1),
        "Rf_e96": Rf_e96,
        "Rb": round(Rb, 1),
        "Rb_e96": Rb_e96,
        "Cf": Cf_pf,
        "A_v_real": Rf_e96 / Ra
    }


def select_components(params: dict) -> list[dict]:
    """
    Основной алгоритм подбора Ra, Rf, Rb, Cf.
    Автоматически корректирует V_out_amp, если требуемое усиление невозможно.
    Возвращает список словарей, отсортированный по ошибке балансировки Rb,
    а затем по близости Rf к целевому значению (Rf_target).
    """
    logger.info("=== Старт подбора номиналов ===")

    # 1. Проверка ограничений по питанию и току
    V_max_amp = abs(params["V_sup"]) - params["V_headroom"]
    if params["V_out_amp"] > V_max_amp:
        logger.warning(f"Заданная амплитуда {params['V_out_amp']} В превышает "
                       f"максимальную {V_max_amp} В при запасе {params['V_headroom']} В")
        # Корректируем вниз до безопасного значения
        params["V_out_amp"] = V_max_amp
        logger.info(f"V_out_amp автоматически уменьшена до {V_max_amp} В")

    I_peak = params["V_out_amp"] / params["R_load"]
    if I_peak > params["I_out_max"]:
        msg = (f"Пиковый ток {I_peak:.3f} А превышает допустимый "
               f"{params['I_out_max']} А. Уменьшите V_out_amp или R_load.")
        logger.error(msg)
        raise ValueError(msg)

    # 2. Амплитуда дифференциального напряжения на выходе TIA
    V_diff_amp = params["I_FS"] * params["R_TIA"]
    if V_diff_amp == 0:
        msg = "Дифференциальное напряжение равно нулю (I_FS=0 или R_TIA=0)"
        logger.error(msg)
        raise ValueError(msg)

    A_v_required = params["V_out_amp"] / V_diff_amp
    # Проверка на клиппирование уже учтена через скорректированный V_out_amp
    logger.info(f"V_diff_amp = {V_diff_amp:.4f} В, требуемое усиление A_v = {A_v_required:.4f}")
    logger.info(f"Макс. амплитуда без клиппирования: ±{V_max_amp} В, пиковый ток нагрузки: {I_peak:.3f} А")

    # 3. Перебор Ra
    results = []
    for Ra in params["Ra_candidates"]:
        combo = _compute_for_ra(Ra, A_v_required, params)
        if combo is not None:
            results.append(combo)

    if not results:
        msg = "Не найдено подходящих комбинаций Ra/Rf/Rb/Cf с заданными ограничениями."
        logger.error(msg)
        raise ValueError(msg)

    # 4. Логирование таблицы результатов
    header = f"\n{'Ra':>6} | {'Rf(расч)':>10} | {'Rf(E96)':>8} | {'Rb(расч)':>10} | {'Rb(E96)':>8} | {'Cf(пФ)':>6} | {'A_v':>6}"
    logger.info(header)
    logger.info("-" * len(header))
    for r in results:
        logger.info(f"{r['Ra']:6} | {r['Rf']:10.1f} | {r['Rf_e96']:8.1f} | "
                    f"{r['Rb']:10.1f} | {r['Rb_e96']:8.1f} | {r['Cf']:6.1f} | {r['A_v_real']:6.3f}")

    # 5. Сортировка: сначала по ошибке Rb, затем по относительной ошибке Rf
    target_rf = params.get("Rf_target", 1210.0)
    for rec in results:
        rec['Rb_error_abs'] = abs(rec['Rb'] - rec['Rb_e96'])
        rec['Rf_error_rel'] = abs(rec['Rf_e96'] - target_rf) / target_rf

    results.sort(key=lambda x: (x['Rb_error_abs'], x['Rf_error_rel']))

    logger.info(f"Найдено {len(results)} подходящих комбинаций")
    logger.info("Комбинации отсортированы по ошибке балансировки Rb, затем по близости Rf к целевому значению.")

    return results