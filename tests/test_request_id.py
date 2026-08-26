# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_request_id.py
# [PÉDAGOGIE] MODULE  — M25 — contrat d'API, validation et preuve de readiness
# [PÉDAGOGIE] RÔLE    — Prouver que le contrat publié (OpenAPI) et la tracabilité des appels
# [PÉDAGOGIE]           (X-Request-ID) sont vérifiables automatiquement.
# [PÉDAGOGIE] THÉORIE — La doc OpenAPI n'est pas un commentaire : elle est GÉNÉRÉE depuis les
# [PÉDAGOGIE]           schémas Pydantic, donc testable comme n'importe quelle sortie
# [PÉDAGOGIE]           • un identifiant de corrélation permet de relier les logs d'un même appel
# [PÉDAGOGIE]           • un middleware s'applique à TOUTES les réponses, y compris les erreurs
# [PÉDAGOGIE] À VOIR  — Swagger (/docs) doit afficher la même contrainte que celle testée ici.
# [PÉDAGOGIE] PIÈGE   — Tester une route absente de main.py produit un échec permanent, pas une
# [PÉDAGOGIE]           spécification. Ne lister que les routes réellement exposées.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_request_id.py
# RÔLE    : Deux familles de preuves, complémentaires de tests/test_api.py.
# -----------------------------------------------------------------------------
# CE QUE CE FICHIER VÉRIFIE :
#   1. LE CONTRAT PUBLIÉ — /openapi.json déclare bien les routes attendues, et
#      la contrainte métier `min_length=7` (7 relevés minimum) est VISIBLE dans
#      la documentation. Un contrat qui n'est pas publié n'est pas un contrat.
#   2. LA TRAÇABILITÉ — chaque réponse porte un en-tête X-Request-ID. S'il est
#      fourni par le client, il est renvoyé tel quel (corrélation de bout en
#      bout). Sinon, le serveur en génère un.
#
# POURQUOI C'EST IMPORTANT :
#   En production, un incident se diagnostique en suivant un identifiant unique
#   à travers les logs du client, de l'API et du modèle. Sans lui, on ne sait
#   pas quelle ligne de log correspond à quel appel.
#
# À NOTER : aucun modèle n'est nécessaire ici. On n'appelle que /health, qui ne
# dépend pas du bundle. Pas besoin de app.dependency_overrides.
# =============================================================================

# --- Imports -----------------------------------------------------------------

# uuid : sert à VALIDER le format de l'identifiant généré par le serveur.
# uuid.UUID(chaine) lève ValueError si la chaîne n'est pas un UUID -> le test
# échoue automatiquement, sans assertion supplémentaire.
import uuid

# TestClient : le "faux navigateur" de FastAPI. Aucun port réseau n'est ouvert.
from fastapi.testclient import TestClient

# app : l'application FastAPI du projet (routes, middleware, dépendances).
from indusense.api.main import app

# Un seul client partagé : le middleware est stateless, rien à isoler.
client = TestClient(app)

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser. Ne lister QUE les routes réellement exposées par main.py.
EXPECTED_ROUTES = ("/health", "/ready", "/predict-tabular")

# [PÉDAGOGIE] CONSTANTE / CONTRAT — miroir de `min_length=7` dans schemas.py.
# [PÉDAGOGIE] Si quelqu'un change le schéma sans changer ce test, le test le signale.
MIN_READINGS = 7


# =============================================================================
# PARTIE 1 — LE CONTRAT OPENAPI
# =============================================================================


# [PÉDAGOGIE] BLOC `test_openapi_documents_contract` — ce test transforme un comportement attendu
# [PÉDAGOGIE] en preuve exécutable.
# [PÉDAGOGIE] CONTRAT — preuve : les routes annoncées existent dans le document publié.
def test_openapi_documents_contract():
    """Les trois routes du jalon 03 sont publiées dans /openapi.json."""
    # FastAPI génère ce document automatiquement depuis les décorateurs @app.get
    # et @app.post. On ne teste donc PAS un fichier écrit à la main.
    spec = client.get("/openapi.json").json()

    for route in EXPECTED_ROUTES:
        # Message d'échec explicite : sans lui, pytest dirait juste "assert False".
        assert route in spec["paths"], f"Route absente du contrat publié : {route}"


