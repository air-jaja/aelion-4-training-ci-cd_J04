# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_predict_flow.py
# [PÉDAGOGIE] MODULE  — M29/M30 — pipeline orchestre et idempotent
# [PÉDAGOGIE] RÔLE    — Prouver l'idempotence par le COMPTAGE, et la bascule d'horodatage
# [PÉDAGOGIE]           entre SQLite et PostgreSQL.
# [PÉDAGOGIE] THÉORIE — l'idempotence se PROUVE en rejouant, pas en relisant le code
# [PÉDAGOGIE]           • deux runs, deux comptages : s'ils different, le contrat est rompu
# [PÉDAGOGIE]           • un INSERT sans ON CONFLICT passerait tous les autres tests
# [PÉDAGOGIE] À VOIR  — Le test qui compte avant/apres : c'est la seule preuve qui vaille.
# [PÉDAGOGIE] PIÈGE   — Tester l'idempotence sur une base vide ne prouve rien : il faut
# [PÉDAGOGIE]           ecrire, puis RE-ecrire les memes cles.
# [PÉDAGOGIE] GARDE   — Tout tourne en SQLite temporaire : aucun serveur requis.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_predict_flow.py
# -----------------------------------------------------------------------------
# CE QUI EST VERIFIE ICI (sans Docker ni PostgreSQL) :
#   1. ingest produit le bon volume et un taux de cible mesurable ;
#   2. predict renvoie UNE ligne par machine, la plus recente ;
#   3. store est IDEMPOTENT : deux passages, meme nombre de lignes ;
#   4. la bascule d'horodatage renvoie str en SQLite, datetime sinon.
#
# CE QUI N'EST PAS VERIFIE ICI : PostgreSQL reel et Compose. La syntaxe
# `ON CONFLICT` est identique dans les deux dialectes, mais seule l'execution
# dans la stack le confirme.
# =============================================================================

import datetime

import pandas as pd
import pytest
from prefect.testing.utilities import prefect_test_harness
from sqlalchemy import create_engine, text

from indusense.config import settings
from indusense.flows.predict_flow import (
    COLONNES_SORTIE,
    creer_table,
    feature,
    horodatage_pour_sql,
    ingest,
    predict,
    predict_flow,
    store,
    taux_cible,
)

DATA_DIR = settings.data_dir
MODEL_DIR = settings.model_dir


# [PÉDAGOGIE] BLOC `harnais_prefect` — UN serveur temporaire pour tout le fichier, au lieu
# [PÉDAGOGIE] d'un par appel de flow. Sans lui, chaque test paierait le demarrage complet.
@pytest.fixture(scope="session", autouse=True)
def harnais_prefect():
    with prefect_test_harness():
        yield


@pytest.fixture
def base_temporaire(tmp_path):
    """URL SQLite jetable, une par test."""
    return f"sqlite:///{tmp_path / 'test.db'}"


