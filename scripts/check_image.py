# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/check_image.py
# [PÉDAGOGIE] MODULE  — M27 — controle qualite reproductible d'une image Docker
# [PÉDAGOGIE] RÔLE    — Verifier taille et privileges d'une image contre un budget MESURE,
# [PÉDAGOGIE]           pas contre un chiffre invente.
# [PÉDAGOGIE] THÉORIE — Un seuil arbitraire ne prouve rien : trop haut il ne detecte aucune
# [PÉDAGOGIE]           derive, trop bas il bloque sans raison
# [PÉDAGOGIE]           • on mesure d'abord, on fige ensuite, on surveille la derive
# [PÉDAGOGIE]           • le budget est VERSIONNE : son evolution se lit dans git log
# [PÉDAGOGIE] À VOIR  — Lancer --calibrate une fois, commiter le budget, puis controler.
# [PÉDAGOGIE] PIÈGE   — Recalibrer a chaque echec vide le controle de son sens. Recalibrer est
# [PÉDAGOGIE]           une DECISION, tracee par un commit.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

"""Controle qualite d'une image Docker : budget de taille calibre et non-root.

Deux modes :

    python scripts/check_image.py --calibrate indusense-api:m27
        Mesure l'image, ecrit docker/image_budget.json. A commiter.

    python scripts/check_image.py indusense-api:m27
        Controle l'image contre le budget enregistre. Sortie != 0 si echec.

La logique de decision (`evaluer`) est une fonction PURE : elle ne parle pas a
Docker. C'est ce qui permet de la tester sans demon Docker, en CI comme en
local.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

# [PÉDAGOGIE] CONSTANTE / CONTRAT — emplacement du budget, versionne avec le code.
BUDGET_PATH = Path(__file__).resolve().parents[1] / "docker" / "image_budget.json"

# [PÉDAGOGIE] CONSTANTE / CONTRAT — marge au-dessus de la mesure. 15 % absorbe une montee de
# [PÉDAGOGIE] version de dependance sans masquer l'ajout d'une couche entiere.
MARGE_PCT_DEFAUT = 15

# [PÉDAGOGIE] CONSTANTE / CONTRAT — UID attendu, aligne sur le Dockerfile (useradd -u 10001).
UID_ATTENDU = 10001

# [PÉDAGOGIE] CONSTANTE / CONTRAT — chemin du modele DANS l'image (aligne sur le Dockerfile :
# [PÉDAGOGIE] COPY artifacts/models ./artifacts/models + WORKDIR /app).
MODEL_PATH_DANS_IMAGE = "/app/artifacts/models/rf.joblib"

# [PÉDAGOGIE] CONSTANTE / CONTRAT — deux variantes de deploiement, deux attentes opposees.
# [PÉDAGOGIE] A : modele EMBARQUE dans l'image (immuable, reproductible, image plus grosse).
# [PÉDAGOGIE] B : modele MONTE au demarrage (image legere, /ready 503 tant qu'il manque).
VARIANTES = ("A", "B")

OCTETS_PAR_MO = 1024 * 1024


# =============================================================================
# COUCHE PURE — testable sans Docker
# =============================================================================


# [PÉDAGOGIE] BLOC `calculer_budget` — fonction PURE : meme mesure, meme budget.
# [PÉDAGOGIE] PIÈGE — `int(180 * 1.15)` donne 206, pas 207 : le flottant vaut 206.99999999999997.
# [PÉDAGOGIE] D'ou l'arithmetique ENTIERE ci-dessous, exacte et reproductible sur toute machine.
def calculer_budget(mesure_mb: float, marge_pct: int = MARGE_PCT_DEFAUT) -> int:
    """Budget = mesure + marge, arrondi au Mo superieur.

    Un budget calcule en flottant varierait selon la plateforme. Ici, deux
    postes qui mesurent la meme taille obtiennent le meme budget, toujours.
    """
    mesure = int(round(mesure_mb))
    # Division entiere avec arrondi au superieur : (a + b - 1) // b.
    return (mesure * (100 + marge_pct) + 99) // 100


# [PÉDAGOGIE] BLOC `evaluer` — fonction PURE : toute la logique de decision, zero I/O.
# [PÉDAGOGIE] CONTRAT — entrees : faits mesures ; sortie : liste des problemes (vide = conforme).
def evaluer(
    taille_octets: int,
    user_declare: str,
    uid_effectif: int | None,
    budget: dict,
    healthcheck: bool,
    modele_present: bool,
) -> list[str]:
    """Confronte les faits mesures au budget. Renvoie la liste des ecarts."""
    problemes: list[str] = []

    taille_mb = taille_octets / OCTETS_PAR_MO
    max_mb = budget["max_mb"]

    if taille_mb > max_mb:
        depassement = taille_mb - budget["mesure_mb"]
        problemes.append(
            f"taille {taille_mb:.0f} Mo > budget {max_mb} Mo "
            f"(+{depassement:.0f} Mo depuis la calibration du {budget['mesure_le']})"
        )

    # Non-root, controle en DEUX temps : ce qui est declare, et ce qui s'execute.
    # Un USER declare peut etre annule par un --user au lancement ; inversement,
    # un Dockerfile sans USER laisse root meme si tout le reste est propre.
    if not user_declare or user_declare in ("root", "0"):
        problemes.append(f"USER declare = {user_declare or '(vide)'} — attendu : appuser")

    if uid_effectif == 0:
        problemes.append("le conteneur s'execute en root (UID 0)")
    elif uid_effectif is not None and uid_effectif != UID_ATTENDU:
        problemes.append(f"UID effectif {uid_effectif} — attendu {UID_ATTENDU}")

    if not healthcheck:
        problemes.append("aucun HEALTHCHECK declare dans l'image")

    # Presence du modele : l'attente DEPEND de la variante, elle n'est pas
    # absolue. Une image sans modele n'est pas cassee — elle est de variante B,
    # et c'est /ready qui repondra 503 tant que rien n'est monte.
    variante = budget.get("variante", "A")
    if variante == "A" and not modele_present:
        problemes.append(
            f"modele absent de l'image : {MODEL_PATH_DANS_IMAGE} "
            "(variante A : le modele doit etre embarque)"
        )
    if variante == "B" and modele_present:
        problemes.append(
            "modele embarque alors que la variante B le monte au demarrage "
            "(image inutilement grosse et figee)"
        )

    return problemes


# [PÉDAGOGIE] BLOC `formater_rapport` — fonction PURE : la mise en forme est separee du verdict.
def formater_rapport(taille_octets: int, budget: dict, problemes: list[str]) -> str:
    """Rapport lisible, quel que soit le verdict."""
    taille_mb = taille_octets / OCTETS_PAR_MO
    marge = budget["max_mb"] - taille_mb
    lignes = [
        f"Image      : {budget['image']}",
        f"Variante   : {budget.get('variante', 'A')}",
        f"Taille     : {taille_mb:.0f} Mo",
        f"Budget     : {budget['max_mb']} Mo (calibre le {budget['mesure_le']})",
        f"Marge      : {marge:+.0f} Mo",
    ]
    if problemes:
        lignes.append("")
        lignes.extend(f"  ECHEC — {p}" for p in problemes)
    return "\n".join(lignes)


# =============================================================================
# COUCHE I/O — parle a Docker
# =============================================================================


def docker(*args: str) -> str:
    """Appelle docker et renvoie sa sortie standard nettoyee."""
    resultat = subprocess.run(["docker", *args], capture_output=True, text=True, check=True)
    return resultat.stdout.strip()


def mesurer(image: str) -> tuple[int, str, int | None, bool, bool]:
    """Collecte les faits observables sur l'image. Aucune decision ici."""
    taille = int(docker("image", "inspect", image, "--format", "{{.Size}}"))
    user = docker("image", "inspect", image, "--format", "{{.Config.User}}")
    sonde = docker("image", "inspect", image, "--format", "{{if .Config.Healthcheck}}1{{end}}")

    # L'UID effectif demande de LANCER le conteneur : c'est le seul moyen de
    # savoir ce qui s'execute vraiment. On tolere l'echec (image sans shell).
    try:
        uid = int(docker("run", "--rm", "--entrypoint", "id", image, "-u"))
    except (subprocess.CalledProcessError, ValueError):
        uid = None

    # Presence du modele : `test -f` renvoie 0 s'il existe, 1 sinon. C'est le
    # CODE RETOUR qui porte l'information, pas la sortie standard (vide).
    # On inspecte le contenu de l'image sans demarrer l'application.
    try:
        docker("run", "--rm", "--entrypoint", "test", image, "-f", MODEL_PATH_DANS_IMAGE)
        modele_present = True
    except subprocess.CalledProcessError:
        modele_present = False

    return taille, user, uid, bool(sonde), modele_present


