#!/usr/bin/env bash
# =============================================================================
# FICHIER : scripts/build_image.sh
# ROLE    : equivalent macOS / Linux de build_image.ps1.
# USAGE   : ./scripts/build_image.sh [--calibrate] [--no-cache] [tag]
# =============================================================================
set -euo pipefail

TAG="indusense-api:m27"
CACHE_DIR=".buildx-cache"
CALIBRATE=0
USE_CACHE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --calibrate) CALIBRATE=1; shift ;;
    --no-cache)  USE_CACHE=0; shift ;;
    *)           TAG="$1"; shift ;;
  esac
done

# 1. BuildKit est indispensable : `docker build` classique ignore --cache-to.
if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx introuvable." >&2
  exit 1
fi

# 2. Le builder par defaut (pilote docker) ne sait pas exporter de cache.
if ! docker buildx ls | grep -q indusense-builder; then
  echo "Creation du builder BuildKit 'indusense-builder'..."
  docker buildx create --name indusense-builder --driver docker-container --use >/dev/null
else
  docker buildx use indusense-builder
fi

# 3. Construction. --load ramene l'image dans le demon local.
ARGS=(buildx build --tag "$TAG" --load)

if [[ $USE_CACHE -eq 1 ]]; then
  # mode=max exporte aussi les couches du stage `build` : sans lui, la
  # compilation des dependances est refaite a chaque fois.
  ARGS+=(--cache-from "type=local,src=${CACHE_DIR}")
  ARGS+=(--cache-to "type=local,dest=${CACHE_DIR}-new,mode=max")
fi

ARGS+=(.)

echo "Construction de ${TAG}..."
debut=$(date +%s)
docker "${ARGS[@]}"
echo "Construite en $(($(date +%s) - debut)) s"

# 4. Rotation du cache : BuildKit ne peut pas ecrire dans le repertoire qu'il
#    lit, et sans rotation le cache grossit indefiniment.
if [[ $USE_CACHE -eq 1 && -d "${CACHE_DIR}-new" ]]; then
  rm -rf "${CACHE_DIR}"
  mv "${CACHE_DIR}-new" "${CACHE_DIR}"
fi

# 5. Calibration ou controle.
if [[ $CALIBRATE -eq 1 ]]; then
  uv run python scripts/check_image.py --calibrate "$TAG"
else
  uv run python scripts/check_image.py "$TAG"
fi
