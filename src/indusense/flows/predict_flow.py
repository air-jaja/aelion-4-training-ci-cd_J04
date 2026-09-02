# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/flows/predict_flow.py
# [PÉDAGOGIE] MODULE  — M29/M30 — pipeline orchestre et idempotent
# [PÉDAGOGIE] RÔLE    — ingest -> feature -> predict -> store, avec un UPSERT qui rend le
# [PÉDAGOGIE]           second passage sans effet sur le nombre de lignes.
# [PÉDAGOGIE] THÉORIE — l'idempotence n'est pas une propriete du code, mais de la CLE choisie
# [PÉDAGOGIE]           • ici (machine, prediction_ts) : deux runs sur les memes donnees ecrasent
# [PÉDAGOGIE]           • un INSERT simple aurait double les lignes a chaque passage
# [PÉDAGOGIE] À VOIR  — La bascule de conversion d'horodatage selon le dialecte SQL.
# [PÉDAGOGIE] PIÈGE   — SQLite n'a pas de type DATETIME natif : il stocke une chaine.
# [PÉDAGOGIE]           PostgreSQL veut un objet datetime. Le meme code doit servir aux deux.
# [PÉDAGOGIE] GARDE   — Le metier reste dans indusense.data / .features / .models.
# [PÉDAGOGIE] ============================================================================

"""Pipeline de prediction InduSense, orchestre par Prefect.

    ingest -> feature -> predict -> store (upsert)

Lancement local (SQLite) :

    uv run python -m indusense.flows.predict_flow

IDEMPOTENCE — la cle est `(machine, prediction_ts)`. Deux executions sur les
memes donnees produisent le MEME nombre de lignes : la seconde met a jour au
lieu d'inserer. C'est la preuve exigee par le jalon.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from prefect import flow, get_run_logger, task
from prefect.exceptions import MissingContextError
from sqlalchemy import Engine, create_engine, text

from indusense.config import settings
from indusense.data.loaders import (
    build_dataset,
    load_incidents,
    load_pressure,
    load_temperature,
)
from indusense.features.temporal import add_temporal_features
from indusense.models.tabular import load_model, predict_proba, select_features

# [PÉDAGOGIE] CONSTANTE / CONTRAT — politique de reprise par NATURE d'echec.
# [PÉDAGOGIE] On ne retente que le transitoire : retenter un calcul pur ne fait que retarder
# [PÉDAGOGIE] le diagnostic de trois tentatives.
RETRIES_IO = 2
RETRIES_CALCUL = 0

# [PÉDAGOGIE] CONSTANTE / CONTRAT — colonnes de la table de sortie, nommees une seule fois
# [PÉDAGOGIE] pour qu'elles ne derivent pas entre le CREATE TABLE et l'INSERT.
COLONNES_SORTIE = ("machine", "prediction_ts", "proba_panne", "decision", "model_version")


def _logger():
    """Logger Prefect si un run est actif, logger standard sinon."""
    try:
        return get_run_logger()
    except MissingContextError:
        return logging.getLogger("indusense.flows.predict_flow")


# =============================================================================
# TASK 1/4 — INGEST
# =============================================================================


# [PÉDAGOGIE] BLOC `ingest` — FRONTIERE D'ENTREE : seul point qui touche aux fichiers sources.
@task(name="ingest", retries=RETRIES_IO, retry_delay_seconds=5)
def ingest(data_dir: Path, window_hours: int) -> pd.DataFrame:
    """Charge les trois sources et construit le dataset joint."""
    logger = _logger()

    dataset = build_dataset(
        load_temperature(data_dir / "capteurs_temperature.csv"),
        load_pressure(data_dir / "capteurs_pression.tsv"),
        load_incidents(data_dir / "releves_incidents.csv"),
        window_hours=window_hours,
    )

    # Le taux de cible est journalise a CHAQUE run : c'est le premier indicateur
    # qu'on regarde si les predictions deviennent absurdes. Un jeu de donnees
    # remplace ou tronque se voit immediatement ici.
    taux = 100 * dataset[settings.target_col].mean()
    logger.info(
        "Ingest : %s lignes, %s machines, taux %s = %.2f %%",
        len(dataset),
        dataset["machine"].nunique(),
        settings.target_col,
        taux,
    )
    return dataset


def taux_cible(dataset: pd.DataFrame) -> float:
    """Taux de la colonne cible, en pourcentage. Utilise par les tests."""
    return 100 * float(dataset[settings.target_col].mean())


# =============================================================================
# TASK 2/4 — FEATURE
# =============================================================================


# [PÉDAGOGIE] BLOC `feature` — FONCTION PURE, donc `retries=0` : un echec est deterministe,
# [PÉDAGOGIE] le rejouer donnerait le meme echec en retardant le diagnostic.
@task(name="feature", retries=RETRIES_CALCUL)
def feature(dataset: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les variables retardees et glissantes (shift(1) AVANT rolling)."""
    logger = _logger()
    enrichi = add_temporal_features(dataset)
    logger.info("Feature : %s colonnes", len(enrichi.columns))
    return enrichi


