"""Server-side validation of model features (independent from Flask)."""
import math

RANGES = {
    "age": (18, 120),
    "trestbps": (70, 260),
    "chol": (80, 650),
    "thalach": (40, 250),
    "oldpeak": (0, 7),
}
CATEGORIES = {
    "sex": {0, 1},
    "cp": {1, 2, 3, 4},
    "fbs": {0, 1},
    "restecg": {0, 1, 2},
    "exang": {0, 1},
    "slope": {1, 2, 3},
    "ca": {0, 1, 2, 3},
    "thal": {3, 6, 7},
}

class ValidationError(ValueError):
    def __init__(self, code, message, *, fields=None):
        super().__init__(message)
        self.code = code
        self.fields = list(fields or [])


def validate_payload(data, features):
    if not isinstance(data, dict):
        raise ValidationError("INVALID_PAYLOAD", "Необходим JSON-объект")
    missing = [name for name in features if name not in data]
    if missing:
        raise ValidationError("MISSING_FIELDS", "Отсутствуют обязательные поля", fields=missing)
    unexpected = [name for name in data if name not in features]
    if unexpected:
        raise ValidationError("UNEXPECTED_FIELDS", "Неизвестные поля", fields=unexpected)

    values = {}
    for field in features:
        raw = data[field]
        if isinstance(raw, bool) or raw is None or isinstance(raw, (dict, list)):
            raise ValidationError("INVALID_FIELD", f"Неверное значение: {field}", fields=[field])
        # Reject strings (e.g. 'NaN', 'True' or ambiguously formatted numbers).
        # Browser sends numbers via JSON.stringify; all 13 features are numeric.
        if not isinstance(raw, (int, float)):
            raise ValidationError("INVALID_FIELD", f"Неверное значение: {field}", fields=[field])
        try:
            value = float(raw)
        except (ValueError, TypeError, OverflowError):
            raise ValidationError("INVALID_FIELD", f"Неверное значение: {field}", fields=[field]) from None
        if not math.isfinite(value):
            raise ValidationError("INVALID_FIELD", f"Недопустимое число: {field}", fields=[field])
        if field in RANGES:
            minimum, maximum = RANGES[field]
            if not minimum <= value <= maximum:
                raise ValidationError("OUT_OF_RANGE", f"Выход за пределы: {field}", fields=[field])
            if field != "oldpeak" and not value.is_integer():
                raise ValidationError("INVALID_FIELD", f"Ожидается целое число: {field}", fields=[field])
        if field in CATEGORIES and value not in CATEGORIES[field]:
            raise ValidationError("INVALID_CATEGORY", f"Недопустимая категория: {field}", fields=[field])
        values[field] = value
    return values
