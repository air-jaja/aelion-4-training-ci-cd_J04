# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/api/main.py
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
#  src/indusense/api/main.py  —  L'APPLICATION FastAPI (le cœur de l'API)
# -----------------------------------------------------------------------------
#  Place dans le projet : Sprint 3, module API (n°25) + sécurité (n°26).
#
#  RÔLE DU FICHIER
#  C'est ici qu'on assemble TOUT : on crée l'application web, on charge le modèle
#  au démarrage, on branche les protections (middlewares, clé API, anti-flood),
#  l'observabilité (logs + métriques Prometheus), et on définit les « routes »
#  (les URL que les clients peuvent appeler) :
#    - GET  /health          : « le serveur est-il VIVANT ? » (liveness)
#    - GET  /ready           : « le serveur est-il PRÊT à servir ? » (readiness)
#    - POST /predict-tabular : prédiction de panne à partir de relevés capteurs
#    - POST /predict-image   : analyse d'une image (validation du fichier ici)
#    - GET  /metrics         : métriques techniques pour Prometheus (auto)
#
#  FASTAPI EN DEUX MOTS
#  Un framework web Python moderne et rapide. On y décrit chaque route avec un
#  décorateur (`@app.get(...)`, `@app.post(...)`) au-dessus d'une fonction.
#  FastAPI s'occupe de lire la requête, valider les données (avec Pydantic),
#  appeler notre fonction, et renvoyer la réponse au format JSON.
#
#  RAPPEL DES CODES HTTP UTILISÉS ICI
#    200 OK                    : tout va bien (succès par défaut).
#    401 Unauthorized          : authentification manquante/invalide (clé API).
#    413 Payload Too Large      : corps de requête trop volumineux (middleware).
#    422 Unprocessable Entity   : données comprises mais invalides (validation).
#    429 Too Many Requests      : trop de requêtes (limiteur de débit).
#    503 Service Unavailable    : service temporairement indisponible (pas de modèle).
# =============================================================================

# Annotations de type modernes (voir explication dans les autres fichiers).
# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

# `uuid` : module standard pour générer des identifiants UNIQUES et aléatoires.
# On l'utilise pour donner un identifiant à chaque requête (traçabilité des logs).
import uuid

# `asynccontextmanager` : transforme une fonction en « gestionnaire de contexte »
# asynchrone. FastAPI s'en sert pour le `lifespan` : du code à exécuter AU
# DÉMARRAGE (avant le `yield`) puis à L'ARRÊT (après le `yield`) de l'application.
from contextlib import asynccontextmanager

# `pandas` (alias `pd`) : la bibliothèque reine pour manipuler des tableaux de
# données (« DataFrame »). On construit un DataFrame à partir des relevés reçus,
# puis on calcule dessus les features temporelles avant de prédire.
import pandas as pd

# On importe les briques FastAPI dont on a besoin :
#   - `Depends`       : déclare une « dépendance » à injecter (clé API, modèle…).
#   - `FastAPI`       : la classe de l'application elle-même.
#   - `Header`        : pour lire une valeur d'en-tête HTTP (ex. X-API-Key).
#   - `HTTPException` : pour renvoyer proprement une erreur HTTP (code + message).
#   - `Request`       : l'objet requête entrante (en-têtes, IP, etc.).
#   - `UploadFile`    : représente un fichier téléversé (pour /predict-image).
#   - `status`        : constantes nommées des codes HTTP (ex. HTTP_401_...).
from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, status
from fastapi.exception_handlers import http_exception_handler

# `loguru.logger` : une bibliothèque de JOURNALISATION (logs) très simple et
# agréable. On l'utilise pour tracer ce qui se passe (modèle chargé, etc.) et,
# plus loin, pour attacher un identifiant de requête à chaque ligne de log.
from loguru import logger

# `Instrumentator` (de prometheus-fastapi-instrumentator) : un outil qui ajoute
# AUTOMATIQUEMENT des métriques à l'API (nombre de requêtes, latences, codes de
# réponse…) et les expose sur une route /metrics au format attendu par
# Prometheus (un système de supervision/monitoring très répandu). Cela permet de
# SURVEILLER l'API en production sans écrire soi-même le code de comptage.
from prometheus_fastapi_instrumentator import Instrumentator

