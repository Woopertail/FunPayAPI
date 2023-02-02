"""
В данном модуле написаны вспомогательные функции.
"""

import string
import random


def gen_random_tag() -> str:
    """
    Генерирует случайный тег для запроса (для runner'а).

    :return: сгенерированный тег.
    """
    simbols = string.digits + string.ascii_lowercase
    tag = "".join(random.choice(simbols) for _ in range(10))
    return tag


def get_wait_time_from_raise_response(response: str) -> int:
    """
    Парсит ответ FunPay на запрос о поднятии лотов.

    :param response: текст ответа.

    :return: Примерное время ожидание до следующего поднятия лотов (в секундах).
    """
    if response == "Подождите секунду.":
        return 1
    elif "сек" in response:
        response = response.split()
        return int(response[1])
    elif response == "Подождите минуту.":
        return 60
    elif "мин" in response:
        response = response.split()
        # ["Подождите", "n", "минут."]
        return (int(response[1])-1) * 60
    elif "час" in response:
        return 3600
    else:
        return 10
