# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/flows/pipeline.py
# [PÉDAGOGIE] MODULE  — M29 — decoupage d'un pipeline en tasks orchestrees
# [PÉDAGOGIE] RÔLE    — Esquisse : les QUATRE signatures, sans corps. A completer en seance.
# [PÉDAGOGIE] THÉORIE — une @task est l'unite de RE-EXECUTION : son decoupage decide de ce
# [PÉDAGOGIE]           qu'on peut rejouer sans tout refaire
# [PÉDAGOGIE]           • trop grosse -> un echec tardif oblige a tout recommencer
# [PÉDAGOGIE]           • trop fine -> le graphe devient illisible et le surcout domine
# [PÉDAGOGIE] À VOIR  — La frontiere PURE / EFFET DE BORD : seule `store` ecrit sur disque.
# [PÉDAGOGIE] PIÈGE   — Mettre du metier ici. Le metier vit dans src/indusense/ ; ce fichier
# [PÉDAGOGIE]           ORCHESTRE, il ne calcule pas.
# [PÉDAGOGIE] GARDE   — Les corps levent NotImplementedError : c'est l'exercice du M29.
# [PÉDAGOGIE] ============================================================================

"""Pipeline InduSense — esquisse des quatre tasks.

    ingest -> feature -> predict -> store

Chaque signature fixe un CONTRAT : ce qui entre, ce qui sort, ce qui peut
echouer. Le corps vient ensuite. Ecrire les signatures d'abord evite le piege
classique — coder puis decouvrir que la task 3 a besoin d'une donnee que la
task 1 n'a pas transmise.

Conception detaillee, diagramme et table d'erreurs : docs/flow_design.md

Lancement (une fois les corps ecrits) :

    uv run python -m indusense.flows.pipeline
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from prefect import flow, task

# [PÉDAGOGIE] CONSTANTE / CONTRAT — politique de reprise par nature d'echec.
# [PÉDAGOGIE] On ne retente QUE ce qui est transitoire. Retenter une erreur de schema
# [PÉDAGOGIE] ne fait que retarder le diagnostic de trois tentatives.
RETRIES_IO = 2  # lecture disque, ecriture : pannes transitoires plausibles
RETRIES_CALCUL = 0  # transformation pure : un echec est deterministe, inutile de rejouer


# =============================================================================
# TASK 1/4 — INGEST : lire les sources brutes et les harmoniser
# =============================================================================


# [PÉDAGOGIE] BLOC `ingest` — FRONTIERE D'ENTREE : le seul endroit qui touche aux fichiers
# [PÉDAGOGIE] sources. En isolant la lecture, on rend le reste du pipeline testable sans disque.
# [PÉDAGOGIE] CONTRAT — entree : un dossier ; sortie : un DataFrame harmonise, une ligne par
# [PÉDAGOGIE] (machine, timestamp), avec la cible `panne`.
@task(name="ingest", retries=RETRIES_IO, retry_delay_seconds=5)
def ingest(data_dir: Path, window_hours: int = 24) -> pd.DataFrame:
    """Charge les trois sources et construit le dataset joint.

    Entree
    ------
    data_dir : dossier contenant capteurs_temperature.csv (`;`),
               capteurs_pression.tsv (`\\t`) et releves_incidents.csv (`,`).
    window_hours : fenetre d'etiquetage de la cible `panne`.

    Sortie
    ------
    DataFrame avec au minimum : machine, timestamp, temperature,
    pressure_bar, panne. Trie par (machine, timestamp).

    Erreurs
    -------
    FileNotFoundError : une source manque -> transitoire si montage reseau,
                        d'ou `retries=2`.
    ValueError        : machine_id sans numero (normalize_machine_id).
                        NON transitoire : rejouer ne changera rien.

    A COMPLETER en M29 — reutiliser load_temperature, load_pressure,
    load_incidents et build_dataset depuis indusense.data.loaders.
    """
    raise NotImplementedError("M29 : implementer ingest")


# =============================================================================
# TASK 2/4 — FEATURE : deriver les variables temporelles
# =============================================================================


# [PÉDAGOGIE] BLOC `feature` — FONCTION PURE : memes entrees, memes sorties, aucun effet de bord.
# [PÉDAGOGIE] `retries=0` assume : un echec ici est deterministe, le rejouer ne fait que masquer.
# [PÉDAGOGIE] CONTRAT — c'est ici que se joue l'anti-fuite : shift(1) AVANT rolling.
@task(name="feature", retries=RETRIES_CALCUL)
def feature(dataset: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les variables retardees et glissantes.

    Entree
    ------
    dataset : sortie de `ingest`.

    Sortie
    ------
    Le meme DataFrame enrichi des colonnes `<col>_lag<n>` et
    `<col>_roll<n>_mean`. Les premieres lignes de chaque machine portent
    des NaN : c'est ATTENDU, pas un defaut.

    Erreurs
    -------
    ValueError : colonne attendue absente -> contrat rompu en amont.
                 Aucune reprise : le probleme vient de `ingest`.

    A COMPLETER en M29 — appeler add_temporal_features depuis
    indusense.features.temporal.
    """
    raise NotImplementedError("M29 : implementer feature")


