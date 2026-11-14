"""Shared contract for the 13 educational model inputs."""

import math

RANGES = {
    "age": (18, 120), "trestbps": (70, 260), "chol": (80, 650),
    "thalach": (40, 250), "oldpeak": (0, 7),
}
CATEGORIES = {
    "sex": {0, 1}, "cp": {1, 2, 3, 4}, "fbs": {0, 1},
    "restecg": {0, 1, 2}, "exang": {0, 1}, "slope": {1, 2, 3},
    "ca": {0, 1, 2, 3}, "thal": {3, 6, 7},
}


class InputError(ValueError):
    def __init__(self, message, fields=None):
        super().__init__(message)
        self.fields = fields or []


def normalize_values(data, features):
    if not isinstance(data, dict):
        raise InputError("Необходим JSON-объект")
    missing = [field for field in features if field not in data]
    if missing:
        raise InputError("Отсутствуют обязательные поля", missing)
    values = {}
    for field in features:
        raw_value = data[field]
        if isinstance(raw_value, bool) or raw_value is None or str(raw_value).strip() == "":
            raise InputError(f"Неверное значение: {field}", [field])
        try:
            value = float(raw_value)
        except (ValueError, TypeError, OverflowError):
            raise InputError(f"Неверное значение: {field}", [field]) from None
        if not math.isfinite(value):
            raise InputError(f"Недопустимое число: {field}", [field])
        if field in RANGES and not RANGES[field][0] <= value <= RANGES[field][1]:
            raise InputError(f"Выход за пределы: {field}", [field])
        if field in CATEGORIES and value not in CATEGORIES[field]:
            raise InputError(f"Недопустимая категория: {field}", [field])
        values[field] = value
    return values
