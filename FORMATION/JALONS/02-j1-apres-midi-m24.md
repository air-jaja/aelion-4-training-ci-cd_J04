# 02 — J1 apres-midi — M24

> Windows, macOS ou Linux : suivre la section M24 du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md).

Objectif : rendre le paquet reproductible et versionne par la qualite locale,
la CI et les preuves DVC/MLflow, sans modifier le lock en salle.

Recu par le jalon : etat M23 stabilise, fichiers de qualite et tests Gold. Les
artefacts indispensables restent disponibles localement pour le mode hors ligne.

A faire : executer pre-commit, lire le workflow CI, faire rougir puis reverdir un
test, versionner donnees et modele, tracer parametres/metriques.

Preuve :

```powershell
uv sync --frozen --extra dev --extra mlops
uv run pre-commit run --all-files
uv run pytest -q
git diff --exit-code -- uv.lock
```

Rattrapage : suite pytest + ruff + lecture de la CI ; DVC/MLflow complet passent
en reserve si le reseau ou un remote de donnees manque.
