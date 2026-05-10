"""
Модуль настройки логирования.
Все части проекта импортируют настроенный логгер 'ADASim'.
Уровень по умолчанию INFO, в файл пишется DEBUG.
"""

import logging
import sys

def setup_logging(log_file: str = "simulation.log") -> logging.Logger:
    """
    Создаёт и настраивает логгер с именем 'ADASim'.
    Возвращает глобальный экземпляр, который можно использовать во всех модулях.
    """
    logger = logging.getLogger('ADASim')
    logger.setLevel(logging.DEBUG)  # Максимальная детализация для файла

    # Формат сообщений: время, уровень, имя модуля, сообщение
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s.%(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обработчик для файла – сохраняет всё от DEBUG и выше
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Консольный обработчик – выводим INFO и выше
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

# Глобальный объект логгера для импорта
logger = logging.getLogger('ADASim')