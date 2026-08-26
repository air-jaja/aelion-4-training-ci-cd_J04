# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/api/__init__.py
# [PÉDAGOGIE] MODULE  — M25 — contrat d'API, validation et preuve de readiness
# [PÉDAGOGIE] RÔLE    — Exposer le modèle derrière un contrat HTTP explicite, testable et
# [PÉDAGOGIE]           observable.
# [PÉDAGOGIE] THÉORIE — Pydantic valide la forme et les invariants avant l'appel au modèle
# [PÉDAGOGIE]           • liveness et readiness répondent à deux questions opérationnelles
# [PÉDAGOGIE]             différentes
# [PÉDAGOGIE]           • l'injection de dépendances permet d'isoler le chargement du modèle dans
# [PÉDAGOGIE]             les tests
# [PÉDAGOGIE] À VOIR  — Swagger/TestClient doivent rendre visibles les entrées, sorties et codes
# [PÉDAGOGIE]           2xx/4xx/5xx attendus.
# [PÉDAGOGIE] PIÈGE   — Une réponse 200 ne suffit pas si le schéma, la version du modèle ou la
# [PÉDAGOGIE]           normalisation sont faux.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
#  src/indusense/api/__init__.py  —  marqueur de SOUS-PACKAGE « api »
# -----------------------------------------------------------------------------
#  Place dans le projet : Sprint 3, module API (n°25) + sécurité (n°26).
#
#  À QUOI SERT CE FICHIER ?
#  La SEULE présence d'un fichier nommé `__init__.py` transforme le dossier
#  `api/` en « package » (= boîte) Python. Sans lui, Python ne saurait pas que
#  `api` est un module importable, et les lignes comme
#      from indusense.api.main import app
#      from indusense.api.schemas import PredictionResponse
#  échoueraient avec une erreur « ModuleNotFoundError ».
#
#  POURQUOI EST-IL VIDE ?
#  Un `__init__.py` n'a AUCUNE obligation de contenir du code. Ici on n'a rien
#  de particulier à exécuter au moment où le package est importé (pas de version
#  à déclarer, pas de raccourci d'import à exposer). On le laisse donc vide :
#  son simple rôle est d'exister pour « activer » le package. C'est un usage
#  tout à fait normal et courant en Python.
#
#  ORGANISATION DU SOUS-PACKAGE `api/` (les 4 autres fichiers) :
#    - schemas.py     : le « contrat » des données entrantes/sortantes (Pydantic).
#    - security.py    : les garde-fous (taille du corps de requête, anti-flood).
#    - model_store.py : le chargement et le stockage du modèle de ML en mémoire.
#    - main.py        : l'application FastAPI (les routes /health, /predict-...).
# =============================================================================

# (Intentionnellement vide : voir le bloc d'explication ci-dessus.)
