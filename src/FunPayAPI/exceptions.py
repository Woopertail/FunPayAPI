"""
В данном модуле описаны кастомные исключения, которые могут райзиться во время работы с FunPayAPI.
"""


class StatusCodeIsNot200(Exception):
    """
    Исключение, которое райзится, если код ответа от FunPay != 200
    """
    def __init__(self, status_code: int):
        """
        :param status_code: полученный статус код.
        """
        self.status_code = status_code

    def __str__(self):
        return f"Не удалось получить ответ от FunPay (статус-код: {self.status_code})."


class AccountDataNotfound(Exception):
    """
    Исключение, которое райзится, если не удалось получить данные об аккаунте.
    """
    def __init__(self):
        pass

    def __str__(self):
        return "Не удалось получить данные об аккаунте. (Возможно, введен неправильный токен?)"


class NotAuthorized(Exception):
    """
    Исключение, которое райзится, когда происходит попытка произвести действия с аккаунтом при не инициализированном
    классе аккаунта.
    """
    def __init__(self):
        pass

    def __str__(self):
        return "Класс аккаунта не инициализирован. Используйте метод Account.get() для инициализации."


class MessageNotDelivered(Exception):
    """
    Исключение, которое райзится, если не удалось доставить сообщение.
    """

    def __init__(self, response: dict):
        self.response = response

    def __str__(self):
        return f"Не удалось отправить сообщение. Ответ сервера: {self.response}"


class LotNotUpdated(Exception):
    """
    Исключение, которое райзится, если не удается сохранить обновить лот.
    """
    def __init__(self, response: dict):
        self.response = response

    def __str__(self):
        return f"Не удалось обновить лот. Ответ сервера {self.response}"
