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

# [PÉDAGOGIE] CIBLE `install` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
install:
	uv sync --extra dev

# [PÉDAGOGIE] CIBLE `test` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
test:
	uv run pytest -q

# [PÉDAGOGIE] CIBLE `lint` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
lint:
	uv run ruff check .

# [PÉDAGOGIE] CIBLE `format-check` — nomme une intention et ses éventuels prérequis avant la
# [PÉDAGOGIE] recette tabulée.
format-check:
	uv run black --check .

# [PÉDAGOGIE] CIBLE `check` — nomme une intention et ses éventuels prérequis avant la recette
# [PÉDAGOGIE] tabulée.
check:
	uv run pytest -q
	uv run ruff check .
	uv run black --check .
	uv run indusense --help
