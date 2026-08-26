# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_smoke_compose.py
# [PÉDAGOGIE] MODULE  — M28 — orchestration Compose et preuve de bout en bout
# [PÉDAGOGIE] RÔLE    — Prouver que la stack ORCHESTREE repond, en traversant un vrai reseau.
# [PÉDAGOGIE] THÉORIE — un smoke test ne remplace pas les tests unitaires : il verifie que
# [PÉDAGOGIE]           l'assemblage tient debout
# [PÉDAGOGIE]           • TestClient teste le code Python ; ici on teste l'IMAGE, le PORT,
# [PÉDAGOGIE]             les VARIABLES D'ENVIRONNEMENT et les VOLUMES
# [PÉDAGOGIE]           • un test reseau doit ATTENDRE la readiness, jamais la supposer
# [PÉDAGOGIE] À VOIR  — La fixture `stack_prete` interroge /ready en boucle avant tout test.
# [PÉDAGOGIE] PIÈGE   — `docker compose up -d` rend la main des que les conteneurs sont CREES,
# [PÉDAGOGIE]           pas quand l'API repond. Interroger tout de suite = test instable.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_smoke_compose.py
# RÔLE    : la seule preuve qui traverse le reseau.
# -----------------------------------------------------------------------------
# PREREQUIS :
#     docker compose up -d --build
#     uv run pytest tests/test_smoke_compose.py -q
#     docker compose down
#
# Si la stack n'est pas demarree, les tests sont IGNORES (skip), pas en echec :
# `uv run pytest -q` doit rester vert sur un poste sans Docker.
#
# CE QUE CE FICHIER ATTRAPE, ET QUE LES AUTRES NE VOIENT PAS :
#   - un `--host 0.0.0.0` oublie dans le CMD (l'API n'ecoute que sur localhost
#     DANS le conteneur, donc injoignable depuis l'hote)
#   - un mapping de ports absent ou errone dans docker-compose.yml
#   - INDUSENSE_API_KEY non transmise au conteneur
#   - le modele absent de l'image (variante A) ou le volume mal monte (B)
#   - un depends_on sans condition: service_healthy
# =============================================================================

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

# [PÉDAGOGIE] CONSTANTE / CONTRAT — l'URL est surchargeable : le meme test sert en local et en CI.
BASE_URL = os.getenv("INDUSENSE_SMOKE_URL", "http://127.0.0.1:8000")

# [PÉDAGOGIE] CONSTANTE / CONTRAT — la cle DOIT etre celle passee au conteneur par le .env.
# [PÉDAGOGIE] Si elles divergent, le test 200 echoue : c'est voulu, l'ecart est un vrai defaut.
API_KEY = os.getenv("INDUSENSE_API_KEY", "dev-key")

# [PÉDAGOGIE] CONSTANTE / CONTRAT — delai maximal d'attente de la readiness. Genereux au premier
# [PÉDAGOGIE] demarrage : Postgres s'initialise, puis l'API charge le modele.
DELAI_READINESS_S = 90
INTERVALLE_S = 2

PAYLOAD_PATH = Path(__file__).resolve().parents[1] / "payload.json"


def _payload() -> dict:
    """Charge le corps de requete de reference.

    On relit `payload.json` plutot que de dupliquer les 8 releves ici : une
    seule source de verite, partagee avec la demonstration manuelle en curl.
    """
    return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))


# =============================================================================
# FIXTURE — attendre la readiness, ne jamais la supposer
# =============================================================================


