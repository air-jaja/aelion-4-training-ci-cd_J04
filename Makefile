# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — Makefile
# [PÉDAGOGIE] MODULE  — M23–M34 — commandes reproductibles et interface d'exploitation
# [PÉDAGOGIE] RÔLE    — Donner des noms stables aux commandes usuelles afin que l'équipe exécute
# [PÉDAGOGIE]           la même procédure.
# [PÉDAGOGIE] THÉORIE — une cible Make exprime une intention plutôt qu'une suite mémorisée de
# [PÉDAGOGIE]           commandes
# [PÉDAGOGIE]           • les dépendances entre cibles rendent l'ordre d'exécution visible
# [PÉDAGOGIE]           • une commande documentée devient une brique de runbook et de CI
# [PÉDAGOGIE] À VOIR  — make help puis la cible choisie doivent rendre l'action et sa preuve
# [PÉDAGOGIE]           faciles à retrouver.
# [PÉDAGOGIE] PIÈGE   — Une recette Make exige une tabulation ; la remplacer par des espaces peut
# [PÉDAGOGIE]           casser son interprétation.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# Makefile — Raccourcis de commandes pour le projet "InduSense"
# -----------------------------------------------------------------------------
# ROLE : regroupe les commandes frequentes sous des noms courts ("cibles").
# Au lieu de retaper une longue ligne, on lance par exemple :  make test
# L'outil "make" lit ce fichier et execute la recette associee a la cible.
#
# ATTENTION (syntaxe make) : chaque ligne de recette (les commandes a executer)
# DOIT commencer par une TABULATION, pas par des espaces. C'est une regle stricte
# de make. Les commentaires (#) sont places sur leur propre ligne, jamais sur
# une ligne de recette indentee.
#
# Cibles disponibles ci-dessous :
#   make install       -> installe les dependances (prod + groupe dev)
#   make test          -> lance les tests
#   make lint          -> verifie la qualite du code (ruff)
#   make format-check  -> verifie le formatage (black), sans modifier
#   make check         -> tout enchaine : tests + lint + format + CLI
# =============================================================================

# Cible "install" : installe les dependances du projet ainsi que le groupe dev.
# [PÉDAGOGIE] CIBLE `install` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
install:
	uv sync --frozen --extra dev

# Cible "test" : execute la suite de tests avec pytest (-q = sortie concise).
# [PÉDAGOGIE] CIBLE `test` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
test:
	uv run pytest -q
 	uv run pytest -m "not smoke"

test-smoke:      ## Suite reseau, apres docker compose up -d
 	uv run pytest -m smoke
#
test-all:        ## Tout, avec le detail des ignores
 	uv run pytest -rs

# Cible "lint" : analyse la qualite du code avec ruff (detecte les problemes).
# [PÉDAGOGIE] CIBLE `lint` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
lint:
	uv run ruff check .

# Cible "format-check" : verifie le formatage avec black (--check = ne modifie rien,
# echoue seulement si du code n'est pas bien formate).
# [PÉDAGOGIE] CIBLE `format-check` — nomme une intention et ses éventuels prérequis avant la
# [PÉDAGOGIE] recette tabulée.
format-check:
	uv run black --check .

# Cible "check" : verification complete. Enchaine les 4 commandes ci-dessous,
# dans l'ordre. Si l'une echoue, make s'arrete (utile avant un commit/push).
# [PÉDAGOGIE] CIBLE `check` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
check:
	uv run pytest -q
	uv run ruff check .
	uv run black --check .
	uv run indusense --help

# Lancer l'API en local avec rechargement auto (module 25)
# [PÉDAGOGIE] CIBLE `serve` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
serve:
	uv run uvicorn indusense.api.main:app --reload

# --- Docker (J3 : modules 27-28) ---
# [PÉDAGOGIE] CIBLE `docker-build` — nomme une intention et ses éventuels prérequis avant la
# [PÉDAGOGIE] recette tabulée.
docker-build:
	docker build -t indusense:local .

# [PÉDAGOGIE] CIBLE `up` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
up:
	docker compose up -d --build

# [PÉDAGOGIE] CIBLE `down` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
down:
	docker compose down

# [PÉDAGOGIE] CIBLE `logs` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
logs:
	docker compose logs -f

# [PÉDAGOGIE] CIBLE `ps` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
ps:
	docker compose ps

# [PÉDAGOGIE] CIBLE `smoke` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
smoke:
	curl -fsS http://localhost:8000/health && echo " OK"

# =============================================================================
# COMMANDES UTILES — a mettre dans le Makefile ou les fiches de jalon
# =============================================================================
#
#   uv run pytest                       suite complete + recapitulatif
#   uv run pytest -v                    une ligne par test : PASSED / FAILED / SKIPPED
#   uv run pytest -m "not smoke"        sans Docker, rapide
#   uv run pytest -m smoke              apres docker compose up -d
#   uv run pytest -rs                   raison de CHAQUE test ignore
#   uv run pytest --lf                  rejoue seulement les derniers echecs
#   uv run pytest -k "image"            filtre par nom de test
#   uv run pytest --tb=long             pile complete pour deboguer
#
# =============================================================================
# CIBLES MAKEFILE SUGGEREES
# =============================================================================
#
# test:            ## Suite rapide, sans Docker
# 	uv run pytest -m "not smoke"
#
# test-smoke:      ## Suite reseau, apres docker compose up -d
# 	uv run pytest -m smoke
#
# test-all:        ## Tout, avec le detail des ignores
# 	uv run pytest -rs
#
# =============================================================================