# =============================================================================
# TASK 3/4 — PREDICT
# =============================================================================


def _version_modele(model_dir: Path) -> str:
    """Version du modele, lue dans les metadonnees. '0' si absente."""
    chemin = model_dir / "model_metadata.json"
    if not chemin.exists():
        return "0"
    # utf-8-sig : tolere un BOM, que PowerShell ajoute volontiers sous Windows.
    meta = json.loads(chemin.read_text(encoding="utf-8-sig"))
    return str(meta.get("package_version", "0"))


# [PÉDAGOGIE] BLOC `predict` — la lecture du modele est une I/O, d'ou `retries=2`.
# [PÉDAGOGIE] CONTRAT — UNE ligne par machine : son releve le PLUS RECENT. On ne renvoie pas
# [PÉDAGOGIE] l'historique complet : une prediction porte sur l'etat courant.
@task(name="predict", retries=RETRIES_IO, retry_delay_seconds=5)
def predict(features: pd.DataFrame, model_dir: Path, seuil: float) -> pd.DataFrame:
    """Score le dernier releve de chaque machine."""
    logger = _logger()

    # Le tri est EXPLICITE : `groupby().tail(1)` sans tri prealable dependrait
    # de l'ordre d'arrivee des lignes, donc du systeme de fichiers.
    derniers = (
        features.sort_values(["machine", "timestamp"]).groupby("machine", as_index=False).tail(1)
    )

    modele = load_model(model_dir / "rf.joblib")
    colonnes = select_features(derniers, target_col=settings.target_col)
    probabilites = predict_proba(modele, colonnes)

    predictions = pd.DataFrame(
        {
            "machine": derniers["machine"].to_numpy(),
            "prediction_ts": derniers["timestamp"].to_numpy(),
            "proba_panne": probabilites,
        }
    )
    predictions["decision"] = predictions["proba_panne"].map(
        lambda proba: "alerte" if proba >= seuil else "ok"
    )
    predictions["model_version"] = _version_modele(model_dir)

    logger.info("Predict : %s machines scorees (seuil %.2f)", len(predictions), seuil)
    return predictions[list(COLONNES_SORTIE)]


# =============================================================================
# TASK 4/4 — STORE : le seul effet de bord, le seul point d'idempotence
# =============================================================================


# [PÉDAGOGIE] BLOC `horodatage_pour_sql` — LE point technique du jalon.
# [PÉDAGOGIE] SQLite n'a pas de type DATETIME : il stocke une CHAINE, et attend donc une chaine
# [PÉDAGOGIE] ISO. PostgreSQL a un vrai TIMESTAMP et veut un objet datetime.
# [PÉDAGOGIE] PIÈGE — passer un Timestamp pandas a SQLite produirait une representation dont
# [PÉDAGOGIE] la forme peut varier ; la cle de l'upsert ne serait plus reconnue au 2e passage,
# [PÉDAGOGIE] et les lignes se dupliqueraient SANS erreur visible.
def horodatage_pour_sql(valeur, engine: Engine):
    """Convertit un horodatage selon le dialecte SQL de la connexion."""
    if engine.dialect.name == "sqlite":
        return pd.Timestamp(valeur).isoformat()
    return pd.Timestamp(valeur).to_pydatetime()


