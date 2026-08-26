# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — FORMATION/EXERCICES/tp_api_m25_v1_20260823/APPLIQUER_PREUVES_M25.ps1
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

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
[CmdletBinding()]
# [PÉDAGOGIE] CONTRAT — les paramètres rendent les entrées du script explicites et validables.
param(
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [Parameter()]
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    [string]$ProjectPath = "."
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
)

# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
Set-StrictMode -Version Latest
# [PÉDAGOGIE] FAIL FAST — arrêter sur la première erreur évite de produire une fausse réussite.
$ErrorActionPreference = "Stop"

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$overlay = $PSScriptRoot
# [PÉDAGOGIE] CHEMIN — résoudre la racine évite que le résultat dépende du dossier depuis lequel
# [PÉDAGOGIE] le script est lancé.
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$lockPath = Join-Path $project "uv.lock"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (-not (Test-Path -LiteralPath $lockPath)) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw "Le dossier cible n'est pas la racine de CISIA_29062026 : uv.lock absent."
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$copies = @(
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    @{ Source = "tests\test_readiness_probe.py"; Target = "tests\test_readiness_probe.py" },
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    @{ Source = "tests\test_model_card_gate.py"; Target = "tests\test_model_card_gate.py" },
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    @{ Source = "tests\fixtures\model_card_template.md"; Target = "tests\fixtures\model_card_template.md" },
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    @{ Source = "scripts\validate_model_card.py"; Target = "scripts\validate_model_card.py" }
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
)

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$required = @(
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    "templates\model_card.md",
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    "README.md"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
) + $copies.Source
# [PÉDAGOGIE] ITÉRATION — la même vérification est appliquée à chaque élément de manière
# [PÉDAGOGIE] contrôlée.
foreach ($relativePath in $required) {
    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if (-not (Test-Path -LiteralPath (Join-Path $overlay $relativePath))) {
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        throw "Surcouche M25 incomplète : $relativePath est absent."
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$lockBefore = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$backupRoot = Join-Path $env:TEMP "CISIA_M25_backup_$stamp"
# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$backupUsed = $false

# [PÉDAGOGIE] ITÉRATION — la même vérification est appliquée à chaque élément de manière
# [PÉDAGOGIE] contrôlée.
foreach ($item in $copies) {
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $source = Join-Path $overlay $item.Source
    # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
    # [PÉDAGOGIE] constante cachée.
    $target = Join-Path $project $item.Target
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null

    # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
    # [PÉDAGOGIE] compréhensible.
    if (Test-Path -LiteralPath $target) {
        # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite
        # [PÉDAGOGIE] une constante cachée.
        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite
        # [PÉDAGOGIE] une constante cachée.
        $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        # [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec
        # [PÉDAGOGIE] compréhensible.
        if ($sourceHash -eq $targetHash) {
            # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de
            # [PÉDAGOGIE] secret.
            Write-Host "DEJA_IDENTIQUE $($item.Target)"
            # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la
            # [PÉDAGOGIE] preuve qui autorise la suite.
            continue
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        }

        # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite
        # [PÉDAGOGIE] une constante cachée.
        $backupTarget = Join-Path $backupRoot $item.Target
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        New-Item -ItemType Directory -Path (Split-Path -Parent $backupTarget) -Force | Out-Null
        # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve
        # [PÉDAGOGIE] qui autorise la suite.
        Copy-Item -LiteralPath $target -Destination $backupTarget -Force
        # [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite
        # [PÉDAGOGIE] une constante cachée.
        $backupUsed = $true
        # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de
        # [PÉDAGOGIE] secret.
        Write-Host "SAUVEGARDE $($item.Target) -> $backupTarget"
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    }

    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    Copy-Item -LiteralPath $source -Destination $target -Force
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "INSTALLE $($item.Target)"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$card = Join-Path $project "docs\model_card.md"
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if (-not (Test-Path -LiteralPath $card)) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    New-Item -ItemType Directory -Path (Split-Path -Parent $card) -Force | Out-Null
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    Copy-Item -LiteralPath (Join-Path $overlay "templates\model_card.md") -Destination $card
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "INITIALISE docs\model_card.md"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
} else {
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "PRESERVE docs\model_card.md"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] ÉTAT LOCAL — nommer cette valeur rend la décision suivante lisible et évite une
# [PÉDAGOGIE] constante cachée.
$lockAfter = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($lockAfter -ne $lockBefore) {
    # [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
    # [PÉDAGOGIE] autorise la suite.
    throw "uv.lock a changé pendant l'application de la surcouche M25."
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}

# [PÉDAGOGIE] DÉCISION — tester le prérequis avant l'action rend le chemin d'échec compréhensible.
if ($backupUsed) {
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "BACKUP_ROOT=$backupRoot"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
} else {
    # [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
    Write-Host "BACKUP_ROOT=NON_NECESSAIRE"
# [PÉDAGOGIE] ÉTAPE — lire cette commande comme une intention, puis identifier la preuve qui
# [PÉDAGOGIE] autorise la suite.
}
# [PÉDAGOGIE] OBSERVABILITÉ — ce message annonce l'étape ou sa preuve sans afficher de secret.
Write-Host "M25_OVERLAY=READY"