# On importe le MODULE `model_store` entier sous l'alias `store`. Pourquoi le
# module entier et pas juste des fonctions ? Parce qu'on doit ÉCRIRE dans sa
# variable globale `store._BUNDLE` au démarrage. En passant par `store.`, on
# modifie bien la variable du module partagé (et non une copie locale).
import indusense.api.model_store as store

# Les garde-fous de sécurité définis dans security.py :
#   - `limit_body_size` : middleware anti-payload-géant (413).
#   - `rate_limit`      : dépendance anti-flood (429).
#   ⚠️ On branche `rate_limit_dependency` (et NON `rate_limit`) : voir sa
#      docstring — brancher `rate_limit` directement exposerait `limit`/`window`
#      en paramètres de requête (`?limit=100000` contournerait le garde-fou).
from indusense.api.errors import PREDICTION_RESPONSES, READINESS_RESPONSES

# On importe aussi directement la classe `ModelBundle` (pour annoter les types)
# et la fonction `get_model_bundle` (pour l'injecter via Depends).
from indusense.api.model_store import ModelBundle, get_model_bundle

# Les schémas Pydantic définissant le contrat d'entrée/sortie de /predict-tabular.
from indusense.api.schemas import PredictionResponse, TabularPredictionRequest
from indusense.api.security import limit_body_size, rate_limit_dependency

# La configuration centrale du projet (chemins, clé API, seuil de décision…).
from indusense.config import settings

# Fonction qui met un identifiant machine au format canonique (ex. "M-7" -> "MACH-07").
from indusense.data.loaders import normalize_machine_id

# Fonction qui ajoute les features temporelles (lags + moyennes glissantes).
from indusense.features.temporal import add_temporal_features

# Deux fonctions du modèle tabulaire :
#   - `predict_proba`   : renvoie la probabilité de panne à partir des features.
#   - `select_features` : isole les colonnes à donner au modèle (retire la cible).
from indusense.models.tabular import predict_proba, select_features


# -----------------------------------------------------------------------------
#  LIFESPAN : ce qu'on fait au DÉMARRAGE et à l'ARRÊT de l'application.
# -----------------------------------------------------------------------------
# Le décorateur `@asynccontextmanager` permet d'avoir du code « avant » et
# « après » le `yield`. FastAPI appellera ce gestionnaire automatiquement :
# le code AVANT `yield` s'exécute au démarrage ; le code APRÈS (ici, rien)
# s'exécuterait à l'extinction. C'est l'endroit idéal pour charger le modèle.
# [PÉDAGOGIE] BLOC `lifespan` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : app ; preuve : l'appelant doit pouvoir vérifier la sortie ou
# [PÉDAGOGIE] l'effet de bord annoncé.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On tente de charger le modèle UNE FOIS, au démarrage du serveur.
    # [PÉDAGOGIE] ERREUR — cette frontière distingue le chemin nominal de la stratégie explicite
    # [PÉDAGOGIE] de récupération.
    try:
        # On charge le bundle (modèle + métadonnées + seuil) et on le RANGE dans
        # la variable globale du module `store`. Comme `get_model_bundle()` relit
        # cette même variable, toutes les routes verront désormais le modèle.
        #   - `settings.model_dir`         : dossier où trouver le modèle.
        #   - `settings.decision_threshold`: seuil de décision configuré.
        store._BUNDLE = store.load_bundle(settings.model_dir, settings.decision_threshold)
        # On trace dans les logs que tout s'est bien passé.
        logger.info("Modèle chargé")
    except (FileNotFoundError, store.ModelIntegrityError) as exc:
        # Le service DEMARRE quand meme : /health repondra 200 (le process vit),
        # /ready repondra 503 (le modele n'est pas la). C'est exactement la
        # distinction liveness / readiness posee au jalon 03. Un service qui
        # refuse de demarrer ne peut meme pas signaler pourquoi.
        logger.warning("Modele non charge : {}", exc)
        store._BUNDLE = None
        # ...et on prévient via un avertissement. Conséquence : /ready répondra
        # 503 (pas prêt) tant qu'aucun modèle n'est disponible. Démarrer malgré
        # tout permet par exemple aux sondes /health de fonctionner.
        logger.warning("Aucun modèle — /ready renverra 503")
    # `yield` = « le démarrage est terminé, l'application tourne maintenant ».
    # Tout ce qui serait écrit APRÈS ce yield s'exécuterait à l'arrêt (nettoyage,
    # fermeture de connexions…). Ici on n'a rien de spécial à faire à l'arrêt.
    yield


