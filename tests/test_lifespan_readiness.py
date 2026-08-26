# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_lifespan_readiness.py
# [PÉDAGOGIE] MODULE  — M27 — cycle de vie de l'application et sonde de readiness
# [PÉDAGOGIE] RÔLE    — Prouver que le service DEMARRE meme sans modele, et le signale
# [PÉDAGOGIE]           par /ready plutot que par un crash.
# [PÉDAGOGIE] THÉORIE — liveness (/health) : le process vit-il ? readiness (/ready) : peut-il
# [PÉDAGOGIE]           servir du trafic ?
# [PÉDAGOGIE]           • un service qui refuse de demarrer ne peut meme pas dire POURQUOI
# [PÉDAGOGIE]           • un orchestrateur retire du trafic sur /ready, redemarre sur /health
# [PÉDAGOGIE] À VOIR  — `with TestClient(app)` declenche le lifespan ; `TestClient(app)` seul
# [PÉDAGOGIE]           ne le declenche PAS. C'est tout l'objet de ce fichier.
# [PÉDAGOGIE] PIÈGE   — Les autres tests du projet n'exercent jamais le demarrage reel : un
# [PÉDAGOGIE]           echec de lifespan passait inapercu jusqu'au lancement d'uvicorn.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_lifespan_readiness.py
# RÔLE    : le seul fichier qui exerce le DEMARRAGE de l'application.
# -----------------------------------------------------------------------------
# POURQUOI IL EXISTE :
#
# `TestClient(app)` utilise en variable globale, comme dans tous les autres
# fichiers de tests, n'execute PAS le gestionnaire `lifespan`. Le chargement du
# modele n'est donc jamais tente, et une exception au demarrage n'apparait qu'au
# lancement d'uvicorn — c'est-a-dire trop tard.
#
# Le gestionnaire de contexte `with TestClient(app) as client:` declenche le
# demarrage et l'arret. C'est la seule facon de tester ce cycle.
#
# CONTRAT VERIFIE :
#   modele chargeable    -> /health 200, /ready 200
#   modele absent        -> /health 200, /ready 503   (le service VIT, il n'est pas PRET)
#   modele non verifiable-> /health 200, /ready 503   (meme traitement)
# =============================================================================

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from indusense.api import model_store
from indusense.api.main import app
from indusense.config import settings


@pytest.fixture(autouse=True)
def bundle_propre():
    """Remet le bundle global a zero entre les tests.

    `store._BUNDLE` est un etat de module : sans ce nettoyage, un test qui
    charge un modele contaminerait le suivant.
    """
    model_store._BUNDLE = None
    yield
    model_store._BUNDLE = None


def _ecrire_modele(dossier, contenu: bytes, avec_empreinte: bool = True):
    """Fabrique un dossier de modele minimal."""
    (dossier / "rf.joblib").write_bytes(contenu)
    meta = {"package_version": "0.1.0", "target_col": "panne"}
    if avec_empreinte:
        meta["rf_sha256"] = hashlib.sha256(contenu).hexdigest()
    (dossier / "model_metadata.json").write_text(json.dumps(meta))


# =============================================================================
# Le service demarre, quoi qu'il arrive
# =============================================================================


# [PÉDAGOGIE] BLOC — LE test central : dossier vide, le service doit vivre.
def test_demarre_sans_modele_et_se_declare_non_pret(tmp_path, monkeypatch):
    """Sans modele, /health repond 200 et /ready repond 503."""
    monkeypatch.setattr(settings, "model_dir", tmp_path)

    # Le `with` declenche le lifespan : c'est ce qui distingue ce test des autres.
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


# [PÉDAGOGIE] BLOC — modele present mais SANS empreinte : meme traitement, pas de crash.
def test_demarre_sans_empreinte_et_se_declare_non_pret(tmp_path, monkeypatch):
    """Un modele non verifiable n'empeche pas le demarrage : /ready repond 503.

    C'est le cas qui faisait planter uvicorn avant correction du lifespan : la
    ModelIntegrityError remontait et tuait le process au demarrage.
    """
    monkeypatch.setattr(settings, "model_dir", tmp_path)
    # Si le mode permissif a ete ajoute au projet, on force la verification :
    # le test ne doit dependre ni du .env local ni d'un reglage d'environnement.
    # Un test qui lit un fichier non versionne n'est pas reproductible.
    if hasattr(settings, "require_model_hash"):
        monkeypatch.setattr(settings, "require_model_hash", True)
    _ecrire_modele(tmp_path, b"modele-sans-empreinte", avec_empreinte=False)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


# [PÉDAGOGIE] BLOC — modele altere : refus du chargement, mais le service reste joignable.
def test_demarre_avec_modele_altere_et_se_declare_non_pret(tmp_path, monkeypatch):
    """Un artefact dont l'empreinte ne correspond pas ne doit pas tuer le service."""
    monkeypatch.setattr(settings, "model_dir", tmp_path)
    _ecrire_modele(tmp_path, b"modele-legitime", avec_empreinte=True)
    (tmp_path / "rf.joblib").write_bytes(b"modele-remplace")

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


# =============================================================================
# La distinction liveness / readiness
# =============================================================================


# [PÉDAGOGIE] BLOC — /health ne doit JAMAIS dependre du modele : sinon l'orchestrateur
# [PÉDAGOGIE] redemarrerait en boucle un service dont le seul tort est de ne pas etre pret.
def test_health_ne_depend_pas_du_modele(tmp_path, monkeypatch):
    """/health repond 200 dans tous les cas : il mesure la vivacite du process."""
    monkeypatch.setattr(settings, "model_dir", tmp_path)

    with TestClient(app) as client:
        reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json()["status"] == "ok"


# [PÉDAGOGIE] BLOC — le 503 doit rester correlable comme toute autre erreur.
def test_le_503_porte_un_request_id(tmp_path, monkeypatch):
    """Une reponse 503 est tracable, comme les autres refus."""
    monkeypatch.setattr(settings, "model_dir", tmp_path)

    with TestClient(app) as client:
        reponse = client.get("/ready")

    assert reponse.status_code == 503
    assert "X-Request-ID" in reponse.headers


# [PÉDAGOGIE] BLOC — le contrat publie annonce bien ce 503 (lien avec errors.py).
def test_le_503_est_documente_dans_openapi():
    """/ready declare son 503 dans le contrat, pas seulement dans le code."""
    assert "503" in app.openapi()["paths"]["/ready"]["get"]["responses"]
