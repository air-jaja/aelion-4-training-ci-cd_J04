# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_security_controls.py
# [PÉDAGOGIE] MODULE  — M26 — durcissement de l'API et modele de menaces
# [PÉDAGOGIE] RÔLE    — Transformer les 5 controles priorises du threat model en preuves
# [PÉDAGOGIE]           executables, AVANT de les implementer.
# [PÉDAGOGIE] THÉORIE — Un controle non teste n'est pas un controle : c'est une intention
# [PÉDAGOGIE]           • ecrire le test en premier fige le contrat attendu
# [PÉDAGOGIE]           • un test rouge decrit precisement ce qui manque
# [PÉDAGOGIE] À VOIR  — Lancer ce fichier AVANT toute modification : les 5 groupes echouent.
# [PÉDAGOGIE] PIÈGE   — Un test qui passe des le depart ne prouve rien ; verifier le rouge.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_security_controls.py
# RÔLE    : les 5 controles priorises dans docs/threat_model.md.
# -----------------------------------------------------------------------------
# MODE D'EMPLOI (cycle rouge -> vert) :
#
#   1. uv run pytest tests/test_security_controls.py -q
#      -> 5 groupes en echec. C'est NORMAL et c'est le point de depart.
#
#   2. Implementer un controle a la fois, dans l'ordre de priorite du
#      threat model.
#
#   3. Relancer apres chaque controle : un groupe passe au vert.
#
# POURQUOI CET ORDRE : le threat model classe par (probabilite x impact) /
# cout. On traite d'abord ce qui ouvre le service en grand pour trois lignes
# de correction.
#
# CE FICHIER NE REMPLACE PAS tests/test_security.py : celui-ci couvre les
# controles DEJA en place (413, 400, 429, signature). Ici, on couvre ce qui
# MANQUE.
# =============================================================================

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from indusense.api import security
from indusense.api.main import app

client = TestClient(app)


# =============================================================================
# CONTROLE 1 — Interdire la cle API par defaut en production          [STRIDE: S]
# -----------------------------------------------------------------------------
# MENACE : config.py fixe `api_key = "dev-key"`. Cette valeur est ecrite dans
# le depot, donc connue de tous. Un oubli de .env en production laisse le
# service ouvert, SANS AUCUN SIGNAL.
#
# CONTRAT ATTENDU : refuser le demarrage si la cle vaut le defaut alors que
# l'environnement declare est « production ».
# =============================================================================


# [PÉDAGOGIE] BLOC — ce test transforme une exigence de configuration en preuve.
def test_default_api_key_rejected_in_production():
    """Demarrer en production avec la cle par defaut doit echouer."""
    from indusense.config import Settings

    # pydantic doit refuser cette combinaison. Sans le controle, l'objet se
    # construit sans broncher : c'est exactement le probleme.
    with pytest.raises(ValueError):
        Settings(environment="production", api_key="dev-key")


# [PÉDAGOGIE] BLOC — le cas symetrique : ne pas casser le poste de formation.
def test_default_api_key_allowed_in_dev():
    """En dev, la cle par defaut reste acceptee : la salle doit pouvoir travailler."""
    from indusense.config import Settings

    settings = Settings(environment="dev", api_key="dev-key")
    assert settings.api_key == "dev-key"


# [PÉDAGOGIE] BLOC — une vraie cle passe quel que soit l'environnement.
def test_real_api_key_accepted_in_production():
    """Une cle explicite est acceptee en production."""
    from indusense.config import Settings

    settings = Settings(environment="production", api_key="une-vraie-cle-longue")
    assert settings.api_key == "une-vraie-cle-longue"


# =============================================================================
# CONTROLE 2 — Verifier l'integrite du modele avant chargement        [STRIDE: T]
# -----------------------------------------------------------------------------
# MENACE : joblib.load deserialise du PICKLE. Lire un fichier revient a
# EXECUTER DU CODE. Quiconque ecrit dans artifacts/models/ obtient l'execution
# arbitraire dans le process de l'API.
#
# CONTRAT ATTENDU : model_metadata.json porte l'empreinte SHA-256 attendue.
# load_bundle compare avant de charger, et refuse en cas d'ecart.
# =============================================================================


def _ecrire_faux_modele(dossier, contenu: bytes, sha256: str | None):
    """Fabrique un dossier de modele minimal, avec ou sans empreinte."""
    (dossier / "rf.joblib").write_bytes(contenu)
    meta = {"package_version": "0.1.0", "target_col": "panne"}
    if sha256 is not None:
        meta["rf_sha256"] = sha256
    (dossier / "model_metadata.json").write_text(json.dumps(meta))