# -----------------------------------------------------------------------------
#  CRÉATION DE L'APPLICATION + branchement des middlewares et de l'observabilité.
# -----------------------------------------------------------------------------
# On instancie l'application FastAPI. On lui donne un titre et une version (qui
# apparaîtront dans la doc auto Swagger), et on lui passe notre `lifespan` pour
# qu'elle charge le modèle au démarrage.
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
app = FastAPI(title="InduSense API", version="0.1.0", lifespan=lifespan)

# Le garde-fou `limit_body_size` sera enregistré APRÈS les autres middlewares,
# plus bas. Starlette exécute le dernier middleware ajouté en premier : cet ordre
# garantit qu'un Content-Length invalide est rejeté avant que Prometheus tente de
# l'interpréter pour sa métrique de taille de requête.

# On active l'instrumentation Prometheus :
#   - `.instrument(app)` : ajoute la collecte automatique des métriques.
#   - `.expose(app, endpoint="/metrics", include_in_schema=False)` : publie ces
#     métriques sur la route GET /metrics. `include_in_schema=False` cache cette
#     route technique de la documentation Swagger (elle ne concerne pas les
#     utilisateurs « métier », seulement les outils de supervision).
# CONTROLE 5 — instrumentation branchee ici, EXPOSITION repoussee apres la
# definition de require_api_key (voir fin de fichier).
_instrumentator = Instrumentator().instrument(app)


# -----------------------------------------------------------------------------
#  MIDDLEWARE : attacher un identifiant unique à chaque requête (traçabilité).
# -----------------------------------------------------------------------------
# Le décorateur enregistre cette fonction comme middleware HTTP : elle s'exécute
# pour chaque requête, autour de l'appel à la route.
# [PÉDAGOGIE] BLOC `add_request_id` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : request, call_next ; preuve : l'appelant doit pouvoir vérifier
# [PÉDAGOGIE] la sortie ou l'effet de bord annoncé.
# ORDRE CRITIQUE — Starlette execute le DERNIER middleware enregistre en
# PREMIER. limit_body_size est donc enregistre AVANT add_request_id.
app.middleware("http")(limit_body_size)


# [PÉDAGOGIE] BLOC `add_request_id` — ...
@app.middleware("http")
async def add_request_id(
    request: Request, call_next
):  # On cherche un identifiant fourni par le client dans l'en-tête "X-Request-ID".
    # S'il n'en fournit pas, on en GÉNÈRE un nouveau, unique, avec uuid4().
    # Intérêt : pouvoir suivre UNE requête précise à travers tous les logs, et la
    # corréler avec ce que voit le client (utile pour le débogage en production).
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # `logger.contextualize(request_id=rid)` ajoute automatiquement ce `request_id`
    # à TOUTES les lignes de log émises pendant le traitement de cette requête.
    # Le bloc `with` garantit que ce contexte est bien retiré à la fin.
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with logger.contextualize(request_id=rid):
        # On laisse la requête poursuivre vers la route et on récupère la réponse.
        response = await call_next(request)

    # On renvoie aussi l'identifiant au client dans l'en-tête de réponse, pour
    # qu'il puisse le noter et le communiquer en cas de problème.
    response.headers["X-Request-ID"] = rid
    # On retourne la réponse (éventuellement enrichie) au client.
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return response


# Enregistré en dernier, ce garde-fou devient la couche HTTP la plus externe.
# Il protège donc aussi les middlewares d'observabilité contre les en-têtes de
# taille malformés, puis laisse passer les requêtes valides vers la chaîne.
# OLD CODE app.middleware("http")(limit_body_size)


