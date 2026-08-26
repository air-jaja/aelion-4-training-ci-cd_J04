#!/usr/bin/env bash
# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/formation/mettre_a_niveau.sh
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
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
rattrapage="${2:-}"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ ! "$jalon" =~ ^(0[1-9]|1[0-2])(-[a-z0-9-]+)?$ ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Usage: bash scripts/formation/mettre_a_niveau.sh 03 [--rattrapage]" >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 2
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ -n "$rattrapage" && "$rattrapage" != "--rattrapage" ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Option inconnue : $rattrapage" >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 2
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi

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

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
branch="$(git branch --show-current)"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ -z "$branch" || "$branch" == "main" || "$branch" == jalon/* ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Travaillez sur une branche personnelle, pas sur '$branch'." >&2
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 2
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if [[ -n "$(git status --porcelain)" ]]; then
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Commitez votre travail avant le nouveau jalon." >&2
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
remote_branch="jalon/$jalon_number"
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
git fetch origin "refs/heads/$remote_branch:refs/remotes/origin/$remote_branch"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
stamp="$(date +%Y%m%d-%H%M%S)"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
safe_branch="${branch//\//-}"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
backup="sauvegarde/$safe_branch/$stamp"
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
git branch "$backup" HEAD
# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
echo "Sauvegarde creee : $backup"

# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ! git pull --no-rebase --no-edit origin "$remote_branch"; then
  # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
  # [PÉDAGOGIE] compréhensible.
  if git rev-parse -q --verify MERGE_HEAD >/dev/null; then
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    git merge --abort
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  fi
  # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
  # [PÉDAGOGIE] compréhensible.
  if [[ "$rattrapage" != "--rattrapage" ]]; then
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    echo "Fusion annulee. Travail preserve dans '$branch' et '$backup'." >&2
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    echo "Relancez avec --rattrapage pour repartir du jalon officiel." >&2
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    exit 1
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  fi

  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  rescue="rattrapage/$jalon_number/$stamp"
  # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
  git switch -c "$rescue" "origin/$remote_branch"
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Mode rattrapage actif : $rescue"
  # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
  echo "Travail precedent preserve : $branch et $backup"
  # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
  # [PÉDAGOGIE] autorise la suite.
  exit 0
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
fi

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
echo "Jalon integre sur $branch : $remote_branch"
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
git status --short --branch
