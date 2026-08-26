# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/formation/verifier_jalon.ps1
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

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
[CmdletBinding()]
# [PÉDAGOGIE] CONTRAT — les paramètres rendent les entrées du script explicites et validables.
param(
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [Parameter(Mandatory = $true)]
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [ValidatePattern('^(0[1-9]|1[0-2])(?:-[a-z0-9-]+)?$')]
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [string]$Jalon
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
)

# [PÉDAGOGIE] FAIL FAST — arrêter sur la première erreur évite de produire une fausse réussite.
$ErrorActionPreference = 'Stop'
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$root = (& git rev-parse --show-toplevel 2>$null)
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0 -or -not $root) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw 'Ouvrez un terminal dans le depot CISIA.'
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Set-Location -LiteralPath $root

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$jalonNumber = $Jalon.Substring(0, 2)
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$marker = Get-Content -LiteralPath 'FORMATION/JALON_ACTUEL.md' -Raw
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$markerPattern = if ($Jalon.Length -eq 2) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    "(?m)^# Jalon actuel : $([regex]::Escape($jalonNumber))(?:-|$)"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
} else {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    "(?m)^# Jalon actuel : $([regex]::Escape($Jalon))\r?$"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($marker -notmatch $markerPattern) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw "Le marqueur local ne correspond pas au jalon demande : $Jalon"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
& uv sync --frozen --extra dev
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0) { throw 'uv sync a echoue.' }
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
& uv run pytest -q
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0) { throw 'pytest a echoue.' }
# [PÉDAGOGIE] UV — exécuter dans l'environnement verrouillé du projet plutôt que dans Python
# [PÉDAGOGIE] global.
& uv run ruff check .
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0) { throw 'ruff a echoue.' }

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "Jalon verifie : jalon/$jalonNumber"