# [PÉDAGOGIE] BLOC `stack_prete` — portee `session` : l'attente est faite UNE fois pour tous
# [PÉDAGOGIE] les tests du fichier, pas a chaque test.
@pytest.fixture(scope="session")
def stack_prete() -> str:
    """Attend que /ready reponde 200, ou ignore les tests si la stack est absente.

    Trois issues distinctes, a ne pas confondre :

      * connexion refusee tout du long -> la stack n'est pas demarree : SKIP.
        Ce n'est pas un echec du code, c'est une absence de prerequis.
      * /ready repond 503 jusqu'au bout -> la stack tourne mais le modele n'est
        pas charge : ECHEC. Le probleme est reel.
      * /ready repond 200 -> on peut tester.
    """
    # Sonde RAPIDE d'abord : si rien n'ecoute sur le port, inutile d'attendre
    # 90 s. On distingue « stack absente » (skip immediat) de « stack en cours
    # de demarrage » (attente justifiee). Sans cela, `uv run pytest -q` sur un
    # poste sans Docker perdrait une minute et demie a chaque execution.
    try:
        httpx.get(f"{BASE_URL}/health", timeout=1.0)
    except httpx.RequestError:
        pytest.skip(
            f"Stack injoignable sur {BASE_URL}. Lancer d'abord : docker compose up -d --build"
        )

    limite = time.monotonic() + DELAI_READINESS_S
    jamais_joignable = True
    dernier_code = None

    while time.monotonic() < limite:
        try:
            reponse = httpx.get(f"{BASE_URL}/ready", timeout=5.0)
            jamais_joignable = False
            dernier_code = reponse.status_code
            if reponse.status_code == 200:
                return BASE_URL
        except httpx.RequestError:
            # Connexion refusee : le conteneur n'ecoute pas encore. Normal
            # pendant les premieres secondes, anormal au bout de 90 s.
            pass
        time.sleep(INTERVALLE_S)

    if jamais_joignable:
        pytest.skip(
            f"Stack injoignable sur {BASE_URL}. Lancer d'abord : docker compose up -d --build"
        )

    # La stack repond mais n'est jamais prete : c'est un vrai probleme.
    pytest.fail(
        f"/ready n'a jamais renvoye 200 en {DELAI_READINESS_S} s "
        f"(dernier code : {dernier_code}). Modele absent de l'image ou volume mal monte ?"
    )
    raise AssertionError("unreachable")  # pragma: no cover


@pytest.fixture(scope="session")
def routes_publiees(stack_prete: str) -> set[str]:
    """Routes REELLEMENT exposees par le service en cours d'execution.

    Un smoke test interroge un conteneur, pas le depot. L'image peut avoir ete
    construite depuis un code anterieur, ou l'apprenant peut etre sur un jalon
    ou la route n'existe pas encore. On lit donc le contrat publie plutot que
    de supposer ce que le service expose.
    """
    return set(httpx.get(f"{stack_prete}/openapi.json", timeout=10.0).json()["paths"])


@pytest.fixture
def route_image(routes_publiees: set[str]) -> str:
    """Ignore le test si /predict-image n'est pas exposee par CE service."""
    if "/predict-image" not in routes_publiees:
        pytest.skip(
            "/predict-image absente du contrat publie. "
            "Image construite depuis un code anterieur ? "
            "Relancer docker compose up -d --build"
        )
    return "/predict-image"


@pytest.fixture(scope="session")
def client(stack_prete: str):
    """Client HTTP reel, partage par les tests du fichier."""
    with httpx.Client(base_url=stack_prete, timeout=30.0) as session:
        yield session


# =============================================================================
# LES SONDES — liveness et readiness
# =============================================================================


# [PÉDAGOGIE] BLOC — /health : le process vit-il ? Ne depend d'aucune dependance externe.
@pytest.mark.smoke
def test_health_repond_200(client):
    """/health renvoie 200 : le conteneur tourne et le port est publie."""
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json()["status"] == "ok"


# [PÉDAGOGIE] BLOC — /ready : le service peut-il SERVIR ? Depend du modele.
@pytest.mark.smoke
def test_ready_repond_200(client):
    """/ready renvoie 200 : le modele est charge DANS le conteneur.

    C'est la preuve que le modele a bien suivi l'image (variante A) ou que le
    volume est correctement monte (variante B). Un 503 ici signifie que
    l'application est joignable mais inutilisable.
    """
    reponse = client.get("/ready")

    assert reponse.status_code == 200
    assert reponse.json()["status"] == "ready"


# [PÉDAGOGIE] BLOC — l'en-tete de correlation traverse le reseau reel, pas seulement TestClient.
@pytest.mark.smoke
def test_request_id_traverse_le_reseau(client):
    """X-Request-ID est present sur une reponse servie par le conteneur."""
    reponse = client.get("/health", headers={"X-Request-ID": "smoke-001"})

    assert reponse.headers["X-Request-ID"] == "smoke-001"


