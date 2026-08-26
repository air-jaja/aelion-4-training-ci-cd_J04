# Threat model InduSense — M26

> Perimetre : `POST /predict-tabular` et la chaine qui l'alimente (chargement du
> bundle, features temporelles, artefacts DVC). Version analysee : `jalon/04`.
> Convention : ce fichier est ecrit sans accents, comme les autres documents de
> `docs/`, pour rester lisible quel que soit l'encodage du poste.

## Actifs a proteger

| Actif | Pourquoi il compte | Ou il vit |
|---|---|---|
| Modele entraine (`rf.joblib`) | Propriete intellectuelle ; sa substitution change toutes les decisions | `artifacts/models/`, remote DVC |
| Cle API (`INDUSENSE_API_KEY`) | Seul secret d'authentification du service | `.env`, variables d'environnement |
| Donnees capteurs entrantes | Revelent la charge et l'etat du parc industriel du client | Corps des requetes, logs |
| Decisions de maintenance | Un faux « ok » laisse tourner une machine en panne imminente | Reponses HTTP |
| Disponibilite du service | La maintenance predictive n'a de valeur que si elle repond | Process uvicorn |
| Dataset gold | Une alteration reoriente silencieusement le prochain entrainement | `data/gold/`, remote DVC |

## Frontieres de confiance

1. **Internet -> API.** Tout ce qui franchit cette limite est hostile par
   defaut : en-tetes, corps, `Content-Length`, `content_type`, `machine_id`.
2. **API -> systeme de fichiers.** `load_bundle` deserialise un `.joblib`.
   Quiconque ecrit dans `artifacts/models/` execute du code dans le process.
3. **API -> logs.** Ce qui y entre sort du perimetre applicatif (collecte,
   retention, acces d'exploitation).
4. **Pipeline d'entrainement -> artefacts.** Le remote DVC est une source
   externe au process d'inference.
5. **Reverse proxy -> API.** `request.client.host` ne designe le client reel
   que si cette frontiere est correctement configuree.

## Menaces STRIDE

| Menace | Scenario concret | Impact | Controle existant | Risque residuel | Action |
|---|---|---|---|---|---|
| **S** — Spoofing | Un tiers rejoue la cle API interceptee ; toutes les integrations partagent la meme | Acces complet a la prediction | `require_api_key` (401) | Eleve — cle unique, non rotative, pas d'identite par client | Une cle par consommateur + rotation documentee |
| **S** — Spoofing | `config.py` fixe `api_key = "dev-key"` par defaut ; sans `.env`, la valeur est publique dans le depot | Authentification nulle en production | `_refuser_cle_par_defaut_en_production` leve au demarrage | **Traite** — subsiste : une cle faible mais differente du defaut passe | Exiger une longueur minimale |
| **S** — Spoofing | Comparaison `x_api_key != settings.api_key` en temps non constant | Extraction de la cle par mesure de latence | Aucun | Faible en pratique, trivial a corriger | `secrets.compare_digest` |
| **T** — Tampering | Corps volumineux en `Transfer-Encoding: chunked`, sans `Content-Length` | Contournement de la limite de 64 Ko | `limit_body_size` (413) lit l'en-tete declare uniquement | **Eleve** | Compter les octets reellement lus, pas ceux annonces |
| **T** — Tampering | Ecriture d'un `rf.joblib` malveillant dans `artifacts/models/` | Execution de code arbitraire au chargement (pickle) | `verify_artifact` compare le SHA-256 AVANT `joblib.load` | **Traite** — subsiste : l'empreinte vit dans `model_metadata.json`, non signee (integrite, pas authenticite) | Signature de l'artefact |
| **T** — Tampering | Empoisonnement du dataset gold sur le remote DVC | Modele biaise, faux « ok » sur des machines a risque | Hash DVC (integrite, pas authenticite) | Moyen | Remote en ecriture restreinte + revue des `.dvc` en PR |
| **R** — Repudiation | Un refus 401 ou 429 ne laisse aucune trace exploitable | Impossible de reconstituer une tentative d'intrusion | `journaliser_les_refus` trace code + route + `request_id` | **Traite** — subsiste : ni l'IP ni la decision « ok » ne sont journalisees | Ajouter l'identite client et l'empreinte d'entree |
| **R** — Repudiation | Une decision « ok » contestee ne peut etre reliee ni au modele ni a l'entree | Pas d'opposabilite en cas de litige | `model_version` dans la reponse | Moyen | Journaliser version, seuil et empreinte de l'entree |
| **I** — Information disclosure | `/metrics` est expose sans authentification | Volumetrie, latences et routes visibles de l'exterieur | `dependencies=[Depends(require_api_key)]` sur l'exposition | **Traite** — subsiste : meme cle que la prediction | Cle dediee ou port interne |
| **I** — Information disclosure | `HTTPException(422, detail=str(exc))` renvoie le message interne, qui contient la valeur envoyee | Fuite mineure ; surface d'apprentissage pour l'attaquant | Aucun | Faible | Message generique cote client, detail cote log |
| **I** — Information disclosure | `/ready` publie `model_version` sans authentification | Renseigne sur le cycle de deploiement | Aucun | Faible | Reduire a `{"status": "ready"}` sur l'exposition publique |
| **D** — Denial of service | Flood depuis N adresses distinctes | Saturation CPU du modele | `rate_limit_dependency` (429), 60 req/min/IP | **Eleve** — compteur en memoire, par process : N workers = N x la limite | Compteur partage (Redis) ou limitation au proxy |
| **D** — Denial of service | Derriere un reverse proxy, `request.client.host` vaut l'IP du proxy | Soit un seul seau pour tous, soit blocage general | `client_identity` lit `X-Forwarded-For` via liste blanche | **Traite** — subsiste : `TRUSTED_PROXIES` vide par defaut, a renseigner au deploiement | Documenter la valeur de production |
| **D** — Denial of service | `_hits` est un `defaultdict` non borne, une entree par IP vue | Croissance memoire illimitee | Purge de la fenetre glissante, jamais des cles | Moyen | Eviction des IP inactives ou TTL |
| **E** — Elevation of privilege | `Depends(rate_limit)` exposerait `limit` et `window` en query string : `?limit=100000` desactive la limite | Contournement complet du garde-fou | `rate_limit_dependency` n'expose que `request` | **Traite** | Test de non-regression sur la signature |
| **E** — Elevation of privilege | `/predict-image` accepte tout contenu declare `image/*` ; un executable renomme passe | Charge utile arbitraire transmise au futur decodeur | `_ressemble_a_une_image` verifie la signature binaire | **Traite** — subsiste : une image bien signee mais malformee cible encore le decodeur | Decodage en environnement contraint (M27) |

## Priorisation — 5 controles

Criteres : probabilite d'exploitation x impact metier, pondere par le cout de
mise en oeuvre. Les cinq retenus couvrent S, T, R, I et D.

### 1. Interdire la cle par defaut au demarrage — `S`

`api_key: str = "dev-key"` est ecrit dans un depot lu par toute la promotion. Un
oubli de `.env` en production donne un service ouvert, sans aucun signal.

**Preuve attendue** : un test demarre l'application avec la valeur par defaut et
un indicateur d'environnement « production », et attend l'echec.
**Cout** : quelques lignes dans `config.py`. **A faire en premier.**

### 2. Verifier l'integrite du modele avant chargement — `T`

`joblib.load` deserialise du pickle : lire un fichier revient a executer du code.
C'est la seule menace du perimetre qui donne l'execution arbitraire.

**Preuve attendue** : `load_bundle` compare une empreinte SHA-256 a une valeur de
reference et refuse de charger en cas d'ecart ; un test fournit un fichier
modifie et attend le refus.
**Cout** : modere. L'empreinte peut venir du `.dvc`, deja versionne.

### 3. Rendre le rate limit effectif derriere un proxy — `D`

Le controle existe mais ne protege pas : en deploiement reel,
`request.client.host` vaut l'IP du reverse proxy. Soit tous les clients partagent
un seau de 60 req/min, soit le premier flood bloque tout le monde. S'y ajoute le
compteur par process, multiplie par le nombre de workers.

**Preuve attendue** : test avec `X-Forwarded-For` verifiant que deux clients
derriere le meme proxy ont des seaux distincts, et qu'un en-tete forge depuis une
source non listee est ignore.
**Cout** : modere ; le passage a un compteur partage peut suivre.

### 4. Journaliser les refus — `R`

Sans trace des 401, 413 et 429, une campagne de reconnaissance est invisible. Le
`request_id` existe deja : il ne manque que l'evenement.

**Preuve attendue** : test capturant la sortie du logger sur une requete sans
cle, verifiant la presence de `request_id`, de la route et du code — **et
l'absence de la cle soumise**.
**Cout** : faible. Effet immediat sur la detection.

### 5. Fermer `/metrics` — `I`

`include_in_schema=False` retire l'endpoint de Swagger, pas du reseau. Un
`GET /metrics` anonyme donne la volumetrie, les latences et la liste des routes,
y compris celles non documentees.

**Preuve attendue** : `GET /metrics` sans authentification renvoie 401.
**Cout** : faible.

### Ecartes a ce stade

`secrets.compare_digest` (cout nul, mais l'attaque par mesure de latence est peu
realiste sur HTTP public) ; la limite `chunked` (couverte partiellement par le
proxy en deploiement type) ; l'eviction des cles de `_hits` ; la rotation des
cles API. A reprendre au jalon suivant.

La validation binaire des images, initialement ecartee, a finalement ete traitee
dans le meme jalon : le cout s'est revele faible (une fonction pure de sept
lignes) et la menace plus concrete qu'estime — le `content_type` etant declare
par le client, la validation existante ne protegeait de rien.