def _compter(db_url: str, table: str = "predictions") -> int:
    """Nombre de lignes dans la table."""
    with create_engine(db_url).begin() as cx:
        return int(cx.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


# =============================================================================
# PARTIE 1 — INGEST
# =============================================================================


# [PÉDAGOGIE] BLOC — `.fn` appelle la fonction brute, sans passer par l'orchestration.
def test_ingest_produit_un_dataset_exploitable():
    """ingest renvoie des lignes, des machines et une cible binaire."""
    dataset = ingest.fn(DATA_DIR, settings.incident_window_hours)

    assert len(dataset) > 0
    assert dataset["machine"].nunique() > 0
    assert settings.target_col in dataset.columns
    assert set(dataset[settings.target_col].unique()) <= {0, 1}


# [PÉDAGOGIE] BLOC — le taux de cible est le premier indicateur d'un jeu de donnees remplace.
# [PÉDAGOGIE] ATTENTION — la valeur DEPEND du jeu monte via INDUSENSE_DATA_DIR : ~10,4 % sur
# [PÉDAGOGIE] les donnees du depot (4 machines), ~4,78 % annonce pour le jeu complet.
# [PÉDAGOGIE] D'ou une PLAGE plutot qu'une egalite : le test doit accepter les deux.
def test_taux_cible_est_dans_la_plage_attendue():
    """Le taux de la colonne cible reste dans une plage plausible.

    GARDE-FOU, pas assertion exacte : un taux qui s'effondre a 0 % ou grimpe
    a 50 % signale un jeu corrompu ou une fenetre d'etiquetage erronee, bien
    avant que les predictions ne deviennent absurdes.
    """
    taux = taux_cible(ingest.fn(DATA_DIR, settings.incident_window_hours))

    assert 1.0 < taux < 25.0, f"taux inattendu : {taux:.2f} %"


# =============================================================================
# PARTIE 2 — PREDICT
# =============================================================================


# [PÉDAGOGIE] BLOC — UNE ligne par machine : une prediction porte sur l'etat COURANT.
def test_predict_renvoie_une_ligne_par_machine():
    """Le nombre de predictions egale le nombre de machines."""
    dataset = ingest.fn(DATA_DIR, settings.incident_window_hours)
    predictions = predict.fn(feature.fn(dataset), MODEL_DIR, seuil=0.5)

    assert len(predictions) == dataset["machine"].nunique()
    assert predictions["machine"].is_unique


# [PÉDAGOGIE] BLOC — la ligne retenue doit etre la PLUS RECENTE de chaque machine.
def test_predict_retient_le_dernier_releve():
    """Chaque prediction porte l'horodatage maximal de sa machine."""
    dataset = ingest.fn(DATA_DIR, settings.incident_window_hours)
    predictions = predict.fn(feature.fn(dataset), MODEL_DIR, seuil=0.5)
    attendus = dataset.groupby("machine")["timestamp"].max()

    for ligne in predictions.itertuples(index=False):
        assert pd.Timestamp(ligne.prediction_ts) == attendus[ligne.machine]


# [PÉDAGOGIE] BLOC — contrat de sortie stable : ni champ manquant, ni champ surprise.
def test_predict_respecte_le_contrat_de_colonnes():
    """Les colonnes de sortie sont exactement celles declarees."""
    dataset = ingest.fn(DATA_DIR, settings.incident_window_hours)
    predictions = predict.fn(feature.fn(dataset), MODEL_DIR, seuil=0.5)

    assert tuple(predictions.columns) == COLONNES_SORTIE


# [PÉDAGOGIE] BLOC — la decision doit decouler du SEUIL, pas d'une valeur figee.
def test_decision_coherente_avec_le_seuil():
    """`decision` vaut "alerte" si et seulement si proba >= seuil."""
    enrichi = feature.fn(ingest.fn(DATA_DIR, settings.incident_window_hours))

    # Seuil a 0 : toutes les lignes basculent en alerte.
    assert set(predict.fn(enrichi, MODEL_DIR, seuil=0.0)["decision"]) == {"alerte"}
    # Seuil au-dessus de 1 : aucune alerte possible.
    assert set(predict.fn(enrichi, MODEL_DIR, seuil=1.01)["decision"]) == {"ok"}


# =============================================================================
# PARTIE 3 — L'IDEMPOTENCE, prouvee par comptage
# =============================================================================


# [PÉDAGOGIE] BLOC — LE test du jalon : deux passages, meme nombre de lignes.
def test_deux_executions_ne_dupliquent_pas(base_temporaire):
    """Rejouer le flow ne cree aucune ligne supplementaire.

    Preuve exigee par le jalon : un INSERT sans ON CONFLICT aurait double le
    compte, et TOUS les autres tests seraient pourtant passes.
    """
    total_1 = predict_flow(db_url=base_temporaire)
    total_2 = predict_flow(db_url=base_temporaire)

    assert total_1 == total_2
    assert _compter(base_temporaire) == total_1


# [PÉDAGOGIE] BLOC — trois passages : l'idempotence n'est pas un hasard du second appel.
def test_trois_executions_restent_stables(base_temporaire):
    """Le compte ne bouge plus apres le premier passage."""
    comptes = [predict_flow(db_url=base_temporaire) for _ in range(3)]

    assert len(set(comptes)) == 1, f"comptes instables : {comptes}"


# [PÉDAGOGIE] BLOC — l'upsert MET A JOUR : la valeur change, la ligne reste unique.
def test_upsert_met_a_jour_sans_dupliquer(base_temporaire):
    """Reecrire la meme cle avec une autre valeur remplace la ligne."""
    predictions = pd.DataFrame(
        [
            {
                "machine": "MACH-99",
                "prediction_ts": pd.Timestamp("2026-01-01 12:00"),
                "proba_panne": 0.10,
                "decision": "ok",
                "model_version": "1.0",
            }
        ]
    )
    store.fn(predictions, base_temporaire, "predictions")

    # Meme cle, valeurs differentes.
    predictions.loc[0, "proba_panne"] = 0.90
    predictions.loc[0, "decision"] = "alerte"
    total = store.fn(predictions, base_temporaire, "predictions")

    assert total == 1
    with create_engine(base_temporaire).begin() as cx:
        ligne = cx.execute(
            text("SELECT proba_panne, decision FROM predictions WHERE machine = 'MACH-99'")
        ).one()
    assert ligne.proba_panne == pytest.approx(0.90)
    assert ligne.decision == "alerte"


# [PÉDAGOGIE] BLOC — deux horodatages DIFFERENTS pour la meme machine = deux lignes.
# [PÉDAGOGIE] L'idempotence porte sur la CLE COMPLETE, pas sur la machine seule.
def test_horodatages_differents_creent_deux_lignes(base_temporaire):
    """La cle est (machine, prediction_ts), pas (machine)."""
    base = {
        "machine": "MACH-99",
        "proba_panne": 0.1,
        "decision": "ok",
        "model_version": "1.0",
    }
    store.fn(
        pd.DataFrame([{**base, "prediction_ts": pd.Timestamp("2026-01-01 12:00")}]),
        base_temporaire,
        "predictions",
    )
    total = store.fn(
        pd.DataFrame([{**base, "prediction_ts": pd.Timestamp("2026-01-01 13:00")}]),
        base_temporaire,
        "predictions",
    )

    assert total == 2


# =============================================================================
# PARTIE 4 — LA BASCULE D'HORODATAGE
# =============================================================================


# [PÉDAGOGIE] BLOC — SQLite n'a pas de type DATETIME : il lui faut une CHAINE ISO.
def test_horodatage_sqlite_est_une_chaine_iso():
    """En SQLite, l'horodatage est converti en chaine ISO."""
    valeur = horodatage_pour_sql(
        pd.Timestamp("2025-09-14 23:00:00"), create_engine("sqlite:///:memory:")
    )

    assert isinstance(valeur, str)
    assert valeur == "2025-09-14T23:00:00"


# [PÉDAGOGIE] BLOC — PostgreSQL a un vrai TIMESTAMP : il veut un objet datetime natif.
def test_horodatage_postgresql_est_un_datetime():
    """Hors SQLite, l'horodatage est converti en datetime, pas en Timestamp."""
    valeur = horodatage_pour_sql(
        pd.Timestamp("2025-09-14 23:00:00"),
        create_engine("postgresql+psycopg://u:p@h/d"),
    )

    assert isinstance(valeur, datetime.datetime)
    assert not isinstance(valeur, pd.Timestamp)


# [PÉDAGOGIE] BLOC — la conversion doit accepter les formes rencontrees en pratique.
@pytest.mark.parametrize(
    "entree",
    [
        pd.Timestamp("2025-09-14 23:00:00"),
        "2025-09-14 23:00:00",
        pd.Timestamp("2025-09-14 23:00:00").to_datetime64(),
    ],
)
def test_horodatage_accepte_plusieurs_formes(entree):
    """Timestamp, chaine ou datetime64 donnent le meme resultat."""
    engine = create_engine("sqlite:///:memory:")

    assert horodatage_pour_sql(entree, engine) == "2025-09-14T23:00:00"


# =============================================================================
# PARTIE 5 — LE SCHEMA
# =============================================================================


# [PÉDAGOGIE] BLOC — sans cle primaire, `ON CONFLICT` n'a aucune cible : l'upsert echouerait.
def test_la_table_porte_une_cle_primaire_composite(base_temporaire):
    """La contrainte (machine, prediction_ts) rend l'upsert possible."""
    engine = create_engine(base_temporaire)
    creer_table(engine, "predictions")

    with engine.begin() as cx:
        colonnes = cx.execute(text("PRAGMA table_info(predictions)")).fetchall()

    # PRAGMA table_info : l'index 5 indique l'appartenance a la cle primaire.
    cles = {c[1] for c in colonnes if c[5]}
    assert cles == {"machine", "prediction_ts"}


# [PÉDAGOGIE] BLOC — CREATE TABLE IF NOT EXISTS : appeler deux fois ne doit pas lever.
def test_creation_de_table_est_reentrante(base_temporaire):
    """creer_table est sans effet au second appel."""
    engine = create_engine(base_temporaire)
    creer_table(engine, "predictions")
    creer_table(engine, "predictions")

    assert _compter(base_temporaire) == 0
