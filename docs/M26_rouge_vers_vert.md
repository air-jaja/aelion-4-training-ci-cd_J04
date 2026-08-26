# M26 — Du rouge au vert : les 5 controles priorises

> Compagnon de `docs/threat_model.md` et de `tests/test_security_controls.py`.
> Toutes les traces ci-dessous sont des executions reelles sur `jalon/04`.

## Principe

On ecrit les tests **avant** le code. Un test rouge n'est pas un echec : c'est
une specification qui n'a pas encore de mise en oeuvre. Le test dit precisement
ce qui manque, et l'implementation n'a plus qu'a le satisfaire.

L'ordre suit la priorisation du threat model : probabilite x impact, pondere par
le cout.

---

## Etape 0 — L'etat initial (rouge)

```powershell
uv run pytest tests/test_security_controls.py -q
```

```
FAILED test_default_api_key_rejected_in_production
FAILED test_bundle_loads_when_hash_matches
FAILED test_bundle_refuses_tampered_model
FAILED test_bundle_refuses_missing_hash
FAILED test_clients_behind_trusted_proxy_get_distinct_buckets
FAILED test_forged_forwarded_header_is_ignored
FAILED test_direct_client_uses_socket_address
FAILED test_rate_limit_uses_client_identity
FAILED test_refusal_is_logged_with_context
FAILED test_request_id_present_in_refusal_log
FAILED test_metrics_requires_api_key
11 failed, 5 passed
```

**Pourquoi 5 tests passent-ils deja ?** Ce sont les cas symetriques : la cle par
defaut acceptee en dev, `/metrics` absent d'OpenAPI, le secret absent de logs
vides. Ils decrivent un comportement deja correct et servent de garde-fou : ils
doivent rester verts pendant tout l'exercice.

**Point a faire remarquer en seance** : un test qui passe des le depart ne prouve
rien tant qu'on ne l'a pas vu echouer sur une version cassee.

---

## Controle 1 — Cle par defaut interdite en production `[S]`

### Le test qui echoue

```python
with pytest.raises(ValueError):
    Settings(environment="production", api_key="dev-key")
```

Sans controle, `Settings` se construit sans broncher. C'est exactement le
probleme : le service demarre ouvert, **sans aucun signal**.

### L'implementation

Dans `src/indusense/config.py` :

```python
DEFAULT_API_KEY = "dev-key"

class Settings(BaseSettings):
    environment: str = "dev"
    api_key: str = "dev-key"

    @model_validator(mode="after")
    def _refuser_cle_par_defaut_en_production(self) -> "Settings":
        if self.environment == "production" and self.api_key == DEFAULT_API_KEY:
            raise ValueError(
                "INDUSENSE_API_KEY vaut encore la valeur par defaut alors que "
                "INDUSENSE_ENVIRONMENT=production. Definir une vraie cle."
            )
        return self
```

### Resultat

```
4 passed, 11 deselected
```

**Ce qui compte ici** : le controle s'applique au demarrage, pas a la premiere
requete. Un service mal configure ne doit jamais atteindre l'etat « en ecoute ».

---

## Controle 2 — Integrite du modele `[T]`

### Le test qui echoue

```python
_ecrire_faux_modele(tmp_path, contenu, hashlib.sha256(contenu).hexdigest())
(tmp_path / "rf.joblib").write_bytes(b"modele-malveillant")   # substitution

with pytest.raises(ModelIntegrityError):
    load_bundle(tmp_path, threshold=0.5)
```

L'attaquant remplace le binaire **sans toucher aux metadonnees**. Sans controle,
`joblib.load` deserialise le pickle et execute son contenu.

### L'implementation

Dans `src/indusense/api/model_store.py` :

```python
class ModelIntegrityError(RuntimeError):
    """Le fichier modele ne correspond pas a l'empreinte declaree."""


def verify_artifact(path: Path, expected_sha256: str | None) -> None:
    if not expected_sha256:
        raise ModelIntegrityError(
            f"Aucune empreinte declaree pour {path.name} : chargement refuse."
        )
    obtenu = sha256_of(path)
    if obtenu != expected_sha256:
        raise ModelIntegrityError(f"Empreinte invalide pour {path.name}")
```

Puis, dans `load_bundle`, **avant** la deserialisation :

```python
meta = json.loads((model_dir / "model_metadata.json").read_text())
verify_artifact(model_dir / "rf.joblib", meta.get("rf_sha256"))   # <- ici
return ModelBundle(model=load_model(model_dir / "rf.joblib"), ...)
```

### Resultat

```
3 passed, 13 deselected
```

**L'ordre EST le controle.** Verifier apres `load_model` ne servirait a rien : le
code malveillant se serait deja execute. C'est le meme raisonnement que
`shift(1)` avant `rolling` au jalon 01 — deux operations correctes, un ordre qui
decide de tout.

**Choix defendu** : l'absence d'empreinte provoque un refus, pas une tolerance
silencieuse. Un artefact non verifiable n'est pas un artefact de confiance.

---

## Controle 3 — Rate limit derriere un proxy `[D]`

### Les tests qui echouent

