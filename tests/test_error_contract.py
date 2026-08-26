# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_error_contract.py
# [PÉDAGOGIE] MODULE  — M26 — contrat d'erreur publie
# [PÉDAGOGIE] RÔLE    — Verifier que la DOC et le CODE disent la meme chose sur les erreurs.
# [PÉDAGOGIE] THÉORIE — Un code produit mais non documente est une surprise en production
# [PÉDAGOGIE]           • un code documente mais jamais produit est un mensonge
# [PÉDAGOGIE]           • les deux sens doivent etre testes
# [PÉDAGOGIE] À VOIR  — /docs affiche 400, 401, 413, 422, 429 et 503 sur /predict-tabular.
# [PÉDAGOGIE] PIÈGE   — Se contenter de tester la doc : elle pourrait decrire un comportement
# [PÉDAGOGIE]           que le code n'a pas. D'ou les tests d'aller-retour ci-dessous.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_error_contract.py
# RÔLE    : le contrat d'erreur, dans les deux sens.
# -----------------------------------------------------------------------------
# SENS 1 — DOC -> CODE : chaque code annonce dans OpenAPI doit etre produit.
# SENS 2 — CODE -> DOC : chaque code produit doit etre annonce.
#
# Un test qui ne verifie qu'un seul sens laisse passer la moitie des ecarts.
# =============================================================================

import pytest
from fastapi.testclient import TestClient

from indusense.api import security
from indusense.api.errors import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from indusense.api.main import app

client = TestClient(app)

# Codes que /predict-tabular doit annoncer dans son contrat.
CODES_ATTENDUS = {"200", "400", "401", "413", "422", "429", "503"}


# =============================================================================
# SENS 1 — Ce que la documentation annonce
# =============================================================================


# [PÉDAGOGIE] BLOC — le contrat publie doit couvrir tous les refus possibles.
def test_prediction_route_documents_all_error_codes():
    """Les six codes d'erreur de /predict-tabular sont publies."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]

    assert set(operation["responses"]) == CODES_ATTENDUS


# [PÉDAGOGIE] BLOC — une description vide n'aide personne.
def test_error_descriptions_are_not_placeholders():
    """Chaque code documente porte une description utile."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]

    for code in ("400", "401", "413", "429", "503"):
        description = operation["responses"][code]["description"]
        assert len(description) > 30, f"Description trop courte pour {code}"


# [PÉDAGOGIE] BLOC — la politique de debit doit etre lisible dans la doc, pas
# [PÉDAGOGIE] seulement dans le code.
def test_rate_limit_policy_is_published():
    """La politique 60/60 s figure dans la description du 429."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]
    description = operation["responses"]["429"]["description"]

    assert str(RATE_LIMIT_PER_MINUTE) in description
    assert str(RATE_LIMIT_WINDOW_SECONDS) in description


# [PÉDAGOGIE] BLOC — la limite de taille doit etre chiffree dans la doc.
def test_body_size_limit_is_published():
    """La limite de 64 Ko figure dans la description du 413."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]

    assert "64" in operation["responses"]["413"]["description"]


# [PÉDAGOGIE] BLOC — l'en-tete de correlation est annonce sur chaque erreur.
def test_request_id_header_is_documented_on_errors():
    """X-Request-ID est declare sur les reponses d'erreur."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]

    for code in ("400", "401", "413", "422", "429", "503"):
        headers = operation["responses"][code].get("headers", {})
        assert "X-Request-ID" in headers, f"En-tete non documente sur {code}"


# [PÉDAGOGIE] BLOC — Retry-After n'a de sens que sur le 429.
def test_retry_after_documented_only_on_429():
    """Retry-After est annonce sur le 429, et nulle part ailleurs."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]

    assert "Retry-After" in operation["responses"]["429"]["headers"]
    assert "Retry-After" not in operation["responses"]["401"].get("headers", {})


# [PÉDAGOGIE] BLOC — /ready ne publie que ce qui la concerne.
def test_ready_documents_only_service_unavailable():
    """/ready annonce 503, sans les codes lies a l'authentification."""
    responses = app.openapi()["paths"]["/ready"]["get"]["responses"]

    assert "503" in responses
    assert "401" not in responses


# =============================================================================
# SENS 2 — Ce que le code produit reellement
# =============================================================================


# [PÉDAGOGIE] BLOC — 400 : Content-Length illisible.
def test_invalid_content_length_matches_documented_shape():
    """Le 400 renvoie bien la forme annoncee."""
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key", "Content-Length": "pas-un-entier"},
        content=b"{}",
    )

    assert reponse.status_code == 400
    assert isinstance(reponse.json()["detail"], str)


# [PÉDAGOGIE] BLOC — 401 : cle absente.
def test_unauthorized_matches_documented_shape():
    """Le 401 renvoie un detail textuel, comme annonce."""
    reponse = client.post("/predict-tabular", json={})

    assert reponse.status_code == 401
    assert isinstance(reponse.json()["detail"], str)


# [PÉDAGOGIE] BLOC — 413 : corps trop volumineux.
def test_payload_too_large_matches_documented_shape():
    """Le 413 se declenche au-dela de la limite publiee."""
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key"},
        content=b"x" * (security.MAX_BODY_BYTES + 1),
    )

    assert reponse.status_code == 413
    assert isinstance(reponse.json()["detail"], str)


# [PÉDAGOGIE] BLOC — 422 : forme DIFFERENTE, et c'est voulu.
def test_validation_error_returns_list_of_details():
    """Le 422 de Pydantic renvoie une LISTE, pas une chaine.

    C'est la seule reponse d'erreur qui ne suit pas ErrorResponse : elle
    enumere chaque champ fautif. On ne cherche pas a l'uniformiser.
    """
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key"},
        json={"machine_id": "MACH-01", "readings": []},
    )

    assert reponse.status_code == 422
    assert isinstance(reponse.json()["detail"], list)


# [PÉDAGOGIE] BLOC — 429 : le Retry-After annonce doit etre EMIS.
def test_rate_limit_emits_retry_after_header():
    """Le 429 porte l'en-tete Retry-After documente."""
    from fastapi import HTTPException

    security._hits.clear()

    class _Client:
        host = "198.51.100.77"

    class _Req:
        client = _Client()
        headers: dict = {}

    requete = _Req()
    for _ in range(RATE_LIMIT_PER_MINUTE):
        security.rate_limit(requete, limit=RATE_LIMIT_PER_MINUTE, window=60.0)

    with pytest.raises(HTTPException) as capture:
        security.rate_limit(requete, limit=RATE_LIMIT_PER_MINUTE, window=60.0)

    assert capture.value.status_code == 429
    assert capture.value.headers["Retry-After"] == "60"


# [PÉDAGOGIE] BLOC — toute erreur reste correlable.
def test_every_error_carries_request_id():
    """400, 401, 413 et 422 portent tous X-Request-ID."""
    appels = [
        client.post("/predict-tabular", json={}),
        client.post(
            "/predict-tabular",
            headers={"X-API-Key": "dev-key", "Content-Length": "abc"},
            content=b"{}",
        ),
        client.post(
            "/predict-tabular",
            headers={"X-API-Key": "dev-key"},
            json={"machine_id": "MACH-01", "readings": []},
        ),
    ]

    for reponse in appels:
        assert "X-Request-ID" in reponse.headers, f"Manquant sur {reponse.status_code}"
