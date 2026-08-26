# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_loaders.py
# [PÉDAGOGIE] MODULE  — M23 — ingestion hétérogène, normalisation et jointure temporelle
# [PÉDAGOGIE] RÔLE    — Transformer plusieurs formats sources en un contrat tabulaire commun et
# [PÉDAGOGIE]           fabriquer la cible sans mélange de machines.
# [PÉDAGOGIE] THÉORIE — la normalisation d'identifiant rend les jointures explicites
# [PÉDAGOGIE]           • merge_asof rapproche des mesures temporelles dans une tolérance
# [PÉDAGOGIE]             contrôlée
# [PÉDAGOGIE]           • la clé machine et l'ordre chronologique empêchent une association
# [PÉDAGOGIE]             inter-équipements
# [PÉDAGOGIE] À VOIR  — Contrôler schéma, nombre de lignes perdues, ordre des dates et
# [PÉDAGOGIE]           distribution de la cible.
# [PÉDAGOGIE] PIÈGE   — Dans les fichiers SQL, ne jamais ajouter en commentaire un faux tuple
# [PÉDAGOGIE]           ressemblant aux données chargées.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] DÉPENDANCE — pathlib : manipule les chemins sans dépendre du séparateur
# [PÉDAGOGIE] Windows/Linux/macOS.
from pathlib import Path

import pandas as pd
import pytest

from indusense.data.loaders import (
    build_dataset,
    load_incidents,
    load_pressure,
    load_temperature,
    normalize_machine_id,
)

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


# [PÉDAGOGIE] BLOC `test_normalize_machine_id_variants` — ce test transforme un comportement
# [PÉDAGOGIE] attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : raw, expected ; preuve : la dernière assertion est l'oracle :
# [PÉDAGOGIE] son échec doit pointer la garantie cassée.
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MACH-01", "MACH-01"),
        ("MACH_01", "MACH-01"),
        ("M-06", "MACH-06"),
        ("M-2", "MACH-02"),
        ("M_07", "MACH-07"),
    ],
)
def test_normalize_machine_id_variants(raw, expected):
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert normalize_machine_id(raw) == expected


# [PÉDAGOGIE] BLOC `test_normalize_machine_id_without_number_raises` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_normalize_machine_id_without_number_raises():
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with pytest.raises(ValueError):
        normalize_machine_id("NOPE")


# [PÉDAGOGIE] BLOC `test_build_dataset_has_binary_target` — ce test transforme un comportement
# [PÉDAGOGIE] attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_build_dataset_has_binary_target():
    temp = load_temperature(SAMPLE / "capteurs_temperature.csv")
    pres = load_pressure(SAMPLE / "capteurs_pression.tsv")
    inc = load_incidents(SAMPLE / "releves_incidents.csv")

    dataset = build_dataset(temp, pres, inc, window_hours=24)

    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert {"machine", "timestamp", "temperature", "pressure_bar", "panne"} <= set(dataset.columns)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert set(dataset["panne"].unique()) <= {0, 1}
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert 0 < dataset["panne"].mean() < 0.5


# [PÉDAGOGIE] BLOC `test_merge_asof_never_matches_other_machine` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_merge_asof_never_matches_other_machine():
    temp = pd.DataFrame(
        {
            "machine": ["MACH-01", "MACH-02"],
            "timestamp": pd.to_datetime(["2026-01-01 12:00", "2026-01-01 12:01"]),
            "temperature": [50.0, 60.0],
        }
    )
    pres = pd.DataFrame(
        {
            "machine": ["MACH-02", "MACH-01"],
            "timestamp": pd.to_datetime(["2026-01-01 12:00", "2026-01-01 20:00"]),
            "pressure_bar": [180.0, 999.0],
        }
    )
    inc = pd.DataFrame(columns=["machine", "incident_ts"])

    dataset = build_dataset(temp, pres, inc, window_hours=24, tolerance_minutes=90)

    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert list(dataset["machine"]) == ["MACH-02"]
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert dataset.iloc[0]["pressure_bar"] == 180.0