# [PÉDAGOGIE] BLOC `test_openapi_exposes_min_readings` — ce test relie une règle métier à sa
# [PÉDAGOGIE] publication.
# [PÉDAGOGIE] CONTRAT — preuve : la contrainte Pydantic est traduite en JSON Schema.
def test_openapi_exposes_min_readings():
    """La contrainte `min_length=7` de schemas.py est visible dans la doc."""
    spec = client.get("/openapi.json").json()
    schema = spec["components"]["schemas"]["TabularPredictionRequest"]
    readings = schema["properties"]["readings"]

    # Pydantic v2 -> JSON Schema : `min_length` sur une liste devient `minItems`.
    # C'est ce que Swagger affiche, et ce qu'un client tiers lira pour générer
    # son propre code. La règle métier des 7 relevés (6 pour l'historique + 1
    # pour la ligne courante) est donc opposable.
    assert readings["minItems"] == MIN_READINGS


# [PÉDAGOGIE] BLOC `test_openapi_declares_response_schema` — ce test vérifie la sortie, pas
# [PÉDAGOGIE] seulement l'entrée.
# [PÉDAGOGIE] CONTRAT — preuve : le schéma de réponse est publié, pas seulement implémenté.
def test_openapi_declares_response_schema():
    """Le schéma de réponse de /predict-tabular est publié."""
    spec = client.get("/openapi.json").json()

    assert "PredictionResponse" in spec["components"]["schemas"]
    responses = spec["paths"]["/predict-tabular"]["post"]["responses"]
    assert "200" in responses


# =============================================================================
# PARTIE 2 — LA PROPAGATION DE X-REQUEST-ID
# =============================================================================


# [PÉDAGOGIE] BLOC `test_request_id_echoed_when_supplied` — ce test couvre le cas "client
# [PÉDAGOGIE] fournisseur d'identifiant".
# [PÉDAGOGIE] CONTRAT — preuve : la valeur entrante ressort INCHANGÉE.
def test_request_id_echoed_when_supplied():
    """Un X-Request-ID fourni par le client est renvoyé tel quel."""
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    # Renvoyé à l'identique : c'est ce qui permet au client de corréler sa propre
    # trace avec celle du serveur.
    assert response.headers["X-Request-ID"] == "abc-123"


# [PÉDAGOGIE] BLOC `test_request_id_generated_when_absent` — ce test couvre le cas "client
# [PÉDAGOGIE] silencieux".
# [PÉDAGOGIE] CONTRAT — preuve : le serveur génère un identifiant valide.
def test_request_id_generated_when_absent():
    """Sans en-tête entrant, le serveur génère un UUID valide."""
    response = client.get("/health")

    # uuid.UUID(...) lève ValueError si le format est invalide : le test échoue
    # alors de lui-même. Pas besoin d'assert supplémentaire.
    uuid.UUID(response.headers["X-Request-ID"])


# [PÉDAGOGIE] BLOC `test_request_id_is_unique_per_request` — ce test empêche une régression
# [PÉDAGOGIE] classique : un identifiant calculé une seule fois au démarrage.
# [PÉDAGOGIE] CONTRAT — preuve : deux appels produisent deux identifiants distincts.
def test_request_id_is_unique_per_request():
    """Deux appels sans en-tête reçoivent deux identifiants différents."""
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]

    assert first != second


# [PÉDAGOGIE] BLOC `test_request_id_present_on_error_response` — un middleware doit s'appliquer
# [PÉDAGOGIE] AUSSI aux réponses d'erreur, sinon les incidents sont les seuls à ne pas être
# [PÉDAGOGIE] traçables.
# [PÉDAGOGIE] CONTRAT — preuve : un 401 porte lui aussi l'en-tête.
def test_request_id_present_on_error_response():
    """Une réponse 401 porte aussi son X-Request-ID."""
    # Aucun en-tête X-API-Key -> require_api_key lève une HTTPException 401.
    response = client.post("/predict-tabular", json={})

    assert response.status_code in (401, 422)
    uuid.UUID(response.headers["X-Request-ID"])
