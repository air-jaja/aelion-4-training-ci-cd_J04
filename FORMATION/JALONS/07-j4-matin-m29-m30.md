# 07 — J4 matin — M29–M30

> Windows, macOS ou Linux : suivre la section Prefect/idempotence du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md).

Objectif : passer d'un script a un pipeline orchestre, rejouable et idempotent.

Recu par le jalon : stack M28, squelette `flows/pipeline.py`, donnees locales et
demo d'idempotence. Aucun corrige PayGuard.

A faire : decomposer en tasks/flow, nommer les runs, gerer reprise et cache,
prouver qu'un second passage ne duplique pas les sorties.

Preuve :

```powershell
uv run python flows/pipeline.py
uv run python scripts/demo_prefect_idempotence.py
git status --short
```

Rattrapage : pipeline local sequentiel avec traces claires ; l'UI Prefect et les
politiques de retry avancees sont de la reserve.
