# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_smoke_compose.py
# [PÉDAGOGIE] MODULE  — Sprint 3 — tests comme contrats exécutables
# [PÉDAGOGIE] RÔLE    — Décrire un invariant observable avec Arrange, Act, Assert et prévenir les
# [PÉDAGOGIE]           régressions.
# [PÉDAGOGIE] THÉORIE — un test porte sur un comportement, pas sur l'implémentation accidentelle
# [PÉDAGOGIE]           • les fixtures contrôlent l'entrée et rendent l'échec reproductible
# [PÉDAGOGIE]           • les cas limites protègent les frontières où les incidents apparaissent
# [PÉDAGOGIE] À VOIR  — Le nom du test, son entrée et son assertion doivent expliquer précisément
# [PÉDAGOGIE]           la garantie couverte.
# [PÉDAGOGIE] PIÈGE   — Un test qui dépend du réseau, de l'heure ou d'un ordre implicite peut
# [PÉDAGOGIE]           devenir instable.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

"""Squelette du smoke test M28, a completer pendant la demi-journee."""

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import pytest


# [PÉDAGOGIE] BLOC `test_api_health_and_auth_contract` — ce test transforme un comportement
# [PÉDAGOGIE] attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
@pytest.mark.skip(reason="A completer en M28 apres docker compose up")
def test_api_health_and_auth_contract() -> None:
    """Prouver /health=200, prediction sans cle=401 et prediction valide=200."""
    # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
    # [PÉDAGOGIE] suivantes.
    raise NotImplementedError
