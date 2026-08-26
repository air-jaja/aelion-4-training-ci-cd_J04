# 10 — J5 apres-midi — M33–M34

> Windows, macOS ou Linux : suivre la section Prometheus/Grafana du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md), notamment le
> raccord `host.docker.internal` sous Docker Engine Linux.

Objectif : rendre visibles service, latence, erreurs et drift, puis relier chaque
alerte a une action du runbook.

Recu par le jalon : drift InduSense stabilise, Prometheus, provisioning Grafana,
dashboard de travail et exporteur de metriques. Aucun Game Day.

A faire : exposer `/metrics`, verifier les targets, lire quatre panneaux,
declencher une alerte controlee et executer le runbook.

Preuve :

```powershell
docker compose config -q
docker compose up -d --build
Invoke-WebRequest http://127.0.0.1:8000/metrics -UseBasicParsing
docker compose ps
```

Sous macOS/Linux, remplacer la ligne `Invoke-WebRequest` par
`curl -fsS http://127.0.0.1:8000/metrics | head`.

Rattrapage : `/metrics` + target Prometheus UP + un panneau + une action de
runbook ; Locust et panneaux supplementaires sont de la reserve.