# =============================================================================
# LE CONTRAT D'AUTHENTIFICATION — il doit survivre a la conteneurisation
# =============================================================================


# [PÉDAGOGIE] BLOC — sans cle : 401. Le durcissement du M26 tient dans le conteneur.
@pytest.mark.smoke
def test_predict_sans_cle_repond_401(client):
    """Une prediction sans X-API-Key est refusee : 401 Unauthorized.

    401 = « je ne sais pas qui tu es ». A ne pas confondre avec 405, qui
    signale un mauvais VERBE HTTP (voir le test suivant).
    """
    reponse = client.post("/predict-tabular", json=_payload())

    assert reponse.status_code == 401


# [PÉDAGOGIE] BLOC — le piege de vocabulaire : 405 n'a rien a voir avec l'authentification.
@pytest.mark.smoke
def test_get_sur_route_post_repond_405(client):
    """Un GET sur /predict-tabular renvoie 405 : mauvaise METHODE, pas mauvaise cle.

    Ce test existe pour distinguer deux codes souvent confondus :
      401 -> tu n'es pas authentifie
      405 -> cette route n'accepte pas ce verbe HTTP
    Le 405 est produit par le routeur AVANT toute verification de cle : il
    apparait meme avec une cle valide.
    """
    reponse = client.get("/predict-tabular", headers={"X-API-Key": API_KEY})

    assert reponse.status_code == 405


# [PÉDAGOGIE] BLOC — avec la bonne cle : 200 et une prediction exploitable.
@pytest.mark.smoke
def test_predict_avec_cle_repond_200(client):
    """Une prediction authentifiee renvoie 200 et un corps conforme au schema.

    Ce test prouve trois choses d'un coup :
      * INDUSENSE_API_KEY a bien ete transmise au conteneur par le .env ;
      * le modele est charge et sait predire ;
      * le contrat de reponse est respecte de bout en bout.
    """
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": API_KEY},
        json=_payload(),
    )

    assert reponse.status_code == 200, reponse.text

    corps = reponse.json()
    assert corps["machine_id"] == "MACH-07"
    # Champs de PredictionResponse (src/indusense/api/schemas.py) :
    #   machine_id, proba_panne, decision, model_version, threshold
    assert 0.0 <= corps["proba_panne"] <= 1.0
    assert corps["decision"] in {"alerte", "ok"}
    assert corps["model_version"]
    assert 0.0 <= corps["threshold"] <= 1.0


# [PÉDAGOGIE] BLOC — une cle FAUSSE doit etre refusee comme une cle absente.
@pytest.mark.smoke
def test_predict_avec_mauvaise_cle_repond_401(client):
    """Une cle incorrecte renvoie 401, pas 403 ni 500."""
    reponse = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "cle-invalide"},
        json=_payload(),
    )

    assert reponse.status_code == 401


# =============================================================================
# COHERENCE DU RESULTAT — la prediction doit se tenir, pas seulement repondre
# =============================================================================


# [PÉDAGOGIE] BLOC — un 200 ne suffit pas : le contenu doit etre coherent avec lui-meme.
@pytest.mark.smoke
def test_predict_decision_coherente_avec_le_seuil(client):
    """`decision` doit decouler de la comparaison proba_panne / threshold.

    Le smoke test ne prejuge pas de la VALEUR de la probabilite — elle depend
    du modele entraine. Il verifie l'INVARIANT : "alerte" si et seulement si la
    probabilite atteint le seuil. Une incoherence signalerait un seuil applique
    dans le conteneur different de celui renvoye au client.
    """
    corps = client.post(
        "/predict-tabular",
        headers={"X-API-Key": API_KEY},
        json=_payload(),
    ).json()

    alerte_attendue = corps["proba_panne"] >= corps["threshold"]
    assert (corps["decision"] == "alerte") is alerte_attendue


# [PÉDAGOGIE] BLOC — le contrat de reponse est stable : ni champ manquant, ni champ surprise.
@pytest.mark.smoke
def test_predict_renvoie_exactement_les_champs_du_contrat(client):
    """Le corps contient les cinq champs de PredictionResponse, et rien d'autre.

    Un champ en trop signalerait une fuite d'information interne ; un champ
    manquant casserait un client qui s'appuie sur le contrat publie.
    """
    corps = client.post(
        "/predict-tabular",
        headers={"X-API-Key": API_KEY},
        json=_payload(),
    ).json()

    assert set(corps) == {
        "machine_id",
        "proba_panne",
        "decision",
        "model_version",
        "threshold",
    }