# =============================================================================
# TASK 3/4 — PREDICT : appliquer le modele
# =============================================================================


# [PÉDAGOGIE] BLOC `predict` — la lecture du modele est une I/O, d'où `retries=2`.
# [PÉDAGOGIE] CONTRAT — sortie MINIMALE : on ne renvoie pas les 40 colonnes de features,
# [PÉDAGOGIE] seulement ce qu'un consommateur exploite. Une task qui rend tout force la suivante
# [PÉDAGOGIE] a trier, et le contrat devient flou.
@task(name="predict", retries=RETRIES_IO, retry_delay_seconds=5)
def predict(features: pd.DataFrame, model_dir: Path, seuil: float) -> pd.DataFrame:
    """Calcule la probabilite de panne et la decision associee.

    Entree
    ------
    features : sortie de `feature`.
    model_dir : dossier contenant rf.joblib et model_metadata.json.
    seuil : au-dela, la decision passe a "alerte".

    Sortie
    ------
    DataFrame a quatre colonnes : machine, timestamp, proba_panne, decision.
    Une ligne par ligne d'entree exploitable.

    Erreurs
    -------
    FileNotFoundError    : modele absent -> transitoire au demarrage.
    ModelIntegrityError  : empreinte invalide -> NE PAS rejouer, l'artefact
                           est compromis (voir docs/threat_model.md).
    ValueError           : colonnes de features absentes du modele.

    A COMPLETER en M29 — load_model, select_features, predict_proba depuis
    indusense.models.tabular.
    """
    raise NotImplementedError("M29 : implementer predict")


# =============================================================================
# TASK 4/4 — STORE : ecrire les resultats, SANS DUPLIQUER
# =============================================================================


# [PÉDAGOGIE] BLOC `store` — SEUL effet de bord du pipeline, et le seul point ou l'idempotence
# [PÉDAGOGIE] se joue. Une task rejouee doit produire le MEME etat final, pas des lignes en double.
# [PÉDAGOGIE] CONTRAT — la cle d'idempotence est `run_date` : ecrire au meme emplacement ecrase
# [PÉDAGOGIE] au lieu d'ajouter. C'est la preuve exigee par le jalon.
@task(name="store", retries=RETRIES_IO, retry_delay_seconds=5)
def store(predictions: pd.DataFrame, output_dir: Path, run_date: datetime) -> Path:
    """Ecrit les predictions de facon idempotente.

    Entree
    ------
    predictions : sortie de `predict`.
    output_dir : dossier de destination.
    run_date : horodatage du run, sert de CLE D'IDEMPOTENCE.

    Sortie
    ------
    Chemin du fichier ecrit. On renvoie le chemin, pas le contenu : la task
    suivante (ou l'operateur) doit pouvoir retrouver le resultat.

    Erreurs
    -------
    PermissionError : disque en lecture seule -> transitoire, on retente.
    OSError         : disque plein -> retenter est inutile mais sans danger.

    IDEMPOTENCE — deux executions sur la meme `run_date` doivent produire UN
    seul fichier, au meme chemin, avec le meme nombre de lignes. Un `append`
    romprait le contrat : c'est le piege que la demo du jalon met en evidence.

    A COMPLETER en M29 — construire un nom deterministe a partir de run_date,
    puis ecrire avec to_csv (mode "w", jamais "a").
    """
    raise NotImplementedError("M29 : implementer store")


# =============================================================================
# LE FLOW — il ORCHESTRE, il ne calcule pas
# =============================================================================


# [PÉDAGOGIE] BLOC `pipeline` — le flow ne contient AUCUNE logique metier : il enchaine.
# [PÉDAGOGIE] Toute condition ou transformation qui apparaitrait ici devrait etre une task.
@flow(name="indusense-pipeline")
def pipeline(
    data_dir: Path | None = None,
    model_dir: Path | None = None,
    output_dir: Path | None = None,
    seuil: float = 0.5,
    run_date: datetime | None = None,
) -> Path:
    """Enchaine ingest -> feature -> predict -> store.

    Renvoie le chemin du fichier de predictions.

    A COMPLETER en M29 — resoudre les valeurs par defaut depuis
    indusense.config.settings, puis appeler les quatre tasks dans l'ordre.
    """
    raise NotImplementedError("M29 : implementer le flow")


if __name__ == "__main__":
    print(pipeline())
