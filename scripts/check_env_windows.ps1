# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/check_env_windows.ps1
# [PÉDAGOGIE] MODULE  — M23–M24 — diagnostic multiplateforme et environnement uv
# [PÉDAGOGIE] RÔLE    — Vérifier les prérequis puis reconstruire et contrôler le même projet sur
# [PÉDAGOGIE]           chaque système.
# [PÉDAGOGIE] THÉORIE — uv isole l'environnement Python et synchronise le verrou
# [PÉDAGOGIE]           • --frozen interdit une modification implicite de la résolution validée
# [PÉDAGOGIE]           • chaque commande produit une preuve locale utile au diagnostic
# [PÉDAGOGIE] À VOIR  — Versions, import du paquet, tests, lint et commandes métier doivent tous
# [PÉDAGOGIE]           réussir dans l'environnement uv.
# [PÉDAGOGIE] PIÈGE   — Lancer python ou pytest hors de uv peut utiliser un autre interpréteur que
# [PÉDAGOGIE]           celui du projet.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] FAIL FAST — arrêter sur la première erreur évite de produire une fausse réussite.
$ErrorActionPreference = "Stop"

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "== System tools =="
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (Get-Command python -ErrorAction SilentlyContinue) { python --version }
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (Get-Command py -ErrorAction SilentlyContinue) { py -0p }
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv --version
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
git --version
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (Get-Command wsl -ErrorAction SilentlyContinue) { wsl -l -v }
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (Get-Command docker -ErrorAction SilentlyContinue) {
    # [PÉDAGOGIE] DOCKER — agir sur un artefact ou un service explicitement nommé puis vérifier le
    # [PÉDAGOGIE] résultat.
    docker --version
    # [PÉDAGOGIE] DOCKER — agir sur un artefact ou un service explicitement nommé puis vérifier le
    # [PÉDAGOGIE] résultat.
    docker compose version
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "`n== Project checks =="
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv venv --python 3.13
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv sync --frozen --extra dev
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run python --version
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run python -c "import indusense; print(indusense.__file__)"
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run pytest -q
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run ruff check .
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run black --check .
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run indusense --help
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run indusense check-data
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
uv run indusense build-gold
