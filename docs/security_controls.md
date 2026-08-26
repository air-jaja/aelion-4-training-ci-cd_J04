# Matrice de controles M26

> Etat au 25/08/2026, branche `jalon/04`. Suite de tests : **73 tests verts**.
> Regle : un controle passe a « Implemente » uniquement si la colonne « Preuve
> testee » nomme un test rejouable. Aucune cle ni valeur de `.env` ici.

## Controles implementes

| Controle | STRIDE | Implementation | Preuve testee | Etat | Limite connue | Action suivante |
|---|---|---|---|---|---|---|
| Cle API / 401 | S | `api/main.py::require_api_key` | `test_api.py::test_missing_api_key_returns_401` | Implemente | Cle unique partagee, non rotative ; comparaison en temps non constant | Une cle par consommateur ; `secrets.compare_digest` |
| Cle par defaut interdite en prod | S | `config.py::_refuser_cle_par_defaut_en_production` | `test_security_controls.py::test_default_api_key_rejected_in_production` (+2) | Implemente | Ne couvre que la valeur `dev-key` exacte, pas une cle faible | Exiger une longueur minimale |
| Validation / 422 | T | `api/schemas.py` (Pydantic) | `test_api.py::test_insufficient_readings_returns_422` | Implemente | `detail=str(exc)` renvoie la valeur soumise au client | Message generique cote client, detail cote log |
| Validation binaire des images | E | `api/main.py::_ressemble_a_une_image` | `test_predict_image.py` (11 tests) | Implemente | Une image bien signee mais malformee passe : le decodeur reste expose | Decodage en environnement contraint (M27) |
| Taille du corps / 413 | T | `api/security.py::limit_body_size` | `test_security.py::test_payload_too_large_returns_413` | Implemente | `Transfer-Encoding: chunked` sans `Content-Length` contourne la limite | Compter les octets lus, pas ceux annonces |
| Content-Length illisible / 400 | T | `api/security.py::limit_body_size` | `test_security.py::test_invalid_content_length_returns_400` | Implemente | — | — |
| Rate limit / 429 | D | `api/security.py::rate_limit_dependency` | `test_security.py::test_rate_limit_blocks_after_limit` | Implemente | Compteur en memoire, par process : N workers = N x la limite | Compteur partage (Redis) |
| Politique de debit non surchargeable | E | `api/security.py::rate_limit_dependency` | `test_security.py::test_rate_limit_policy_is_not_exposed_as_query_parameters` | Implemente | — | — |
| Identite client derriere proxy | D | `api/security.py::client_identity` | `test_security_controls.py::test_forged_forwarded_header_is_ignored` (+3) | Implemente | `TRUSTED_PROXIES` vide par defaut : a renseigner au deploiement | Documenter la valeur attendue en production |
| Integrite du modele | T | `api/model_store.py::verify_artifact` | `test_security_controls.py::test_bundle_refuses_tampered_model` (+2) | Implemente | L'empreinte vit dans `model_metadata.json`, non signee : integrite, pas authenticite | Signature de l'artefact |
| Audit logging des refus | R | `api/main.py::journaliser_les_refus` | `test_security_controls.py::test_refusal_is_logged_with_context` (+2) | Implemente | Ne journalise ni l'IP ni la decision « ok » | Ajouter l'identite client et l'empreinte d'entree |
| `/metrics` authentifie | I | `api/main.py` (`dependencies=[Depends(require_api_key)]`) | `test_security_controls.py::test_metrics_requires_api_key` (+2) | Implemente | Meme cle que la prediction : l'exploitation partage le secret metier | Cle dediee ou port interne |
| Correlation `X-Request-ID` | R | `api/main.py::add_request_id` | `test_request_id.py` (7 tests) | Implemente | — | — |
| Contrat d'erreur publie | — | `api/errors.py` | `test_error_contract.py` (13 tests) | Implemente | — | — |

## Controles planifies

| Controle | STRIDE | Preuve testee | Etat | Limite connue | Action suivante |
|---|---|---|---|---|---|
| Comparaison de cle a temps constant | S | Aucune | Planifie v0 | Attaque par mesure de latence peu realiste sur HTTP public | `secrets.compare_digest`, cout nul |
| Limite de corps sur flux `chunked` | T | Aucune | Planifie v0 | Partiellement couvert par le reverse proxy en deploiement type | Compter les octets reellement lus |
| Eviction du compteur de debit | D | Aucune | Planifie v0 | `_hits` croit avec le nombre d'IP distinctes vues | TTL ou purge des cles inactives |
| Rotation des cles API | S | Aucune | Planifie v0 | Une seule cle pour toutes les integrations | Une cle par consommateur + procedure de rotation |
| Reduction de `/ready` | I | Aucune | Planifie v0 | `model_version` visible sans authentification | Reduire a `{"status": "ready"}` en exposition publique |

## Deux points d'attention pour la relecture

**Un controle teste n'est pas un controle efficace.** Le rate limit passait ses
tests au depart tout en etant inoperant derriere un reverse proxy : il comptait
par adresse de socket, donc par IP de proxy. La colonne « Limite connue » existe
pour ces ecarts entre ce qui est prouve et ce qui protege.

**Trois controles dependent d'un ORDRE, pas d'une presence.** `verify_artifact`
avant `joblib.load`, `add_request_id` enregistre apres `limit_body_size`,
et le filtre de bornes avant le dedoublonnage dans `clean_sensor_data`. Deplacer
l'un d'eux laisse le code fonctionnel et le controle inoperant, sans qu'aucun
test de presence ne le detecte.

Ne jamais marquer un controle « implemente » sans test rejouable. Ne jamais
coller de cle ou de valeur de `.env` dans cette matrice.