# -----------------------------------------------------------------------------
#  DÉPENDANCE D'AUTHENTIFICATION : exiger une clé API valide (-> 401 sinon).
# -----------------------------------------------------------------------------
# Cette fonction sera branchée via `Depends(require_api_key)` sur les routes
# sensibles. FastAPI l'exécutera AVANT la route ; si elle lève une exception,
# la route n'est jamais atteinte.
#   - `x_api_key` : FastAPI lit pour nous l'en-tête HTTP "X-API-Key" (grâce à
#     `Header(None, alias="X-API-Key")`) et nous le donne. `None` = valeur par
#     défaut si l'en-tête est absent.
# [PÉDAGOGIE] BLOC `require_api_key` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : x_api_key ; preuve : l'appelant doit pouvoir vérifier la sortie
# [PÉDAGOGIE] ou l'effet de bord annoncé.
def require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    # Clé absente OU invalide -> 401 (et non 422) : statut sémantiquement correct pour l'auth.
    # Détail pédagogique : on choisit 401 (« Unauthorized » = non authentifié)
    # plutôt que 422 (« données invalides »), car ici le problème n'est pas la
    # FORME de la donnée mais le fait que l'appelant n'a pas prouvé son identité.
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if x_api_key is None or x_api_key != settings.api_key:
        # On compare la clé reçue à la clé attendue (stockée dans la config). Si
        # elle manque ou ne correspond pas, on refuse l'accès avec un message clair.
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé API absente ou invalide"
        )


# -----------------------------------------------------------------------------
#  ROUTE /health — « LIVENESS » : le serveur est-il vivant ?
# -----------------------------------------------------------------------------
# `@app.get("/health")` déclare une route accessible en GET sur l'URL /health.
# [PÉDAGOGIE] BLOC `health` — unité de responsabilité : isoler un comportement nommable, testable
# [PÉDAGOGIE] et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : l'appelant doit pouvoir
# [PÉDAGOGIE] vérifier la sortie ou l'effet de bord annoncé.
# CONTROLE 4 (STRIDE: Repudiation) — chaque refus laisse une trace correlee.
# Sans cela, une campagne de reconnaissance (401 en rafale) est invisible.
@app.exception_handler(HTTPException)
async def journaliser_les_refus(request: Request, exc: HTTPException):
    if exc.status_code in (401, 403, 413, 422, 429):
        # On journalise le CONTEXTE, jamais le secret soumis : la cle envoyee
        # par le client n'apparait nulle part ici, volontairement.
        logger.warning(
            "Refus {code} sur {route}",
            code=exc.status_code,
            route=request.url.path,
        )
    return await http_exception_handler(request, exc)


@app.get("/health")
def health() -> dict:
    # On renvoie un simple dictionnaire (FastAPI le convertit en JSON, code 200).
    # Cette sonde répond « ok » DÈS QUE le processus tourne, SANS vérifier le
    # modèle. C'est volontaire : un orchestrateur (ex. Kubernetes) l'utilise pour
    # savoir si le conteneur est vivant ; si /health échoue, il redémarre le pod.
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return {"status": "ok"}


# -----------------------------------------------------------------------------
#  ROUTE /ready — « READINESS » : le serveur est-il PRÊT à traiter des requêtes ?
# -----------------------------------------------------------------------------
# [PÉDAGOGIE] BLOC `ready` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : bundle ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
# [OLD] '@app.get("/ready")'
@app.get("/ready", responses=READINESS_RESPONSES)
def ready(bundle: ModelBundle | None = Depends(get_model_bundle)) -> dict:
    # Différence clé avec /health : ici on vérifie une vraie DÉPENDANCE métier,
    # le modèle. FastAPI nous l'injecte via `Depends(get_model_bundle)`.
    # Si le modèle n'est pas chargé (`bundle is None`), le service N'EST PAS prêt :
    # on répond 503 (« Service Unavailable »). Un orchestrateur cessera alors de
    # nous envoyer du trafic tant qu'on n'est pas prêt, sans pour autant nous tuer.
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if bundle is None:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=503, detail="Modèle non chargé")
    # Sinon, on est prêt : on renvoie « ready » et la version du modèle chargé
    # (pratique pour vérifier rapidement quel modèle tourne).
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return {"status": "ready", "model_version": bundle.version}


