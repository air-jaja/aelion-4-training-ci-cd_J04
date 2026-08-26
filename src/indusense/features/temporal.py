# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/features/temporal.py
# [PÉDAGOGIE] MODULE  — M23 — features temporelles et prévention de la fuite
# [PÉDAGOGIE] RÔLE    — Construire lags et statistiques glissantes en n'utilisant que le passé de
# [PÉDAGOGIE]           chaque machine.
# [PÉDAGOGIE] THÉORIE — shift(1) exclut la ligne courante avant le rolling
# [PÉDAGOGIE]           • groupby isole les séries et interdit qu'une machine emprunte le passé
# [PÉDAGOGIE]             d'une autre
# [PÉDAGOGIE]           • le tri temporel est un prérequis du calcul et du test
# [PÉDAGOGIE] À VOIR  — Les premières lignes doivent contenir des NaN explicables et les tests
# [PÉDAGOGIE]           doivent détecter toute fuite.
# [PÉDAGOGIE] PIÈGE   — Calculer rolling avant shift injecte la valeur courante dans sa propre
# [PÉDAGOGIE]           caractéristique.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import pandas as pd


# [PÉDAGOGIE] BLOC `add_temporal_features` — unité de responsabilité : isoler un comportement
# [PÉDAGOGIE] nommable, testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : df, group_col, timestamp_col, value_cols, lags, windows ; preuve
# [PÉDAGOGIE] : l'appelant doit pouvoir vérifier la sortie ou l'effet de bord annoncé.
def add_temporal_features(
    df: pd.DataFrame,
    group_col: str = "machine",
    timestamp_col: str = "timestamp",
    value_cols: tuple[str, ...] = ("temperature", "pressure_bar"),
    lags: tuple[int, ...] = (1, 3, 6),
    windows: tuple[int, ...] = (3, 6),
) -> pd.DataFrame:
    """Add lag and rolling features per machine without temporal leakage."""
    required = {group_col, timestamp_col, *value_cols}
    missing = required - set(df.columns)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if missing:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")

    df = df.sort_values([group_col, timestamp_col]).reset_index(drop=True).copy()
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for col in value_cols:
        grouped = df.groupby(group_col)[col]
        # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur
        # [PÉDAGOGIE] un invariant stable.
        for lag in lags:
            df[f"{col}_lag{lag}"] = grouped.shift(lag)
        # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur
        # [PÉDAGOGIE] un invariant stable.
        for window in windows:
            df[f"{col}_roll{window}_mean"] = grouped.transform(
                lambda series, window=window: series.shift(1).rolling(window).mean()
            )
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return df
