# Plan local des douze jalons

Cadence visio : **09h00–12h30**, pause dejeuner **12h30–13h30**,
**13h30–17h00**. Chaque demi-journee contient 210 minutes, pause courte incluse.

| N° | Date et plage | Branche publiee au moment voulu | Contenu revele, sans solution future |
|---:|---|---|---|
| 01 | lun. 24/08, matin | `jalon/01` | Socle fin S2, M23 : structure, package, anti-fuite, CLI |
| 02 | lun. 24/08, apres-midi | `jalon/02` | Stabilisation M23, M24 : qualite, tests, CI, versioning |
| 03 | mar. 25/08, matin | `jalon/03` | Stabilisation M24, squelette FastAPI M25 |
| 04 | mar. 25/08, apres-midi | `jalon/04` | API M25 rejouable, atelier menaces et garde-fous M26 |
| 05 | mer. 26/08, matin | `jalon/05` | API durcie, Dockerfile et preuves M27 |
| 06 | mer. 26/08, apres-midi | `jalon/06` | Image M27, Compose/smoke M28 ; M29 reste masque jusqu'a J4 |
| 07 | mar. 01/09, matin | `jalon/07` | Stack M28, orchestration Prefect M29–M30 |
| 08 | mar. 01/09, apres-midi | `jalon/08` | Pipeline stabilise, bascule vers PayGuard adversarial |
| 09 | mer. 02/09, matin | `jalon/09` | Retour InduSense, fenetres et mesure du drift |
| 10 | mer. 02/09, apres-midi | `jalon/10` | Drift stabilise, Prometheus/Grafana et runbook |
| 11 | jeu. 03/09, matin | `jalon/11` | Stack observable, Game Day casse phases 0–2 |
| 12 | jeu. 03/09, apres-midi | `jalon/12` | Game Day phases 3–6, preuves et post-mortem, sans corrige |

## Politique de revelation

- `main` reste le point de depart fin Sprint 2.
- Les branches publiques sont `jalon/01` a `jalon/12` ; leur marqueur interne
  conserve le slug pedagogique long documente dans `JALON_INDEX.tsv`.
- Les douze branches sont deja publiees. Le formateur annonce uniquement le
  numero du jalon courant afin de ne pas devoiler la suite du parcours.
- Une branche n'apporte que l'etat necessaire au moment considere : le corrige
  d'une demi-journee peut devenir le prerequis de la suivante, jamais avant.
- J4 apres-midi utilise le depot PayGuard separe ; J6 utilise la branche cassee
  dediee. Le present depot n'integre aucune solution du Game Day.
- Le socle operationnel et la reference semantique de fin S2 sont deux sources
  distinctes : voir [`PROVENANCE_SOCLE.md`](PROVENANCE_SOCLE.md).