# -----------------------------------------------------------------------------
#  ROUTE /predict-tabular — la PRÉDICTION DE PANNE (le cœur métier de l'API).
# -----------------------------------------------------------------------------
# Décortiquons le décorateur :
#   - POST sur /predict-tabular (POST car le client ENVOIE des données).
#   - `response_model=PredictionResponse` : FastAPI VALIDERA et formatera la
#     réponse selon ce schéma (garantit le contrat de sortie + doc auto).
#   - `dependencies=[Depends(require_api_key), Depends(rate_limit_dependency)]` :
#     avant d'exécuter la route, FastAPI applique D'ABORD la vérification de clé
#     API (401 si invalide) PUIS le limiteur de débit (429 si trop de requêtes).
#     (On branche `rate_limit_dependency`, pas `rate_limit` : cf. sa docstring —
#     brancher la fonction paramétrée exposerait `?limit=` et la contournerait.)
#     Mettre ces dépendances ici (et pas en argument) signifie « exécute-les
#     pour leur EFFET de contrôle, on n'a pas besoin de leur valeur de retour ».
# [PÉDAGOGIE] BLOC `predict_tabular` — phase d'inférence ou d'évaluation : appliquer un contrat
# [PÉDAGOGIE] gelé à des observations nouvelles.
# [PÉDAGOGIE] CONTRAT — entrées : payload, bundle ; preuve : contrôler ordre des features, seuil,
# [PÉDAGOGIE] métriques et provenance du modèle.
@app.post(
    "/predict-tabular",
    response_model=PredictionResponse,
    dependencies=[Depends(require_api_key), Depends(rate_limit_dependency)],
    responses=PREDICTION_RESPONSES,
)
def predict_tabular(
    # `payload` : le corps JSON de la requête, automatiquement validé par Pydantic
    # selon le schéma `TabularPredictionRequest` (machine_id + >= 7 relevés).
    # Si les données sont invalides, FastAPI renvoie 422 AVANT même d'entrer ici.
    payload: TabularPredictionRequest,
    bundle: ModelBundle | None = Depends(get_model_bundle),
) -> PredictionResponse:
    # Garde-fou : si aucun modèle n'est chargé, on ne peut pas prédire -> 503.
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if bundle is None:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=503, detail="Modèle non chargé")

    # On transforme la liste de relevés (objets Pydantic) en un tableau pandas.
    #   - `r.model_dump()` convertit chaque relevé en dictionnaire simple.
    #   - On en fait une LISTE de dictionnaires, que pandas range en lignes.
    # Résultat : un DataFrame avec les colonnes timestamp, temperature, pressure_bar.
    df = pd.DataFrame([r.model_dump() for r in payload.readings])

    # Canonicalisation au bord : un client peut envoyer M-7 / MACH_07 (cf. 95 §2).
    # On normalise vers la clé interne ``machine`` ; ``machine_id`` brut est conservé en sortie.
    # Détail : « au bord » = à l'entrée de l'API, on nettoie tout de suite l'ID pour
    # que tout le reste du pipeline travaille sur un format unique et fiable.
    # [PÉDAGOGIE] ERREUR — cette frontière distingue le chemin nominal de la stratégie explicite
    # [PÉDAGOGIE] de récupération.
    try:
        # `normalize_machine_id` met l'ID au format canonique "MACH-0N". On range
        # cette valeur unique dans une nouvelle colonne "machine" attendue par les
        # fonctions de features (qui regroupent les relevés PAR machine).
        df["machine"] = normalize_machine_id(payload.machine_id)
    except ValueError as exc:
        # Si l'ID ne contient aucun numéro exploitable, `normalize_machine_id` lève
        # une `ValueError`. On la transforme en erreur HTTP 422 (donnée invalide),
        # avec le message d'origine. `from exc` garde le lien vers l'erreur initiale
        # (utile dans les logs pour comprendre la cause).
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # On calcule les FEATURES TEMPORELLES (lags + moyennes glissantes), puis on
    # retire les lignes incomplètes avec `.dropna()`. Les premières lignes ont
    # forcément des features manquantes (pas assez de passé pour calculer un lag 6
    # ou une moyenne sur 6) : on les écarte pour ne garder que des lignes exploitables.
    feats = add_temporal_features(df).dropna()

    # Si, après nettoyage, il ne reste AUCUNE ligne valide, c'est que l'historique
    # fourni était insuffisant (trop peu de relevés pour calculer les features sur
    # au moins une mesure). On répond 422 « Historique insuffisant ». Cela complète
    # la borne `min_length=7` du schéma : la borne filtre en amont, ce test attrape
    # les cas limites restants (ex. doublons d'horodatage réduisant l'historique utile).
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if feats.empty:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=422, detail="Historique insuffisant")

    # On prépare l'entrée du modèle :
    #   - `select_features(feats, bundle.target_col)` retire les colonnes qui ne
    #     sont pas des features (dont la colonne cible) : on ne donne au modèle
    #     que les variables explicatives.
    #   - `.iloc[[-1]]` ne garde que la DERNIÈRE ligne (la mesure la plus récente) :
    #     c'est sur l'état le plus actuel de la machine qu'on veut prédire. Les
    #     doubles crochets `[[-1]]` conservent un DataFrame (et non une simple
    #     ligne), format attendu par le modèle.
    X = select_features(feats, bundle.target_col).iloc[[-1]]

    # On demande au modèle la PROBABILITÉ de panne pour cette dernière mesure.
    #   - `predict_proba(...)` renvoie un tableau ; `[0]` prend le premier élément.
    #   - `float(...)` convertit ce résultat (type numpy) en nombre Python standard,
    #     attendu par le schéma de réponse (et propre à sérialiser en JSON).
    proba = float(predict_proba(bundle.model, X)[0])

    # On construit et renvoie la réponse, conforme au schéma `PredictionResponse` :
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return PredictionResponse(
        # On renvoie l'ID machine TEL QUE fourni par le client (pas la version
        # normalisée) : il s'y retrouve plus facilement.
        machine_id=payload.machine_id,
        # La probabilité de panne calculée.
        proba_panne=proba,
        # La DÉCISION : si la proba atteint/dépasse le seuil -> "alerte", sinon "ok".
        # C'est ici qu'une probabilité (nombre) devient une recommandation lisible.
        decision="alerte" if proba >= bundle.threshold else "ok",
        # La version du modèle (traçabilité).
        model_version=bundle.version,
        # Le seuil utilisé (transparence sur la règle de décision).
        threshold=bundle.threshold,
    )


