# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/check_image.py
# [PÉDAGOGIE] MODULE  — M27 — inspection automatisée d'une image Docker
# [PÉDAGOGIE] RÔLE    — Vérifier des propriétés de l'image construite sans supposer que son tag
# [PÉDAGOGIE]           par défaut correspond au jalon.
# [PÉDAGOGIE] THÉORIE — une image est un artefact ; un conteneur est son instance en exécution
# [PÉDAGOGIE]           • l'inspection complète les tests fonctionnels par des propriétés de
# [PÉDAGOGIE]             construction
# [PÉDAGOGIE]           • le tag doit être passé explicitement lorsqu'il diffère de la valeur de
# [PÉDAGOGIE]             démonstration
# [PÉDAGOGIE] À VOIR  — Passer le tag réellement construit puis lire chaque contrôle comme une
# [PÉDAGOGIE]           assertion de qualité.
# [PÉDAGOGIE] PIÈGE   — Tester le mauvais tag peut valider une ancienne image et donner une preuve
# [PÉDAGOGIE]           trompeuse.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

"""Controle pedagogique de taille et d'utilisateur d'une image M27."""

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import subprocess
import sys

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
IMAGE = sys.argv[1] if len(sys.argv) > 1 else "indusense:0.1.0"
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
MAX_MB = 200


# [PÉDAGOGIE] BLOC `docker` — unité de responsabilité : isoler un comportement nommable, testable
# [PÉDAGOGIE] et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : *args ; preuve : l'appelant doit pouvoir vérifier la sortie ou
# [PÉDAGOGIE] l'effet de bord annoncé.
def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return result.stdout.strip()


# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
size_mb = int(docker("image", "inspect", IMAGE, "--format", "{{.Size}}")) / (1024 * 1024)
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
user = docker("run", "--rm", "--entrypoint", "whoami", IMAGE)

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
problems = []
# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if size_mb > MAX_MB:
    problems.append(f"taille {size_mb:.0f} Mo > {MAX_MB} Mo")
# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if user == "root":
    problems.append("conteneur en root (attendu : appuser)")
# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if problems:
    # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
    # [PÉDAGOGIE] suivantes.
    raise SystemExit("ECHEC : " + " ; ".join(problems))

print(f"OK : {size_mb:.0f} Mo, user={user}")
