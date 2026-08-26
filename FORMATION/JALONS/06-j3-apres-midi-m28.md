# 06 — J3 apres-midi — M28

> Windows, macOS ou Linux : suivre la section Compose du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md).

Objectif : orchestrer API, Prometheus et Grafana, puis prouver que la stack sait
attendre la readiness au lieu de courir au demarrage.

Recu par le jalon : image M27 stabilisee, Compose de travail, smoke test et
configuration locale de monitoring. Pas de pipeline Prefect resolu.

A faire : `docker compose config`, `up --build`, healthcheck, dependances,
volumes, smoke et `down`. Le contenu M29 reste masque jusqu'a J4 matin, selon le
conducteur final et le pas-a-pas apprenant.

Preuve :

```powershell
docker compose config -q
docker compose up -d --build
docker compose ps
uv run pytest tests/test_smoke_compose.py -q
docker compose down
```

Rattrapage : API seule + lecture du graphe Compose ; le smoke test remplace la
navigation manuelle.