# [PÉDAGOGIE] CONSTANTE / CONTRAT — signatures binaires des formats acceptés.
# [PÉDAGOGIE] Ces premiers octets sont imposés par chaque format d'image : le client
# [PÉDAGOGIE] ne peut pas les inventer sans envoyer une vraie image.
SIGNATURES_IMAGE: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"\xff\xd8\xff",  # JPEG
    b"GIF87a",  # GIF (ancienne version)
    b"GIF89a",  # GIF (version courante)
    b"BM",  # BMP
    b"II*\x00",  # TIFF petit-boutiste
    b"MM\x00*",  # TIFF grand-boutiste
)


# [PÉDAGOGIE] BLOC `_ressemble_a_une_image` — fonction PURE : mêmes octets, même verdict.
# [PÉDAGOGIE] L'isoler de la route la rend testable sans passer par HTTP.
def _ressemble_a_une_image(content: bytes) -> bool:
    """Vrai si les premiers octets correspondent a un format d'image connu.

    On ne decode pas l'image : on verifie seulement sa signature. C'est
    volontairement modeste — le but est d'ecarter ce qui n'est manifestement
    pas une image, pas de garantir qu'elle est valide ou inoffensive.
    """
    if any(content.startswith(signature) for signature in SIGNATURES_IMAGE):
        return True

    # WEBP : "RIFF" + 4 octets de taille + "WEBP". La taille varie, d'ou le
    # controle en deux morceaux plutot qu'un prefixe simple.
    return content.startswith(b"RIFF") and content[8:12] == b"WEBP"


