# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/formation/mettre_a_niveau.ps1
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
    [string]$Jalon,

    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [switch]$Rattrapage
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
)

# [PÉDAGOGIE] FAIL FAST — arrêter sur la première erreur évite de produire une fausse réussite.
$ErrorActionPreference = 'Stop'

# [PÉDAGOGIE] FONCTION — encapsule une étape nommée afin de pouvoir la lire, la tester et la
# [PÉDAGOGIE] réutiliser.
function Invoke-Git {
    # [PÉDAGOGIE] CONTRAT — les paramètres rendent les entrées du script explicites et validables.
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    & git @Arguments
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if ($LASTEXITCODE -ne 0) {
        # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute
        # [PÉDAGOGIE] intégration.
        throw "Git a echoue : git $($Arguments -join ' ')"
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$root = (& git rev-parse --show-toplevel 2>$null)
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0 -or -not $root) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw 'Ouvrez un terminal dans le depot CISIA avant de lancer ce script.'
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Set-Location -LiteralPath $root

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$branch = (& git branch --show-current).Trim()
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (-not $branch) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw 'HEAD detache : revenez sur votre branche personnelle.'
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($branch -eq 'main' -or $branch.StartsWith('jalon/')) {
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    throw "Branche protegee '$branch' : creez d'abord une branche personnelle avec git switch -c prenom-nom."
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$dirty = @(& git status --porcelain)
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($dirty.Count -gt 0) {
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    throw 'Travail non enregistre. Faites git status, git add -A puis git commit avant le jalon.'
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$jalonNumber = $Jalon.Substring(0, 2)
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$remoteBranch = "jalon/$jalonNumber"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Invoke-Git fetch origin "refs/heads/$remoteBranch`:refs/remotes/origin/$remoteBranch"

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$safeBranch = ($branch -replace '[^A-Za-z0-9._-]', '-')
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$backup = "sauvegarde/$safeBranch/$stamp"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Invoke-Git branch $backup HEAD
# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "Sauvegarde creee : $backup"

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
& git pull --no-rebase --no-edit origin $remoteBranch
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0) {
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    $gitDir = (& git rev-parse --git-dir).Trim()
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if (Test-Path -LiteralPath (Join-Path $gitDir 'MERGE_HEAD')) {
        # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute
        # [PÉDAGOGIE] intégration.
        & git merge --abort
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }

    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if (-not $Rattrapage) {
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        throw "Fusion annulee. Relancez avec -Rattrapage pour repartir du jalon officiel ; votre travail reste dans '$branch' et '$backup'."
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }

    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $rescue = "rattrapage/$jalonNumber/$stamp"
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    Invoke-Git switch -c $rescue "origin/$remoteBranch"
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "Mode rattrapage actif : $rescue"
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "Travail precedent preserve : $branch et $backup"
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    exit 0
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "Jalon integre sur $branch : $remoteBranch"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Invoke-Git status --short --branch
