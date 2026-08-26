# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_package.py
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

# [PÉDAGOGIE] DÉPENDANCE — indusense : apporte une dépendance explicitement visible au lecteur.
import indusense


# [PÉDAGOGIE] BLOC `test_package_importable` — ce test transforme un comportement attendu en
# [PÉDAGOGIE] contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_package_importable():
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert indusense.__version__ == "0.1.0"