# =============================================================================
# /predict-image — l'absence d'image doit etre refusee
# =============================================================================
# NOTE : sur ce jalon, /predict-image ne charge AUCUN modele — elle valide le
# fichier recu, rien de plus. Les tests ci-dessous portent donc sur la
# validation d'entree, pas sur une inference.
# =============================================================================


# [PÉDAGOGIE] BLOC — aucun fichier transmis : Pydantic refuse avant d'entrer dans la route.
@pytest.mark.smoke
def test_predict_image_sans_fichier_repond_422(client, route_image):
    """Sans champ `file`, la validation refuse : 422 avec un detail par champ.

    Attention au vocabulaire : ce 422 vient de Pydantic (« Field required »),
    pas d'un controle metier. Son `detail` est une LISTE, contrairement aux
    refus explicites de l'application qui renvoient une chaine.
    """
    reponse = client.post(route_image, headers={"X-API-Key": API_KEY})

    assert reponse.status_code == 422
    assert isinstance(reponse.json()["detail"], list)


# [PÉDAGOGIE] BLOC — fichier present mais VIDE : refus metier, detail textuel.
@pytest.mark.smoke
def test_predict_image_fichier_vide_repond_422(client, route_image):
    """Un fichier de zero octet est refuse par la route elle-meme."""
    reponse = client.post(
        route_image,
        headers={"X-API-Key": API_KEY},
        files={"file": ("vide.png", b"", "image/png")},
    )

    assert reponse.status_code == 422
    assert isinstance(reponse.json()["detail"], str)


# [PÉDAGOGIE] BLOC — le contenu n'est pas une image : refus, meme si le nom finit en .png.
@pytest.mark.smoke
def test_predict_image_contenu_non_image_repond_422(client, route_image):
    """Un fichier texte est refuse, quel que soit son nom."""
    reponse = client.post(
        route_image,
        headers={"X-API-Key": API_KEY},
        files={"file": ("faux.png", b"ceci n'est pas une image", "text/plain")},
    )

    assert reponse.status_code == 422


# [PÉDAGOGIE] BLOC — la route reste protegee : l'authentification passe AVANT la validation.
@pytest.mark.smoke
def test_predict_image_sans_cle_repond_401(client, route_image):
    """Sans cle, on obtient 401 — pas 422. L'ordre des controles compte."""
    reponse = client.post(
        route_image,
        files={"file": ("vide.png", b"", "image/png")},
    )

    assert reponse.status_code == 401


# =============================================================================
# LES AUTRES COMPOSANTS DE LA STACK
# =============================================================================
# Chaque service est teste INDEPENDAMMENT, avec un skip si son port n'est pas
# publie. Un poste qui ne lance que l'API doit pouvoir passer le reste du
# fichier : c'est le mode « rattrapage » prevu par la fiche du jalon.
# =============================================================================

URL_PROMETHEUS = os.getenv("INDUSENSE_PROMETHEUS_URL", "http://127.0.0.1:9090")
URL_GRAFANA = os.getenv("INDUSENSE_GRAFANA_URL", "http://127.0.0.1:3000")


def _sonder(url: str, chemin: str, nom: str) -> httpx.Response:
    """Interroge un service, ou ignore le test s'il n'est pas joignable."""
    try:
        return httpx.get(f"{url}{chemin}", timeout=5.0)
    except httpx.RequestError:
        pytest.skip(f"{nom} injoignable sur {url} — service non demarre ?")


# [PÉDAGOGIE] BLOC — Prometheus expose sa propre sonde de sante sur /-/healthy.
@pytest.mark.smoke
def test_prometheus_est_sain():
    """Prometheus repond 200 sur /-/healthy."""
    reponse = _sonder(URL_PROMETHEUS, "/-/healthy", "Prometheus")

    assert reponse.status_code == 200


