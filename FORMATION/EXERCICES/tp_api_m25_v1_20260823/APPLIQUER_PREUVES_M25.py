# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — FORMATION/EXERCICES/tp_api_m25_v1_20260823/APPLIQUER_PREUVES_M25.py
# [PÉDAGOGIE] MODULE  — M25 — contrat d'API, validation et preuve de readiness
# [PÉDAGOGIE] RÔLE    — Exposer le modèle derrière un contrat HTTP explicite, testable et
# [PÉDAGOGIE]           observable.
# [PÉDAGOGIE] THÉORIE — Pydantic valide la forme et les invariants avant l'appel au modèle
# [PÉDAGOGIE]           • liveness et readiness répondent à deux questions opérationnelles
# [PÉDAGOGIE]             différentes
# [PÉDAGOGIE]           • l'injection de dépendances permet d'isoler le chargement du modèle dans
# [PÉDAGOGIE]             les tests
# [PÉDAGOGIE] À VOIR  — Swagger/TestClient doivent rendre visibles les entrées, sorties et codes
# [PÉDAGOGIE]           2xx/4xx/5xx attendus.
# [PÉDAGOGIE] PIÈGE   — Une réponse 200 ne suffit pas si le schéma, la version du modèle ou la
# [PÉDAGOGIE]           normalisation sont faux.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

"""Applique la surcouche M25 de façon idempotente sur Windows, macOS et Linux."""

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
COPIES = (
    Path("tests/test_readiness_probe.py"),
    Path("tests/test_model_card_gate.py"),
    Path("tests/fixtures/model_card_template.md"),
    Path("scripts/validate_model_card.py"),
)
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
REQUIRED = (Path("templates/model_card.md"), Path("README.md"), *COPIES)


# [PÉDAGOGIE] BLOC `sha256` — unité de responsabilité : isoler un comportement nommable, testable
# [PÉDAGOGIE] et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : l'appelant doit pouvoir vérifier la sortie ou
# [PÉDAGOGIE] l'effet de bord annoncé.
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with path.open("rb") as stream:
        # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur
        # [PÉDAGOGIE] un invariant stable.
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return digest.hexdigest()


# [PÉDAGOGIE] BLOC `parse_args` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : vérifier schéma, types,
# [PÉDAGOGIE] ordre et erreurs explicites avant tout calcul aval.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Appliquer la surcouche de preuves M25 sans modifier uv.lock."
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="racine du projet cible (défaut : dossier courant)",
    )
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return parser.parse_args()


# [PÉDAGOGIE] BLOC `main` — orchestration : rendre l'ordre, les dépendances et les points d'échec
# [PÉDAGOGIE] visibles.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : chaque étape doit annoncer
# [PÉDAGOGIE] sa preuve avant que la suivante ne commence.
def main() -> int:
    args = parse_args()
    overlay = Path(__file__).resolve().parent
    project = Path(args.project_path).expanduser().resolve(strict=True)
    lock_path = project / "uv.lock"
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not lock_path.is_file():
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise SystemExit("Le dossier cible n'est pas la racine du projet CISIA : uv.lock absent.")

    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for relative in REQUIRED:
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if not (overlay / relative).is_file():
            # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les
            # [PÉDAGOGIE] étapes suivantes.
            raise SystemExit(f"Surcouche M25 incomplète : {relative.as_posix()} est absent.")

    lock_before = sha256(lock_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_root = Path(tempfile.gettempdir()) / f"CISIA_M25_backup_{stamp}"
    backup_used = False

    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for relative in COPIES:
        source = overlay / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if target.exists():
            # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
            # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
            if sha256(source) == sha256(target):
                print(f"DEJA_IDENTIQUE {relative.as_posix()}")
                continue
            backup_target = backup_root / relative
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_target)
            backup_used = True
            print(f"SAUVEGARDE {relative.as_posix()} -> {backup_target}")

        shutil.copy2(source, target)
        print(f"INSTALLE {relative.as_posix()}")

    card = project / "docs/model_card.md"
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if card.exists():
        print("PRESERVE docs/model_card.md")
    else:
        card.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / "templates/model_card.md", card)
        print("INITIALISE docs/model_card.md")

    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if sha256(lock_path) != lock_before:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise SystemExit("uv.lock a changé pendant l'application de la surcouche M25.")

    print(f"BACKUP_ROOT={backup_root if backup_used else 'NON_NECESSAIRE'}")
    print("M25_OVERLAY=READY")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return 0


# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if __name__ == "__main__":
    # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
    # [PÉDAGOGIE] suivantes.
    raise SystemExit(main())
