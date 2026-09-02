# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/flows/hello.py
# [PÉDAGOGIE] MODULE  — M29 — orchestration avec Prefect
# [PÉDAGOGIE] RÔLE    — Le plus petit flow utile : un @flow qui appelle une @task avec retries.
# [PÉDAGOGIE] THÉORIE — une @task est l'unite de RE-EXECUTION ; un @flow est l'unite d'ORCHESTRATION
# [PÉDAGOGIE]           • `retries=2` = 2 tentatives EN PLUS de la premiere, soit 3 au total
# [PÉDAGOGIE]           • une tache rejouee doit etre IDEMPOTENTE, sinon le retry aggrave la panne
# [PÉDAGOGIE] À VOIR  — Les logs Prefect nomment chaque tentative : « Retry 1/2 will start... ».
# [PÉDAGOGIE] PIÈGE   — Croire que `retries=2` donne 2 executions. Le test en compte 3.
# [PÉDAGOGIE] GARDE   — Aucun serveur Prefect requis : `-m indusense.flows.hello` suffit.
# [PÉDAGOGIE] ============================================================================

"""Flow « hello » — le squelette minimal de l'orchestration.

Lancement :

    uv run python -m indusense.flows.hello
    uv run python -m indusense.flows.hello --echecs 2   # force 2 echecs, voir les retries

Ce que Prefect apporte par rapport a un simple appel de fonction :

  * chaque execution de tache est TRACEE (etat, duree, tentative) ;
  * les retries sont declaratifs, pas codes a la main dans un `while` ;
  * le flow devient deployable et planifiable sans changer son code.
"""

from __future__ import annotations

import argparse
import logging

from prefect import flow, get_run_logger, task
from prefect.exceptions import MissingContextError

# [PÉDAGOGIE] CONSTANTE / CONTRAT — nombre de RE-tentatives apres l'echec initial.
# [PÉDAGOGIE] retries=2 -> 3 executions au maximum (1 initiale + 2 reprises).
NB_RETRIES = 2

# [PÉDAGOGIE] CONSTANTE / CONTRAT — delai entre deux tentatives. Court ici pour la demonstration ;
# [PÉDAGOGIE] en production on utiliserait `exponential_backoff` pour ne pas marteler un service
# [PÉDAGOGIE] deja en difficulte.
DELAI_RETRY_S = 1


# [PÉDAGOGIE] BLOC `_logger` — `get_run_logger()` LEVE hors d'un run Prefect. Sans repli,
# [PÉDAGOGIE] la fonction serait intestable en isolation (`dire_bonjour.fn(...)`).
# [PÉDAGOGIE] Le motif try/except rend le code utilisable DANS et HORS orchestration.
def _logger():
    """Logger Prefect si un run est actif, logger standard sinon."""
    try:
        return get_run_logger()
    except MissingContextError:
        return logging.getLogger("indusense.flows.hello")


# Compteur de tentatives, utilise UNIQUEMENT par la demonstration d'echec.
# En production une tache ne garderait pas d'etat global : elle serait pure.
_tentatives = {"n": 0}


# [PÉDAGOGIE] BLOC `dire_bonjour` — la @task : unite de travail RE-EXECUTABLE.
# [PÉDAGOGIE] CONTRAT — `retries=2` : si elle leve, Prefect la relance jusqu'a 2 fois.
@task(
    name="dire-bonjour",
    retries=NB_RETRIES,
    retry_delay_seconds=DELAI_RETRY_S,
)
def dire_bonjour(nom: str, echecs_simules: int = 0) -> str:
    """Renvoie un message de salutation.

    `echecs_simules` sert uniquement a la demonstration : la tache echoue les
    N premieres fois, puis reussit. C'est ce qui rend les retries OBSERVABLES.

    ATTENTION — cette tache s'appuie sur un compteur global, donc elle n'est
    PAS idempotente. C'est acceptable pour une demonstration, jamais en
    production : une tache rejouee doit produire le meme effet a chaque fois.
    """
    # Logger Prefect quand un run est actif : ses messages sont rattaches au
    # run et visibles dans l'interface, contrairement a print().
    logger = _logger()

    _tentatives["n"] += 1
    logger.info("Tentative n° %s", _tentatives["n"])

    if _tentatives["n"] <= echecs_simules:
        # Lever une exception est le SEUL moyen de declencher un retry.
        # Renvoyer None ou un code d'erreur ne declencherait rien.
        raise RuntimeError(f"Echec simule n° {_tentatives['n']}")

    message = f"Bonjour {nom} !"
    logger.info(message)
    return message


# [PÉDAGOGIE] BLOC `hello` — le @flow : unite d'ORCHESTRATION.
# [PÉDAGOGIE] CONTRAT — il appelle la tache et renvoie son resultat. Aucune logique metier ici :
# [PÉDAGOGIE] un flow coordonne, il ne calcule pas.
@flow(name="hello", log_prints=True)
def hello(nom: str = "InduSense", echecs_simules: int = 0) -> str:
    """Appelle la tache `dire_bonjour` et renvoie son message."""
    logger = _logger()
    logger.info("Demarrage du flow hello (echecs simules : %s)", echecs_simules)

    # Appel DIRECT de la tache : Prefect intercepte et cree un « task run ».
    # C'est ce qui differe d'un appel de fonction ordinaire.
    message = dire_bonjour(nom, echecs_simules=echecs_simules)

    logger.info("Flow termine")
    return message


def reinitialiser_compteur() -> None:
    """Remet le compteur de tentatives a zero (utilise par les tests)."""
    _tentatives["n"] = 0


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description="Flow hello de demonstration.")
    parseur.add_argument("--nom", default="InduSense")
    parseur.add_argument(
        "--echecs",
        type=int,
        default=0,
        help=f"nombre d'echecs a simuler (0 a {NB_RETRIES} pour finir en succes)",
    )
    arguments = parseur.parse_args()

    resultat = hello(nom=arguments.nom, echecs_simules=arguments.echecs)
    print(f"\nResultat du flow : {resultat}")
    print(f"Tentatives consommees : {_tentatives['n']}")