# [PÉDAGOGIE] BLOC — le cas nominal : empreinte correcte, chargement autorise.
def test_bundle_loads_when_hash_matches(tmp_path):
    """Une empreinte conforme laisse passer le chargement."""
    from indusense.api import model_store

    contenu = b"faux-modele-pour-le-test"
    _ecrire_faux_modele(tmp_path, contenu, hashlib.sha256(contenu).hexdigest())

    # On remplace le vrai chargeur : ici on teste l'INTEGRITE, pas joblib.
    model_store.verify_artifact(tmp_path / "rf.joblib", hashlib.sha256(contenu).hexdigest())


# [PÉDAGOGIE] BLOC — le cas d'attaque : le fichier a ete remplace.
def test_bundle_refuses_tampered_model(tmp_path):
    """Un modele modifie apres coup doit etre refuse, pas charge."""
    from indusense.api.model_store import ModelIntegrityError, load_bundle

    contenu = b"modele-legitime"
    _ecrire_faux_modele(tmp_path, contenu, hashlib.sha256(contenu).hexdigest())

    # L'attaquant remplace le binaire SANS toucher aux metadonnees.
    (tmp_path / "rf.joblib").write_bytes(b"modele-malveillant")

    with pytest.raises(ModelIntegrityError):
        load_bundle(tmp_path, threshold=0.5)


# [PÉDAGOGIE] BLOC — absence d'empreinte = refus, pas tolerance silencieuse.
def test_bundle_refuses_missing_hash(tmp_path, monkeypatch):
    """Sans empreinte declaree, on refuse : l'absence de preuve n'est pas une preuve."""
    from indusense.api import model_store
    from indusense.api.model_store import ModelIntegrityError, load_bundle

    # Le test fixe le reglage lui-meme : il ne doit pas dependre du .env local.
    monkeypatch.setattr(model_store.settings, "require_model_hash", True)

    _ecrire_faux_modele(tmp_path, b"modele-sans-empreinte", sha256=None)

    with pytest.raises(ModelIntegrityError):
        load_bundle(tmp_path, threshold=0.5)


# =============================================================================
# CONTROLE 3 — Rate limit effectif derriere un reverse proxy          [STRIDE: D]
# -----------------------------------------------------------------------------
# MENACE : en deploiement reel, request.client.host vaut l'IP DU PROXY, pas
# celle du client. Consequence : soit tous les clients partagent un seul seau
# de 60 req/min, soit le premier flood bloque tout le monde.
#
# CONTRAT ATTENDU : si l'appel vient d'un proxy de confiance, lire
# X-Forwarded-For. Sinon, l'IGNORER (sans quoi n'importe qui le forge).
# =============================================================================


class _FauxClient:
    def __init__(self, host):
        self.host = host


class _FauxRequete:
    """Objet minimal imitant une Request : juste .client et .headers."""

    def __init__(self, host, headers=None):
        self.client = _FauxClient(host)
        self.headers = headers or {}


# [PÉDAGOGIE] BLOC — deux clients derriere le meme proxy ne doivent pas se genrer.
def test_clients_behind_trusted_proxy_get_distinct_buckets():
    """Derriere un proxy de confiance, chaque client reel a son propre compteur."""
    identite = security.client_identity

    proxy = "10.0.0.1"
    requete_a = _FauxRequete(proxy, {"x-forwarded-for": "203.0.113.7"})
    requete_b = _FauxRequete(proxy, {"x-forwarded-for": "203.0.113.8"})

    assert identite(requete_a, trusted_proxies={proxy}) == "203.0.113.7"
    assert identite(requete_b, trusted_proxies={proxy}) == "203.0.113.8"


# [PÉDAGOGIE] BLOC — le piege : un en-tete forge depuis une source non listee.
def test_forged_forwarded_header_is_ignored():
    """Un X-Forwarded-For envoye directement par un client est ignore."""
    identite = security.client_identity

    # 198.51.100.9 n'est PAS un proxy de confiance : il se declare
    # « 203.0.113.7 » pour obtenir un seau neuf a chaque appel.
    requete = _FauxRequete("198.51.100.9", {"x-forwarded-for": "203.0.113.7"})

    assert identite(requete, trusted_proxies={"10.0.0.1"}) == "198.51.100.9"


