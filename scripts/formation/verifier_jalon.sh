#!/usr/bin/env bash
# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/formation/verifier_jalon.sh
# [PÉDAGOGIE] MODULE  — Parcours CISIA — progression Git sûre et reprise multiplateforme
# [PÉDAGOGIE] RÔLE    — Synchroniser ou vérifier un jalon tout en protégeant le travail local et
# [PÉDAGOGIE]           les références distantes.
# [PÉDAGOGIE] THÉORIE — fetch met à jour les références distantes sans intégrer de code
# [PÉDAGOGIE]           • switch choisit explicitement l'état de travail
# [PÉDAGOGIE]           • status et rev-parse rendent branche et commit vérifiables
# [PÉDAGOGIE] À VOIR  — Le terminal doit afficher le dépôt attendu, la branche attendue et un état
# [PÉDAGOGIE]           local compris avant de continuer.
# [PÉDAGOGIE] PIÈGE   — Une commande destructive ou un push forcé n'est jamais une méthode de
# [PÉDAGOGIE]           rattrapage pédagogique.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] FAIL FAST — arrêter sur la première erreur évite de produire une fausse réussite.
set -euo pipefail

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
jalon="${1:-}"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ ! "$jalon" =~ ^(0[1-9]|1[0-2])(-[a-z0-9-]+)?$ ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Usage: bash scripts/formation/verifier_jalon.sh 03" >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 2
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
jalon_number="${jalon:0:2}"

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Ouvrez un terminal dans le depot CISIA." >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 2
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
cd "$root"

# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ ${#jalon} -eq 2 ]]; then
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  marker_matches=$(grep -Ec "^# Jalon actuel : ${jalon_number}(-|$)" FORMATION/JALON_ACTUEL.md || true)
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
else
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  marker_matches=$(grep -Fxc "# Jalon actuel : $jalon" FORMATION/JALON_ACTUEL.md || true)
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ "$marker_matches" -ne 1 ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Le marqueur local ne correspond pas au jalon demande : $jalon" >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 1
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi

# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv sync --frozen --extra dev
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run pytest -q
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run ruff check .

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
echo "Jalon verifie : jalon/$jalon_number"
