# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_temporal.py
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

# [PÉDAGOGIE] DÉPENDANCE — pandas : porte les tableaux typés et les transformations de données.
import pandas as pd
import pytest

from indusense.features.temporal import add_temporal_features


# [PÉDAGOGIE] BLOC `test_temporal_features_do_not_use_current_value` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_temporal_features_do_not_use_current_value():
    df = pd.DataFrame(
        {
            "machine": ["MACH-01"] * 4,
            "timestamp": pd.date_range("2025-01-01", periods=4, freq="h"),
            "temperature": [10.0, 20.0, 30.0, 40.0],
            "pressure_bar": [195.0, 196.0, 197.0, 198.0],
        }
    )
    out = add_temporal_features(df, value_cols=("temperature",), lags=(1,), windows=(2,))

    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert out["temperature_lag1"].isna().iloc[0]
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert out["temperature_roll2_mean"].iloc[2] == 15.0


# [PÉDAGOGIE] BLOC `test_temporal_features_sort_by_machine_and_time` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_temporal_features_sort_by_machine_and_time():
    df = pd.DataFrame(
        {
            "machine": ["MACH-01", "MACH-02", "MACH-01", "MACH-02"],
            "timestamp": pd.to_datetime(
                ["2025-01-01 01:00", "2025-01-01 00:00", "2025-01-01 00:00", "2025-01-01 01:00"]
            ),
            "temperature": [11.0, 20.0, 10.0, 21.0],
            "pressure_bar": [196.0, 205.0, 195.0, 206.0],
        }
    )
    out = add_temporal_features(df, value_cols=("temperature",), lags=(1,), windows=(2,))

    m1 = out[out["machine"] == "MACH-01"].reset_index(drop=True)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert m1.loc[1, "temperature_lag1"] == 10.0


# [PÉDAGOGIE] BLOC `test_temporal_features_missing_column_raises` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_temporal_features_missing_column_raises():
    df = pd.DataFrame({"machine": ["MACH-01"], "timestamp": pd.to_datetime(["2025-01-01"])})
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with pytest.raises(ValueError):
        add_temporal_features(df, value_cols=("temperature",))
