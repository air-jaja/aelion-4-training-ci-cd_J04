# 04 — J2 apres-midi — M26

> Windows, macOS ou Linux : suivre la section M26 du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md).

Objectif : modeliser les menaces puis durcir l'API sans rendre la politique de
securite surchargeable par le client.

Recu par le jalon : API M25 rejouable, matrice de menaces a completer et tests de
garde-fous. Aucun conteneur.

A faire : taille de corps 413, `Content-Length` illisible 400, rate limit 429,
dependance fixe, request-id et logs sans secret.

Preuve :

```powershell
uv run pytest tests/test_api.py tests/test_security.py -q
uv run python -c "from inspect import signature; from indusense.api.security import rate_limit_dependency; print(signature(rate_limit_dependency))"
```

La signature affiche uniquement `request`; ni `limit` ni `window` ne doivent
etre exposables par query string.

Rattrapage : auth + 413 + 429 ; l'arbre d'attaque detaille passe en restitution.
