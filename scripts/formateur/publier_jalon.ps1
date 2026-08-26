# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — scripts/formateur/publier_jalon.ps1
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
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
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
if ($LASTEXITCODE -ne 0 -or -not $root) { throw 'Depot Git introuvable.' }
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Set-Location -LiteralPath $root

# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (@(& git status --porcelain).Count -gt 0) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw 'Le depot de preparation doit etre propre avant toute publication.'
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$jalonNumber = $Jalon.Substring(0, 2)
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$jalonMarker = if ($Jalon.Length -gt 2) {
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $Jalon
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
} else {
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $indexRow = Import-Csv -LiteralPath 'FORMATION/JALON_INDEX.tsv' -Delimiter "`t" |
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        Where-Object { $_.ordre -eq $jalonNumber }
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if (-not $indexRow) { throw "Jalon absent de FORMATION/JALON_INDEX.tsv : $jalonNumber" }
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $indexRow.jalon_marqueur
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$source = "preparation/$jalonMarker"
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$target = "jalon/$jalonNumber"
# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
& git show-ref --verify --quiet "refs/heads/$source"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($LASTEXITCODE -ne 0) { throw "Branche locale absente : $source" }

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$origin = (& git remote get-url origin).Trim()
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($origin -notmatch 'github\.com[/:]thomasfesq/CISIA_24082026_Parcours(?:\.git)?$') {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw "Remote refuse : $origin"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
$remoteOid = (& git ls-remote --heads origin "refs/heads/$target").Trim()
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($remoteOid) {
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $published = ($remoteOid -split '\s+')[0]
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    $local = (& git rev-parse "refs/heads/$source").Trim()
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if ($published -eq $local) {
        # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de
        # [PÉDAGOGIE] secret.
        Write-Host "Deja publie a l'identique : $target"
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        exit 0
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw "Le jalon distant existe avec un autre commit. Aucune reecriture automatique."
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($PSCmdlet.ShouldProcess("origin/$target", "publier uniquement $source")) {
    # [PÉDAGOGIE] GIT — rendre branche, commit et état local vérifiables avant toute intégration.
    & git push origin "refs/heads/$source`:refs/heads/$target"
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if ($LASTEXITCODE -ne 0) { throw 'Publication Git echouee.' }
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "Publie : $target"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
