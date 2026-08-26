# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/api/errors.py
# [PÉDAGOGIE] MODULE  — M26 — durcissement de l'API et contrat d'erreur
# [PÉDAGOGIE] RÔLE    — Publier dans OpenAPI les codes d'erreur que l'API sait deja produire.
# [PÉDAGOGIE] THÉORIE — Un code d'erreur non documente n'est pas un contrat : le client le
# [PÉDAGOGIE]           decouvre en production
# [PÉDAGOGIE]           • 4xx = le client corrige et rejoue ; 5xx = le service est en cause
# [PÉDAGOGIE]           • centraliser les descriptions evite qu'elles derivent route par route
# [PÉDAGOGIE] À VOIR  — Swagger doit lister 400, 401, 413, 422, 429 et 503 sur /predict-tabular.
# [PÉDAGOGIE] PIÈGE   — Documenter un code que le code ne produit pas (ou l'inverse) : les tests
# [PÉDAGOGIE]           de ce jalon verifient les deux sens.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

"""Contrat d'erreur de l'API InduSense.

Deux formes de corps d'erreur coexistent, et c'est normal :

* ``{"detail": "message"}``          -> nos refus explicites (401, 413, 429, 503)
* ``{"detail": [{...}, {...}]}``     -> la validation Pydantic (422)

Le second est genere par FastAPI (schema ``HTTPValidationError``) et liste
chaque champ fautif. On ne cherche pas a les unifier : ils repondent a deux
besoins differents.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# [PÉDAGOGIE] CONSTANTE / CONTRAT — la politique de debit est fixe et publiee ici une seule fois.
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_WINDOW_SECONDS = 60


# [PÉDAGOGIE] BLOC `ErrorResponse` — frontiere de sortie : donner une forme stable a nos refus.
class ErrorResponse(BaseModel):
    """Corps renvoye par les refus explicites de l'API."""

    detail: str = Field(..., examples=["Cle API absente ou invalide"])


# [PÉDAGOGIE] BLOC — chaque entree decrit un code que l'API produit REELLEMENT.
# [PÉDAGOGIE] Ne rien ajouter ici sans le test correspondant : la doc mentirait.

_REQUEST_ID_HEADER = {
    "X-Request-ID": {
        "description": "Identifiant de correlation, repris de la requete ou genere.",
        "schema": {"type": "string"},
    }
}

BAD_CONTENT_LENGTH = {
    "model": ErrorResponse,
    "description": (
        "En-tete `Content-Length` illisible. Le middleware refuse avant tout "
        "traitement plutot que de laisser le serveur planter."
    ),
    "headers": _REQUEST_ID_HEADER,
    "content": {"application/json": {"example": {"detail": "Content-Length invalide"}}},
}

UNAUTHORIZED = {
    "model": ErrorResponse,
    "description": "En-tete `X-API-Key` absent ou incorrect.",
    "headers": _REQUEST_ID_HEADER,
    "content": {"application/json": {"example": {"detail": "Cle API absente ou invalide"}}},
}

PAYLOAD_TOO_LARGE = {
    "model": ErrorResponse,
    "description": (
        "Corps de requete superieur a 64 Ko. La limite est fixe et ne peut pas "
        "etre relevee par le client."
    ),
    "headers": _REQUEST_ID_HEADER,
    "content": {"application/json": {"example": {"detail": "Payload trop volumineux"}}},
}

TOO_MANY_REQUESTS = {
    "model": ErrorResponse,
    "description": (
        f"Plus de {RATE_LIMIT_PER_MINUTE} requetes par fenetre de "
        f"{RATE_LIMIT_WINDOW_SECONDS} s pour un meme client. Politique FIXE : "
        "aucun parametre de requete ne permet de la modifier."
    ),
    "headers": {
        **_REQUEST_ID_HEADER,
        "Retry-After": {
            "description": "Nombre de secondes avant de pouvoir rejouer.",
            "schema": {"type": "integer"},
        },
    },
    "content": {"application/json": {"example": {"detail": "Trop de requetes"}}},
}

UNPROCESSABLE = {
    "description": (
        "Corps invalide au regard du schema : moins de 7 releves, valeur hors "
        "bornes physiques, `machine_id` sans numero, ou historique insuffisant "
        "apres calcul des features temporelles."
    ),
    "headers": _REQUEST_ID_HEADER,
}

SERVICE_UNAVAILABLE = {
    "model": ErrorResponse,
    "description": (
        "Aucun modele charge. Le service est vivant (`/health` repond) mais pas "
        "pret : c'est toute la difference entre liveness et readiness."
    ),
    "headers": _REQUEST_ID_HEADER,
    "content": {"application/json": {"example": {"detail": "Modele non charge"}}},
}


# [PÉDAGOGIE] CONTRAT — jeu complet pour une route de prediction protegee.
PREDICTION_RESPONSES: dict[int | str, dict] = {
    400: BAD_CONTENT_LENGTH,
    401: UNAUTHORIZED,
    413: PAYLOAD_TOO_LARGE,
    422: UNPROCESSABLE,
    429: TOO_MANY_REQUESTS,
    503: SERVICE_UNAVAILABLE,
}

# [PÉDAGOGIE] CONTRAT — /ready ne demande pas de cle : seule la readiness peut echouer.
READINESS_RESPONSES: dict[int | str, dict] = {
    503: SERVICE_UNAVAILABLE,
}
