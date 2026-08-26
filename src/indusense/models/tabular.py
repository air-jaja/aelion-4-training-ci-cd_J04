# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/models/tabular.py
# [PÉDAGOGIE] MODULE  — M23–M24 — baseline supervisée et persistance du modèle
# [PÉDAGOGIE] RÔLE    — Fournir une chaîne d'entraînement et d'inférence déterministe pour les
# [PÉDAGOGIE]           données tabulaires.
# [PÉDAGOGIE] THÉORIE — random_state rend l'expérience comparable
# [PÉDAGOGIE]           • class_weight traite un déséquilibre sans inventer de nouvelles
# [PÉDAGOGIE]             observations
# [PÉDAGOGIE]           • la sérialisation doit voyager avec le contrat de features attendu
# [PÉDAGOGIE] À VOIR  — Une même entrée, un même modèle et un même seuil doivent reproduire la
# [PÉDAGOGIE]           même décision.
# [PÉDAGOGIE] PIÈGE   — Charger un modèle sans vérifier ses features ou sa provenance peut
# [PÉDAGOGIE]           produire une prédiction silencieusement fausse.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
NON_FEATURE_COLUMNS: tuple[str, ...] = ("machine", "timestamp")


# [PÉDAGOGIE] BLOC `select_features` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : df, target_col, exclude ; preuve : l'appelant doit pouvoir
# [PÉDAGOGIE] vérifier la sortie ou l'effet de bord annoncé.
def select_features(
    df: pd.DataFrame,
    target_col: str,
    exclude: tuple[str, ...] = NON_FEATURE_COLUMNS,
) -> pd.DataFrame:
    cols = [col for col in (*exclude, target_col) if col in df.columns]
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return df.drop(columns=cols)


# [PÉDAGOGIE] BLOC `train_model` — phase d'apprentissage : relier données, paramètres et modèle
# [PÉDAGOGIE] reproductible.
# [PÉDAGOGIE] CONTRAT — entrées : x, y, n_estimators, random_state ; preuve : conserver graine,
# [PÉDAGOGIE] split, métriques et artefact afin de pouvoir refaire l'expérience.
def train_model(
    x: pd.DataFrame,
    y: pd.Series,
    n_estimators: int = 200,
    random_state: int = 42,
) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        class_weight="balanced",
        random_state=random_state,
    )
    model.fit(x, y)
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return model


# [PÉDAGOGIE] BLOC `predict_proba` — phase d'inférence ou d'évaluation : appliquer un contrat gelé
# [PÉDAGOGIE] à des observations nouvelles.
# [PÉDAGOGIE] CONTRAT — entrées : model, x ; preuve : contrôler ordre des features, seuil,
# [PÉDAGOGIE] métriques et provenance du modèle.
def predict_proba(model: Any, x: pd.DataFrame) -> np.ndarray:
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return model.predict_proba(x)[:, 1]


# [PÉDAGOGIE] BLOC `save_model` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : model, path ; preuve : l'appelant doit pouvoir vérifier la
# [PÉDAGOGIE] sortie ou l'effet de bord annoncé.
def save_model(model: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


# [PÉDAGOGIE] BLOC `load_model` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def load_model(path: Path) -> Any:
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return joblib.load(path)
