# =============================================================================
# FICHIER : scripts/build_image.ps1
# ROLE    : construire l'image M27 avec un cache BuildKit persistant, puis la
#           controler contre le budget versionne.
# -----------------------------------------------------------------------------
# POURQUOI UN CACHE EXPORTE ?
#
# Le Dockerfile utilise deja `RUN --mount=type=cache` pour le cache d'uv. Ce
# cache-la vit DANS le builder : il accelere les rebuilds sur la meme machine,
# mais disparait sur un runner de CI neuf, ou apres `docker builder prune`.
#
# `--cache-to` / `--cache-from` exportent les couches vers un repertoire (ou un
# registre). Elles survivent au builder, se partagent entre machines, et se
# restaurent en CI. C'est ce qui fait passer un rebuild de plusieurs minutes a
# quelques secondes quand seul `src/` a change.
#
# ORDRE DES COUCHES : le Dockerfile copie pyproject.toml + uv.lock AVANT src/,
# et fait deux `uv sync` distincts. C'est ce decoupage qui rend le cache utile :
# modifier une ligne de code n'invalide pas l'installation des dependances.
# =============================================================================

[CmdletBinding()]
param(
    [string]$Tag = "indusense-api:m27",
    [string]$CacheDir = ".buildx-cache",
    [switch]$Calibrate,
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

# --- 1. Verifier que buildx est disponible -----------------------------------
# `docker build` classique ignore --cache-to. Il faut le builder BuildKit.
docker buildx version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "docker buildx introuvable. Installer Docker Desktop >= 4.x ou le plugin buildx."
}

# --- 2. Creer un builder dedie s'il n'existe pas ------------------------------
# Le builder par defaut ("default", pilote docker) ne sait pas exporter de
# cache. Le pilote docker-container, si.
$builders = docker buildx ls
if ($builders -notmatch "indusense-builder") {
    Write-Host "Creation du builder BuildKit 'indusense-builder'..."
    docker buildx create --name indusense-builder --driver docker-container --use | Out-Null
} else {
    docker buildx use indusense-builder
}

# --- 3. Construire -----------------------------------------------------------
$arguments = @(
    "buildx", "build",
    "--tag", $Tag,
    "--load"                      # sans --load, l'image reste dans le builder
)

if (-not $NoCache) {
    $arguments += @(
        "--cache-from", "type=local,src=$CacheDir"
        # mode=max exporte AUSSI les couches intermediaires du stage `build`.
        # Sans lui, seule l'image finale est mise en cache, et le stage de
        # compilation est refait a chaque fois : l'essentiel du gain est perdu.
        "--cache-to", "type=local,dest=$CacheDir-new,mode=max"
    )
}

$arguments += "."

Write-Host "Construction de $Tag..."
$chrono = [System.Diagnostics.Stopwatch]::StartNew()
docker @arguments
if ($LASTEXITCODE -ne 0) { throw "Echec de la construction." }
$chrono.Stop()
Write-Host ("Construite en {0:N1} s" -f $chrono.Elapsed.TotalSeconds)

# --- 4. Faire tourner le cache -----------------------------------------------
# BuildKit ne sait pas ecrire dans le repertoire qu'il lit : sans cette
# rotation, le cache grossit indefiniment (chaque build empile ses couches).
if (-not $NoCache -and (Test-Path "$CacheDir-new")) {
    if (Test-Path $CacheDir) { Remove-Item -Recurse -Force $CacheDir }
    Move-Item "$CacheDir-new" $CacheDir
}

# --- 5. Calibrer ou controler ------------------------------------------------
if ($Calibrate) {
    uv run python scripts/check_image.py --calibrate $Tag
} else {
    uv run python scripts/check_image.py $Tag
    if ($LASTEXITCODE -ne 0) { throw "Controle qualite en echec." }
}