# [PÉDAGOGIE] CONSTANTE / CONTRAT — job attendu « up ». Les autres jobs de prometheus.yml
# [PÉDAGOGIE] (ex. indusense-drift) ciblent des exporters qui arrivent plus tard dans le
# [PÉDAGOGIE] parcours : leur etat « down » est NORMAL et ne doit pas faire echouer ce test.
JOB_API = os.getenv("INDUSENSE_PROMETHEUS_JOB", "indusense-api")


# [PÉDAGOGIE] BLOC — la vraie preuve du monitoring : Prometheus VOIT-IL l'API ?
@pytest.mark.smoke
def test_prometheus_scrape_bien_l_api():
    """La cible `indusense-api` est en etat `up` dans Prometheus.

    Un Prometheus sain qui ne scrape rien ne sert a rien. Ce test verifie le
    LIEN entre les services. On ne regarde QUE le job de l'API : les autres
    cibles peuvent legitimement etre absentes a ce stade du parcours.

    On tolere l'attente : le premier scrape n'a pas lieu instantanement.
    """
    limite = time.monotonic() + 30
    etats: dict[str, str] = {}

    while time.monotonic() < limite:
        reponse = _sonder(URL_PROMETHEUS, "/api/v1/targets", "Prometheus")
        cibles = reponse.json()["data"]["activeTargets"]
        etats = {cible["labels"].get("job"): cible["health"] for cible in cibles}
        if etats.get(JOB_API) == "up":
            return
        time.sleep(INTERVALLE_S)

    if JOB_API not in etats:
        pytest.fail(
            f"Job '{JOB_API}' absent de Prometheus. Jobs vus : {sorted(etats)}. "
            "Verifier scrape_configs dans monitoring/prometheus.yml."
        )

    # Diagnostic : on interroge /metrics nous-memes pour dire POURQUOI ca echoue.
    # Cas le plus frequent : un 401. Si /metrics a ete protege par une cle API
    # (controle M26), Prometheus ne peut plus scraper sans authentification.
    indice = ""
    try:
        sonde = httpx.get(f"{BASE_URL}/metrics", timeout=5.0)
        if sonde.status_code == 401:
            indice = (
                " — /metrics repond 401 : l'endpoint est protege par une cle API, "
                "mais prometheus.yml ne l'envoie pas. Ajouter `authorization` dans "
                "le scrape_config, ou exposer /metrics sur un port interne."
            )
        else:
            indice = f" — /metrics repond {sonde.status_code} depuis l'hote."
    except httpx.RequestError:
        indice = " — /metrics injoignable depuis l'hote."

    pytest.fail(f"Cible '{JOB_API}' en etat '{etats[JOB_API]}' apres 30 s{indice}")


# [PÉDAGOGIE] BLOC — Grafana : /api/health ne demande PAS d'authentification.
@pytest.mark.smoke
def test_grafana_est_sain():
    """Grafana repond 200 sur /api/health, avec sa base en etat `ok`."""
    reponse = _sonder(URL_GRAFANA, "/api/health", "Grafana")

    assert reponse.status_code == 200
    assert reponse.json()["database"] == "ok"


# [PÉDAGOGIE] BLOC — Postgres n'a pas d'interface HTTP. On lit l'etat que DOCKER connait.
@pytest.mark.smoke
def test_tous_les_services_compose_sont_sains():
    """Aucun service Compose n'est arrete ou en etat `unhealthy`.

    Postgres n'expose pas de port HTTP : impossible de le sonder comme les
    autres. On interroge donc Docker lui-meme, seule source qui connaisse le
    resultat des healthcheck declares dans docker-compose.yml.
    """
    try:
        resultat = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("docker compose indisponible ou stack non demarree")

    # `docker compose ps --format json` produit un objet JSON PAR LIGNE
    # (JSON Lines), pas un tableau : un json.loads sur tout le flux echouerait.
    services = [json.loads(ligne) for ligne in resultat.stdout.splitlines() if ligne.strip()]
    if not services:
        pytest.skip("aucun service Compose en cours d'execution")

    defaillants = [
        f"{service['Service']} ({service.get('Health') or service['State']})"
        for service in services
        if service["State"] != "running" or service.get("Health") not in (None, "", "healthy")
    ]

    assert not defaillants, "services non sains : " + ", ".join(defaillants)