def creer_table(engine: Engine, table: str) -> None:
    """Cree la table de predictions si elle n'existe pas.

    La CLE PRIMAIRE sur (machine, prediction_ts) est ce qui rend l'upsert
    possible. Sans elle, `ON CONFLICT` n'aurait aucune cible et chaque run
    ajouterait des lignes.
    """
    type_ts = "TEXT" if engine.dialect.name == "sqlite" else "TIMESTAMP"

    with engine.begin() as cx:
        cx.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                machine       VARCHAR(32) NOT NULL,
                prediction_ts {type_ts}   NOT NULL,
                proba_panne   DOUBLE PRECISION NOT NULL,
                decision      VARCHAR(16) NOT NULL,
                model_version VARCHAR(32) NOT NULL,
                CONSTRAINT {table}_pk PRIMARY KEY (machine, prediction_ts)
            )
            """)
        )


# [PÉDAGOGIE] BLOC `store` — SEUL effet de bord du pipeline.
# [PÉDAGOGIE] CONTRAT — UPSERT sur (machine, prediction_ts) : le second run MET A JOUR.
# [PÉDAGOGIE] La preuve du jalon compte les lignes avant et apres : elles doivent etre egales.
@task(name="store", retries=RETRIES_IO, retry_delay_seconds=5)
def store(predictions: pd.DataFrame, db_url: str, table: str) -> int:
    """Ecrit les predictions en upsert. Renvoie le nombre total de lignes en base."""
    logger = _logger()
    engine = create_engine(db_url)
    creer_table(engine, table)

    # `ON CONFLICT ... DO UPDATE` a la MEME syntaxe en SQLite et PostgreSQL :
    # une seule requete sert les deux dialectes.
    requete = text(f"""
        INSERT INTO {table}
            (machine, prediction_ts, proba_panne, decision, model_version)
        VALUES
            (:machine, :prediction_ts, :proba_panne, :decision, :model_version)
        ON CONFLICT (machine, prediction_ts) DO UPDATE SET
            proba_panne   = EXCLUDED.proba_panne,
            decision      = EXCLUDED.decision,
            model_version = EXCLUDED.model_version
    """)

    with engine.begin() as cx:
        for ligne in predictions.itertuples(index=False):
            cx.execute(
                requete,
                {
                    "machine": ligne.machine,
                    # Conversion AVANT execute : le dialecte decide de la forme.
                    "prediction_ts": horodatage_pour_sql(ligne.prediction_ts, engine),
                    "proba_panne": float(ligne.proba_panne),
                    "decision": ligne.decision,
                    "model_version": ligne.model_version,
                },
            )

    with engine.begin() as cx:
        total = cx.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()

    logger.info("Store : %s lignes ecrites, %s en base", len(predictions), total)
    return int(total)


# =============================================================================
# LE FLOW — il orchestre, il ne calcule pas
# =============================================================================


@flow(name="indusense-predict")
def predict_flow(
    data_dir: Path | None = None,
    model_dir: Path | None = None,
    db_url: str | None = None,
    table: str | None = None,
    seuil: float = 0.5,
    window_hours: int | None = None,
) -> int:
    """Enchaine ingest -> feature -> predict -> store. Renvoie le total en base."""
    logger = _logger()

    # Valeurs par defaut resolues depuis la CONFIGURATION, pas codees ici : le
    # flow se comporte pareil en local et dans Compose, seul l'environnement
    # change (INDUSENSE_DATA_DIR, INDUSENSE_DB_URL).
    data_dir = Path(data_dir or settings.data_dir)
    model_dir = Path(model_dir or settings.model_dir)
    db_url = db_url or settings.db_url
    table = table or settings.predictions_table
    window_hours = window_hours or settings.incident_window_hours

    # On ne journalise JAMAIS l'URL complete : elle contient le mot de passe.
    logger.info("Flow demarre : data=%s db=%s", data_dir, db_url.rsplit("@", 1)[-1])

    dataset = ingest(data_dir, window_hours)
    enrichi = feature(dataset)
    predictions = predict(enrichi, model_dir, seuil)
    total = store(predictions, db_url, table)

    logger.info("Flow termine : %s lignes en base", total)
    return total


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description="Pipeline de prediction InduSense.")
    parseur.add_argument("--data-dir", type=Path, default=None)
    parseur.add_argument("--seuil", type=float, default=0.5)
    arguments = parseur.parse_args()

    total = predict_flow(data_dir=arguments.data_dir, seuil=arguments.seuil)
    print(f"\nLignes en base : {total}")