# [PÉDAGOGIE] BLOC — sans proxy declare, comportement inchange.
def test_direct_client_uses_socket_address():
    """Sans liste de proxys, on retombe sur l'adresse du socket."""
    requete = _FauxRequete("203.0.113.42")

    assert security.client_identity(requete, trusted_proxies=set()) == "203.0.113.42"


# [PÉDAGOGIE] BLOC — le rate limit consomme bien cette identite, pas l'IP brute.
def test_rate_limit_uses_client_identity():
    """Deux clients derriere le meme proxy ne partagent pas leur quota."""
    security._hits.clear()
    proxy = "10.0.0.1"

    requete_a = _FauxRequete(proxy, {"x-forwarded-for": "203.0.113.7"})
    requete_b = _FauxRequete(proxy, {"x-forwarded-for": "203.0.113.8"})

    for _ in range(60):
        security.rate_limit(requete_a, limit=60, window=60.0, trusted_proxies={proxy})

    # Le client B n'a rien consomme : il doit passer sans erreur.
    security.rate_limit(requete_b, limit=60, window=60.0, trusted_proxies={proxy})


# =============================================================================
# CONTROLE 4 — Journaliser les refus                                  [STRIDE: R]
# -----------------------------------------------------------------------------
# MENACE : sans trace des 401, 413 et 429, une campagne de reconnaissance est
# INVISIBLE. Le request_id existe deja ; il manque l'evenement.
#
# CONTRAT ATTENDU : chaque refus produit une ligne de log contenant le code, la
# route et le request_id — et JAMAIS la cle soumise.
# =============================================================================


@pytest.fixture
def journal():
    """Capture les lignes de log emises pendant le test."""
    lignes = []
    identifiant = logger.add(lignes.append, level="WARNING", format="{message} {extra}")
    yield lignes
    logger.remove(identifiant)


# [PÉDAGOGIE] BLOC — un refus doit laisser une trace exploitable.
def test_refusal_is_logged_with_context(journal):
    """Un 401 produit un log portant le code et la route."""
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "mauvaise-cle", "X-Request-ID": "trace-001"},
        json={"machine_id": "MACH-01", "readings": []},
    )
    assert reponse.status_code in (401, 422)

    trace = " ".join(journal)
    assert "401" in trace or "422" in trace
    assert "/predict-tabular" in trace


# [PÉDAGOGIE] BLOC — le piege classique : journaliser le secret qu'on protege.
def test_submitted_key_never_appears_in_logs(journal):
    """La cle soumise ne doit JAMAIS apparaitre dans les logs."""
    client.post(
        "/predict-tabular",
        headers={"X-API-Key": "SECRET-A-NE-PAS-LOGUER", "X-Request-ID": "trace-002"},
        json={"machine_id": "MACH-01", "readings": []},
    )

    trace = " ".join(journal)
    assert "SECRET-A-NE-PAS-LOGUER" not in trace


# [PÉDAGOGIE] BLOC — la correlation doit etre possible.
def test_request_id_present_in_refusal_log(journal):
    """Le request_id fourni par le client se retrouve dans la trace."""
    client.post(
        "/predict-tabular",
        headers={"X-API-Key": "mauvaise-cle", "X-Request-ID": "trace-003"},
        json={"machine_id": "MACH-01", "readings": []},
    )

    assert "trace-003" in " ".join(journal)


# =============================================================================
# CONTROLE 5 — Fermer /metrics                                        [STRIDE: I]
# -----------------------------------------------------------------------------
# MENACE : include_in_schema=False retire l'endpoint de Swagger, PAS du reseau.
# Un GET /metrics anonyme donne la volumetrie, les latences et la liste des
# routes, y compris celles qui ne sont pas documentees.
#
# CONTRAT ATTENDU : /metrics exige la cle API.
# =============================================================================


# [PÉDAGOGIE] BLOC — l'acces anonyme doit etre refuse.
def test_metrics_requires_api_key():
    """GET /metrics sans cle renvoie 401."""
    assert client.get("/metrics").status_code == 401


# [PÉDAGOGIE] BLOC — avec la cle, l'exploitation garde son acces.
def test_metrics_accessible_with_api_key():
    """GET /metrics avec la bonne cle renvoie 200."""
    reponse = client.get("/metrics", headers={"X-API-Key": "dev-key"})

    assert reponse.status_code == 200
    assert "python_info" in reponse.text or "http_request" in reponse.text


# [PÉDAGOGIE] BLOC — masquer de la doc n'est pas proteger.
def test_metrics_absent_from_openapi():
    """/metrics reste hors du contrat publie : discretion ET authentification."""
    assert "/metrics" not in app.openapi()["paths"]
