"""Illustrative, non-diagnostic cross-field data-entry checks (CARD-17)."""


def check_anomalies(values):
    """Return warnings without changing values or blocking a valid prediction.

    These example thresholds are for a synthetic-data classroom exercise only.
    They are NOT clinical cutoffs and must not be used for patient assessment.
    """
    warnings = []

    if values["trestbps"] >= 220 and values["chol"] >= 450:
        warnings.append({
            "fields": ["trestbps", "chol"],
            "message": "Проверьте введённые давление и холестерин: сочетание помечено учебным правилом проверки ввода.",
        })

    if values["age"] >= 70 and values["thalach"] >= 200:
        warnings.append({
            "fields": ["age", "thalach"],
            "message": "Проверьте возраст и максимальную ЧСС: сочетание помечено учебным правилом проверки ввода.",
        })

    return warnings