## Hors perimetre et hypotheses

- **Hypothese** : TLS est termine par un reverse proxy en amont. Le service ne
  gere ni certificats ni redirection HTTP vers HTTPS.
- **Hypothese** : l'acces au systeme de fichiers du conteneur suppose deja une
  compromission de l'hote. Le durcissement de l'image est traite en M27.
- **Hors perimetre** : securite du remote DVC (droits, chiffrement au repos).
- **Hors perimetre** : conformite RGPD des donnees capteurs. Aucune donnee
  personnelle identifiee a ce stade, a reconfirmer si `machine_id` devient
  rattachable a un operateur.
- **Hors perimetre** : extraction de modele par requetes repetees. Le rate limit
  la ralentit sans l'empecher.

## Etat au 25/08/2026

Les cinq controles priorises sont implementes, plus la validation binaire des
images. Six menaces passent de « Critique » ou « Eleve » a « Traite ». Les
risques residuels sont documentes ligne par ligne : aucun n'est ferme, tous sont
reduits.

Suite de tests : **73 tests verts**. Detail des preuves dans
`docs/security_controls.md`.

Menaces restant a traiter, par priorite decroissante :

1. Cle unique partagee, non rotative (`S`) — la plus exposee des restantes.
2. Contournement de la limite de corps en `Transfer-Encoding: chunked` (`T`).
3. Compteur de debit en memoire, par process : N workers = N x la limite (`D`).
4. Croissance non bornee de `_hits` (`D`).
5. `detail=str(exc)` renvoie la valeur soumise (`I`).

**Ne jamais marquer un controle « implemente » sans test rejouable** : les deux
documents doivent rester coherents, sinon la matrice devient une declaration
d'intention.
