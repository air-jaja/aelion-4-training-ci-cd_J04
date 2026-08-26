# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — FORMATION/EXERCICES/tp_api_m25_v1_20260823/tests/test_readiness_probe.py
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

# [PÉDAGOGIE] DÉPENDANCE — collections.abc : apporte une dépendance explicitement visible au
# [PÉDAGOGIE] lecteur.
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from indusense.api.main import app
from indusense.api.model_store import get_model_bundle
from indusense.config import settings

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
client = TestClient(app)


# [PÉDAGOGIE] BLOC `model_unavailable` — unité de responsabilité : isoler un comportement
# [PÉDAGOGIE] nommable, testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : l'appelant doit pouvoir
# [PÉDAGOGIE] vérifier la sortie ou l'effet de bord annoncé.
@contextmanager
def model_unavailable() -> Iterator[None]:
    """Remplace seulement get_model_bundle, puis restaure son état exact."""
    overrides = app.dependency_overrides
    marker = object()
    previous = overrides.get(get_model_bundle, marker)
    overrides[get_model_bundle] = lambda: None
    # [PÉDAGOGIE] ERREUR — cette frontière distingue le chemin nominal de la stratégie explicite
    # [PÉDAGOGIE] de récupération.
    try:
        yield
    finally:
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if previous is marker:
            overrides.pop(get_model_bundle, None)
        else:
            overrides[get_model_bundle] = previous


# [PÉDAGOGIE] BLOC `readings` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : vérifier schéma, types,
# [PÉDAGOGIE] ordre et erreurs explicites avant tout calcul aval.
def readings() -> list[dict[str, object]]:
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return [
        {
            "timestamp": f"2025-02-01T{hour:02d}:00:00",
            "temperature": 50 + hour,
            "pressure_bar": 195 + hour * 0.5,
        }
        for hour in range(8)
    ]


# [PÉDAGOGIE] BLOC `test_ready_returns_exact_503_when_model_is_unavailable` — ce test transforme
# [PÉDAGOGIE] un comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_ready_returns_exact_503_when_model_is_unavailable() -> None:
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with model_unavailable():
        response = client.get("/ready")

    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert response.status_code == 503
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert response.json() == {"detail": "Modele non charge"}


# [PÉDAGOGIE] BLOC `test_predict_tabular_returns_exact_503_after_auth_and_validation` — ce test
# [PÉDAGOGIE] transforme un comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_predict_tabular_returns_exact_503_after_auth_and_validation() -> None:
    # [PÉDAGOGIE] RESSOURCE — le gestionnaire de contexte garantit ouverture et libération, même
    # [PÉDAGOGIE] en cas d'exception.
    with model_unavailable():
        response = client.post(
            "/predict-tabular",
            headers={"X-API-Key": settings.api_key},
            json={"machine_id": "MACH-01", "readings": readings()},
        )

    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert response.status_code == 503
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert response.json() == {"detail": "Modele non charge"}
