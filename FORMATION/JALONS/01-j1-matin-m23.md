# 01 — J1 matin — M23

> Windows, macOS ou Linux : suivre la section M23 du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md).

Objectif : repartir du paquet de fin S2 et prouver qu'il est importable,
testable et sans fuite temporelle.

Recu par le jalon : package `src/indusense`, Gold, modele RF, metadata, CLI et
tests de base. Aucun element API, Docker ou monitoring.

A faire : observer le layout, verifier `shift(1)` avant `rolling`, tester la
normalisation des IDs, extraire `clean_sensor_data` puis faire passer son test.

Preuve :

```powershell
uv run pytest tests/test_package.py tests/test_loaders.py tests/test_temporal.py -q
uv run ruff check .
uv run indusense --help
```

Rattrapage : rester sur les tests fournis et le package importable ; CLI avancee
et couverture supplementaire sont de la reserve.
