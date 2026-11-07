
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split

FEATURE_LABELS = {
    "age": "Возраст",
    "sex": "Пол",
    "cp": "Тип боли в груди",
    "trestbps": "Артериальное давление",
    "chol": "Холестерин",
    "fbs": "Уровень глюкозы натощак",
    "restecg": "Результат ЭКГ",
    "thalach": "Максимальная ЧСС",
    "exang": "Стенокардия при нагрузке",
    "oldpeak": "Депрессия сегмента ST",
    "slope": "Наклон сегмента ST",
    "ca": "Число сосудов",
    "thal": "Результат исследования thal"
}


class HeartExplainer:
    def __init__(self, model, model_info, base_dir):
        self.features = model_info["input_features"]
        self.preprocessor = model.named_steps["preprocess"]
        self.classifier = model.named_steps["classifier"]

        dataset = pd.read_csv(
            base_dir / "data" / "heart_cleveland.csv"
        )

        X = dataset[self.features]
        y = dataset["heart_disease"]

        X_train, _ = train_test_split(
            X,
            test_size=0.20,
            random_state=42,
            stratify=y
        )

        background = X_train.sample(
            n=min(50, len(X_train)),
            random_state=42
        )

        background_processed = self.to_dense(
            self.preprocessor.transform(background)
        )

        self.explainer = shap.LinearExplainer(
            self.classifier,
            background_processed
        )

        self.transformed_names = (
            self.preprocessor.get_feature_names_out()
        )

    @staticmethod
    def to_dense(values):
        if hasattr(values, "toarray"):
            return values.toarray()
        return np.asarray(values)

    def explain(self, input_df):
        processed = self.to_dense(
            self.preprocessor.transform(input_df)
        )

        shap_values = self.explainer(processed).values[0]

        grouped = {
            feature: 0.0
            for feature in self.features
        }

        for transformed_name, value in zip(
            self.transformed_names, shap_values
        ):
            short_name = transformed_name.split("__", 1)[-1]

            matches = [
                feature for feature in self.features
                if short_name == feature
                or short_name.startswith(feature + "_")
            ]

            if not matches:
                raise ValueError(
                    f"Неизвестный признак: {transformed_name}"
                )

            original_feature = max(matches, key=len)
            grouped[original_feature] += float(value)

        top_factors = sorted(
            grouped.items(),
            key=lambda item: abs(item[1]),
            reverse=True
        )[:3]

        result = []

        for feature, impact in top_factors:
            if impact > 0:
                direction = "увеличивает"
            elif impact < 0:
                direction = "уменьшает"
            else:
                direction = "не изменяет"

            result.append({
                "name": FEATURE_LABELS.get(feature, feature),
                "direction": direction,
                "impact_log_odds": round(impact, 4)
            })

        return result
