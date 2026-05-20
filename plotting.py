"""
Модуль построения графиков на основе данных симуляции.

Использует matplotlib и pandas. Предоставляет функции:
- plot_time_domain: напряжение и ток из CSV,
- plot_spectrum: спектр гармоник из лога,
- plot_degradation: график THD от частоты.
"""

import matplotlib.pyplot as plt
import pandas as pd
from logger_config import logger


def plot_time_domain(csv_path: str):
    """
    Читает CSV с результатами симуляции и рисует два графика:
    верхний – V(signal), нижний – ток через нагрузку I(Rload).
    """
    logger.info(f"Построение временных графиков из {csv_path}")
    df = pd.read_csv(csv_path)

    # Проверка наличия нужных колонок
    if 'V(signal)' not in df.columns or 'I(Rload)' not in df.columns:
        logger.error("В CSV отсутствуют столбцы 'V(signal)' или 'I(Rload)'")
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Время в микросекундах для наглядности
    time_us = df['Time'] * 1e6

    ax1.plot(time_us, df['V(signal)'], color='blue', label='Выходное напряжение')
    ax1.set_ylabel('Напряжение (В)')
    ax1.set_title('Результаты симуляции ADA4870')
    ax1.grid(True, linestyle='--')
    ax1.legend()

    ax2.plot(time_us, df['I(Rload)'], color='red', label='Ток нагрузки')
    ax2.set_ylabel('Ток (А)')
    ax2.set_xlabel('Время (мкс)')
    ax2.grid(True, linestyle='--')
    ax2.legend()

    plt.tight_layout()
    plt.show()


def plot_spectrum(harmonics: list[int], amplitudes: list[float], thd_text: str = ""):
    """
    Строит столбцовый график амплитуд гармоник (в логарифмическом масштабе).
    harmonics – список номеров гармоник,
    amplitudes – соответствующие амплитуды в вольтах,
    thd_text – подпись с THD для заголовка.
    """
    if not harmonics:
        logger.warning("Нет данных гармоник для построения спектра")
        return

    logger.info("Построение спектра гармоник")
    plt.figure(figsize=(10, 6))
    plt.bar(harmonics, amplitudes, color='purple', alpha=0.7)
    plt.yscale('log')
    plt.title(f'Спектр выходного сигнала\nTHD = {thd_text}')
    plt.xlabel('Номер гармоники')
    plt.ylabel('Амплитуда (В)')
    plt.xticks(harmonics)
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.show()


def plot_degradation(frequencies: list[float], thd_list: list[float]):
    """
    Строит зависимость THD (%) от частоты (Гц) в логарифмическом масштабе.
    frequencies – список частот,
    thd_list – измеренные значения THD в процентах.
    """
    logger.info("Построение графика деградации THD")
    plt.figure(figsize=(10, 5))
    plt.semilogx(frequencies, thd_list, 'o-r', linewidth=2)
    plt.title('Деградация THD от частоты')
    plt.xlabel('Частота (Гц)')
    plt.ylabel('THD (%)')
    plt.grid(True, which='both', linestyle='--')
    plt.show()

def plot_input_currents(csv_path: str, r_tia: float):
    """
    Строит графики токов IOUTA и IOUTB, вычисляя их по напряжениям.
    """
    logger.info(f"Построение графиков токов из {csv_path}, R_TIA={r_tia} Ом")
    df = pd.read_csv(csv_path)

    required = ['V(inn)', 'V(n001)', 'V(inp)', 'V(n002)']
    if not all(col in df.columns for col in required):
        logger.warning("В CSV нет нужных колонок для вычисления токов. Пропускаем.")
        return

    iouta = (df['V(n001)'] - df['V(inn)']) / r_tia
    ioutb = (df['V(n002)'] - df['V(inp)']) / r_tia
    time_us = df['Time'] * 1e6

    plt.figure(figsize=(10, 5))
    plt.plot(time_us, iouta, label='IOUTA', color='blue')
    plt.plot(time_us, ioutb, label='IOUTB', color='red', linestyle='--')
    plt.xlabel('Время (мкс)')
    plt.ylabel('Ток (А)')
    plt.title('Входные токи IOUTA и IOUTB (расчёт по напряжениям)')
    plt.grid(True)
    plt.legend()
    plt.show()