def charger_budget(chemin: Path) -> dict:
    """Lit le budget versionne, ou explique comment le creer."""
    if not chemin.exists():
        raise SystemExit(
            f"Budget absent : {chemin}\n"
            "Lancer d'abord : python scripts/check_image.py --calibrate <image>"
        )
    return json.loads(chemin.read_text(encoding="utf-8"))


def ecrire_budget(
    chemin: Path, image: str, taille_octets: int, marge_pct: int, variante: str = "A"
) -> dict:
    """Mesure -> budget -> fichier JSON versionne."""
    mesure_mb = round(taille_octets / OCTETS_PAR_MO)
    budget = {
        "image": image,
        "mesure_mb": mesure_mb,
        "marge_pct": marge_pct,
        "max_mb": calculer_budget(mesure_mb, marge_pct),
        "mesure_le": date.today().isoformat(),
        "variante": variante,
    }
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")
    return budget


# =============================================================================
# POINT D'ENTREE
# =============================================================================


def main() -> int:
    parseur = argparse.ArgumentParser(description="Controle qualite d'une image Docker.")
    parseur.add_argument("image", help="tag de l'image a controler, ex. indusense-api:m27")
    parseur.add_argument(
        "--calibrate",
        action="store_true",
        help="mesurer l'image et (re)ecrire le budget au lieu de controler",
    )
    parseur.add_argument("--marge", type=int, default=MARGE_PCT_DEFAUT, help="marge en pourcent")
    parseur.add_argument("--budget", type=Path, default=BUDGET_PATH)
    parseur.add_argument(
        "--variante",
        choices=VARIANTES,
        default="A",
        help="A = modele embarque dans l'image ; B = modele monte au demarrage",
    )
    arguments = parseur.parse_args()

    if arguments.calibrate:
        taille = int(docker("image", "inspect", arguments.image, "--format", "{{.Size}}"))
        budget = ecrire_budget(
            arguments.budget, arguments.image, taille, arguments.marge, arguments.variante
        )
        print(
            f"Budget calibre : {budget['mesure_mb']} Mo mesures "
            f"+ {budget['marge_pct']} % = {budget['max_mb']} Mo\n"
            f"Ecrit dans {arguments.budget}\n"
            f"A COMMITER : le budget fait partie du contrat de l'image."
        )
        return 0

    budget = charger_budget(arguments.budget)
    if budget["image"] != arguments.image:
        print(
            f"Attention : budget calibre pour {budget['image']}, "
            f"controle demande sur {arguments.image}.",
            file=sys.stderr,
        )

    taille, user, uid, sonde, modele = mesurer(arguments.image)
    problemes = evaluer(taille, user, uid, budget, sonde, modele)

    print(formater_rapport(taille, budget, problemes))
    return 1 if problemes else 0


if __name__ == "__main__":
    raise SystemExit(main())