# -----------------------------------------------------------------------------
#  ROUTE /predict-image — analyse d'image (ici : VALIDATION du fichier reçu).
# -----------------------------------------------------------------------------
# Mêmes protections que /predict-tabular : clé API (401) + anti-flood (429).
# Cette route est `async` car lire un fichier téléversé est une opération d'I/O
# qu'on attend avec `await` (le serveur peut faire autre chose pendant ce temps).
# [PÉDAGOGIE] BLOC `predict_image` — phase d'inférence ou d'évaluation : appliquer un contrat gelé
# [PÉDAGOGIE] à des observations nouvelles.
# [PÉDAGOGIE] CONTRAT — entrées : file, bundle ; preuve : contrôler ordre des features, seuil,
# [PÉDAGOGIE] métriques et provenance du modèle.
@app.post(
    "/predict-image",
    dependencies=[Depends(require_api_key), Depends(rate_limit_dependency)],
    responses=PREDICTION_RESPONSES,
)
async def predict_image(
    # `file: UploadFile` : FastAPI gère pour nous la réception d'un fichier envoyé
    # en « multipart/form-data ». `UploadFile` donne accès au nom, au type et au
    # contenu du fichier, sans tout charger d'un coup en mémoire si le fichier est gros.
    file: UploadFile,
    bundle: ModelBundle | None = Depends(get_model_bundle),
) -> dict:
    """Vision (intermédiaire) : validation réelle du fichier ; score auto-encodeur à brancher."""
    # La docstring ci-dessus annonce que la logique de scoring (détection
    # d'anomalie par auto-encodeur) reste à implémenter : pour l'instant on
    # se concentre sur la VALIDATION du fichier reçu (un vrai sujet de sécurité).

    # On lit le contenu binaire du fichier. `await` car c'est une opération d'I/O
    # asynchrone (lecture potentiellement longue).
    content = await file.read()

    # Validation 1 : le fichier ne doit pas être VIDE. Un contenu vide n'a aucun
    # sens à analyser -> on répond 422 (donnée invalide).
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not content:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=422, detail="Fichier image vide")

    # Validation 2 : le fichier doit être une IMAGE. On regarde le type MIME
    # déclaré (`content_type`, ex. "image/png", "image/jpeg"). On vérifie qu'il
    # COMMENCE par "image/". Si un type est fourni mais qu'il ne correspond pas à
    # une image -> 422. (On ne bloque pas si `content_type` est absent : on teste
    # `if file.content_type and ...`, donc la vérif ne s'applique que s'il est présent.)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if file.content_type and not file.content_type.startswith("image/"):
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(status_code=422, detail="Le fichier n'est pas une image")

    # Validation 3 : le CONTENU doit vraiment être une image. La validation 2
    # ne lit que l'en-tête DÉCLARÉ par le client — or un client hostile déclare
    # ce qu'il veut. Un exécutable renommé en .png avec content_type
    # "image/png" passe la validation 2 sans problème.
    # On vérifie donc les premiers octets du fichier, sa « signature » (aussi
    # appelée magic bytes) : chaque format d'image commence par une séquence
    # connue, que le client ne contrôle pas s'il envoie une vraie image.
    # [PÉDAGOGIE] DÉCISION — on fait confiance aux OCTETS, jamais à ce que le client déclare.
    # [PÉDAGOGIE] C'est la différence entre valider une étiquette et valider un contenu.
    if not _ressemble_a_une_image(content):
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise HTTPException(
            status_code=422,
            detail="Le contenu du fichier n'est pas une image reconnue",
        )

    # Si toutes les validations passent, on renvoie pour l'instant une réponse de
    # démonstration : on confirme le nom du fichier, sa taille réelle (en octets),
    # un score d'anomalie fixé à 0.0 (placeholder) et une décision "ok". C'est le
    # point d'ancrage où l'on branchera plus tard le vrai modèle de vision.
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "anomaly_score": 0.0,
        "decision": "ok",
    }


# CONTROLE 5 (STRIDE: Information disclosure) — include_in_schema=False retire
# /metrics de Swagger, PAS du reseau. On exige donc la cle API.
_instrumentator.expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
    dependencies=[Depends(require_api_key)],
)
