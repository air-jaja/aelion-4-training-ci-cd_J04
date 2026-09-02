# =============================================================================
# FICHIER : scripts/prove_idempotence.ps1
# ROLE    : prouver l'idempotence du flow sur PostgreSQL, dans Compose.
# -----------------------------------------------------------------------------
# PRINCIPE : deux executions identiques, deux comptages. S'ils different,
# l'upsert ne fait pas son travail et le contrat du jalon est rompu.
#
# CE QUE CE SCRIPT NE FAIT PAS : il ne teste pas le code metier. Cela releve de
# `uv run pytest tests/test_predict_flow.py`, qui couvre les memes garanties en
# SQLite, sans Docker. Ici on verifie l'assemblage REEL : image, reseau, base.
#
# PREREQUIS :
#   $env:INDUSENSE_DATA_DIR pointe vers le jeu de donnees complet
#   docker compose up -d db   (la base doit etre saine)
# =============================================================================

[CmdletBinding()]
param(
    # Population attendue apres scoring. AJUSTER selon le jeu de donnees :
    #   jeu complet du parcours -> 15
    #   donnees du depot (4 machines) -> 4
    [int]$PopulationAttendue = 15
)

$ErrorActionPreference = "Stop"

# --- 1. Verifier le jeu de donnees -------------------------------------------
# Le jeu complet n'est PAS dans le depot : il est monte depuis l'exterieur.
if (-not $env:INDUSENSE_DATA_DIR) {
    throw "Definir INDUSENSE_DATA_DIR vers le jeu complet"
}
$sourceData = (Resolve-Path -LiteralPath $env:INDUSENSE_DATA_DIR -ErrorAction Stop).Path
Write-Host "Jeu de donnees : $sourceData"

# --- 2. Reconstruire l'image --------------------------------------------------
# Sans --build, Compose reutilise une image qui peut dater d'avant l'ajout du
# flow. C'est la premiere cause de resultats incoherents.
docker compose build api
if ($LASTEXITCODE -ne 0) { throw "Build API a echoue : code $LASTEXITCODE" }

# --- 3. Arguments du flow -----------------------------------------------------
# --no-deps : on ne relance pas la base, elle doit deja tourner.
# Les variables PREFECT_* coupent la telemetrie et forcent le profil local :
# sans elles, chaque run tente un appel reseau sortant et ralentit la demo.
$flowArgs = @(
    "compose", "run", "--rm", "--no-deps",
    "-e", "PREFECT_PROFILE=ephemeral",
    "-e", "PREFECT_SERVER_ANALYTICS_ENABLED=false",
    "-e", "PREFECT_CLOUD_ENABLE_ORCHESTRATION_TELEMETRY=false",
    "-e", "INDUSENSE_DATA_DIR=/app/data/run",
    "--volume", "${sourceData}:/app/data/run:ro",
    "api", "python", "-m", "indusense.flows.predict_flow"
)

# --- 4. Premier passage -------------------------------------------------------
Write-Host "`n=== RUN 1 ===" -ForegroundColor Cyan
docker @flowArgs
if ($LASTEXITCODE -ne 0) { throw "Flow run 1 a echoue : code $LASTEXITCODE" }

$count1 = (docker compose exec -T db psql -U indusense `
    -d indusense -tA -c "SELECT count(*) FROM predictions;").Trim()
if ($LASTEXITCODE -ne 0) { throw "Lecture count1 a echoue : code $LASTEXITCODE" }
Write-Host "Lignes apres run 1 : $count1"

# --- 5. Second passage, strictement identique ---------------------------------
# Memes donnees, memes parametres. Tout ecart de comptage viendrait donc de
# l'ecriture, pas de l'entree.
Write-Host "`n=== RUN 2 ===" -ForegroundColor Cyan
docker @flowArgs
if ($LASTEXITCODE -ne 0) { throw "Flow run 2 a echoue : code $LASTEXITCODE" }

$count2 = (docker compose exec -T db psql -U indusense `
    -d indusense -tA -c "SELECT count(*) FROM predictions;").Trim()
if ($LASTEXITCODE -ne 0) { throw "Lecture count2 a echoue : code $LASTEXITCODE" }
Write-Host "Lignes apres run 2 : $count2"

# --- 6. Les deux verdicts -----------------------------------------------------
# VERDICT 1 — idempotence : le compte ne doit pas bouger.
if ([int]$count1 -ne [int]$count2) {
    throw "Idempotence KO : $count1 puis $count2"
}

# VERDICT 2 — population : le compte doit valoir ce qu'on attend.
# Un pipeline idempotent qui n'ecrit RIEN passerait le premier verdict.
if ([int]$count2 -ne $PopulationAttendue) {
    throw "Population scoree inattendue : $count2 au lieu de $PopulationAttendue"
}

Write-Host "`nIDEMPOTENCE OK : $count1 lignes, stables sur deux passages." -ForegroundColor Green

# --- 7. Detail, pour la lecture en seance -------------------------------------
docker compose exec -T db psql -U indusense -d indusense -c `
    "SELECT machine, prediction_ts, round(proba_panne::numeric, 3) AS proba, decision FROM predictions ORDER BY machine;"