```python
# Deux clients derriere le meme proxy doivent avoir des seaux distincts
assert client_identity(requete_a, trusted_proxies={proxy}) == "203.0.113.7"

# Un en-tete forge depuis une source non listee est ignore
assert client_identity(requete_forgee, trusted_proxies={"10.0.0.1"}) == "198.51.100.9"
```

Le rate limit existait deja et etait teste. Mais il comptait par
`request.client.host` : derriere un reverse proxy, **toutes les requetes du monde
partagent un seul seau de 60 req/min**.

### L'implementation

Dans `src/indusense/api/security.py` :

```python
TRUSTED_PROXIES: set[str] = set()


def client_identity(request, trusted_proxies: set[str] | None = None) -> str:
    proxies = TRUSTED_PROXIES if trusted_proxies is None else trusted_proxies
    adresse_socket = request.client.host

    if adresse_socket not in proxies:
        return adresse_socket          # en-tete non fiable : on l'ignore

    transmis = request.headers.get("x-forwarded-for", "")
    if not transmis:
        return adresse_socket

    return transmis.split(",")[0].strip()
```

Puis dans `rate_limit` :

```python
ip = client_identity(request, trusted_proxies)   # au lieu de request.client.host
```

### Resultat

```
4 passed, 12 deselected
```

**La lecon centrale du jalon** : le garde-fou etait *teste* et pourtant
*inoperant*. Un test qui passe ne dit rien de l'efficacite du controle dans son
environnement reel. La liste blanche est indispensable — sans elle, n'importe
qui forge `X-Forwarded-For` et obtient un quota neuf a chaque requete.

---

## Controle 4 — Journaliser les refus `[R]`

### Les tests qui echouent

```python
trace = " ".join(journal)
assert "401" in trace or "422" in trace
assert "/predict-tabular" in trace
assert "SECRET-A-NE-PAS-LOGUER" not in trace   # deja vert : logs vides
```

Le `request_id` existait depuis le jalon 03. Il manquait l'evenement.

### L'implementation

Dans `src/indusense/api/main.py` :

```python
@app.exception_handler(HTTPException)
async def journaliser_les_refus(request: Request, exc: HTTPException):
    if exc.status_code in (401, 403, 413, 422, 429):
        logger.warning(
            "Refus {code} sur {route}",
            code=exc.status_code,
            route=request.url.path,
        )
    return await http_exception_handler(request, exc)
```

Le `request_id` arrive automatiquement : le middleware du jalon 03 pose deja un
`logger.contextualize(request_id=rid)` autour de l'appel.

### Resultat

```
3 passed
```

**Le piege a montrer** : le test `test_submitted_key_never_appears_in_logs`
passait *avant* l'implementation, parce que les logs etaient vides. Il ne devient
significatif qu'une fois le controle 4 en place. C'est un bon exemple de test
dont la valeur depend d'un autre controle.

---

## Controle 5 — Fermer `/metrics` `[I]`

### Le test qui echoue

```python
assert client.get("/metrics").status_code == 401
```

```
AssertionError: assert 200 == 401
```

Deux cents anonyme : la volumetrie, les latences et la liste des routes sont
publiques.

### L'implementation

`include_in_schema=False` retire l'endpoint de Swagger, **pas du reseau**. Il
faut une dependance :

```python
# En haut : on instrumente, sans exposer
_instrumentator = Instrumentator().instrument(app)

# En bas de fichier, APRES la definition de require_api_key
_instrumentator.expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
    dependencies=[Depends(require_api_key)],
)
```

**Contrainte d'ordre** : `require_api_key` doit exister avant l'appel a
`expose()`. D'ou le deplacement en fin de fichier.

### Resultat

```
16 passed
```

---

## Etat final

```powershell
uv run pytest tests/ -q
```

```
38 passed
```

```powershell
uv run ruff check .
```

```
All checks passed!
```

Les 22 tests preexistants (`test_api.py`, `test_security.py`, `test_loaders.py`,
`test_temporal.py`, `test_package.py`) restent verts : aucune regression.

| Controle | STRIDE | Fichier modifie | Tests |
|---|---|---|---|
| 1. Cle par defaut interdite | S | `config.py` | 3 |
| 2. Integrite du modele | T | `api/model_store.py` | 3 |
| 3. Identite client reelle | D | `api/security.py` | 4 |
| 4. Journal des refus | R | `api/main.py` | 3 |
| 5. `/metrics` authentifie | I | `api/main.py` | 3 |

Total : 122 lignes ajoutees sur 4 fichiers, pour 16 preuves rejouables.

---

## Trois enseignements a formuler explicitement

**Un controle teste n'est pas un controle efficace.** Le rate limit du jalon 04
passait ses tests tout en etant inoperant derriere un proxy. La question n'est
pas « le test passe-t-il ? » mais « que se passe-t-il en production ? ».

**L'ordre des operations est parfois le controle lui-meme.** `verify_artifact`
avant `joblib.load`, comme `shift(1)` avant `rolling`. Deux operations correctes,
un ordre qui decide du resultat.

**« Non documente » n'est pas « non accessible ».** `include_in_schema=False`
masque de Swagger. Le port reste ouvert.

---

## Suite

Reporter les cinq controles dans `docs/security_controls.md`, avec le nom du test
comme preuve. Un controle sans nom de test dans cette colonne reste au statut
« planifie ».
