# 03 — J2 matin — M25

> Windows, macOS ou Linux : suivre la section M25 du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md), notamment pour
> le second terminal et l'appel HTTP.

Objectif : exposer le contrat I/O de fin S2 avec FastAPI.

Recu par le jalon : socle M24 stabilise, `payload.json` et squelette
`src/indusense/api/`. Aucun garde-fou M26, Dockerfile ou Compose.

A faire : distinguer `/health` et `/ready`, charger le modele une fois, proteger
la prediction par cle API, normaliser l'ID au bord et obtenir 401/422/503.

Preuve :

```powershell
uv run pytest tests/test_api.py -q
uv run uvicorn indusense.api.main:app --reload --port 8000
```

Dans un second terminal :
`Invoke-RestMethod http://127.0.0.1:8000/health` sous Windows, ou
`curl -fsS http://127.0.0.1:8000/health` sous macOS/Linux.
Swagger : `http://127.0.0.1:8000/docs`.

Rattrapage : health + auth 401 + validation 422 ; image et variantes restent en
reserve.
