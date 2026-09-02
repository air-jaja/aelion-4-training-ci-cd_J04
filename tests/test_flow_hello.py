# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_flow_hello.py
# [PÉDAGOGIE] MODULE  — M29 — orchestration avec Prefect
# [PÉDAGOGIE] RÔLE    — Prouver le comportement des retries, chiffres a l'appui.
# [PÉDAGOGIE] THÉORIE — un flow se teste comme une fonction : on l'APPELLE
# [PÉDAGOGIE]           • pas besoin de serveur Prefect ni de deploiement
# [PÉDAGOGIE]           • `retries=2` = 3 executions au maximum, le test le compte
# [PÉDAGOGIE] À VOIR  — Le test qui compte les tentatives : c'est la seule preuve chiffree.
# [PÉDAGOGIE] PIÈGE   — Oublier de remettre le compteur a zero entre deux tests : le second
# [PÉDAGOGIE]           heriterait des tentatives du premier.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_flow_hello.py
# RÔLE    : le contrat du flow « hello ».
# -----------------------------------------------------------------------------
# CE QUI EST VERIFIE :
#   1. le flow s'execute et renvoie le message attendu ;
#   2. `retries=2` autorise EXACTEMENT 3 executions (1 + 2 reprises) ;
#   3. au-dela, l'exception remonte : le flow echoue.
#
# Un flow Prefect s'appelle comme une fonction ordinaire. Prefect cree un
# « flow run » ephemere en memoire : aucun serveur a lancer.
# =============================================================================

import pytest
from prefect.testing.utilities import prefect_test_harness

# `indusense.flows` est un sous-paquet ordinaire : aucun bricolage de sys.path.
# C'est l'avantage de placer les flows DANS le paquet plutot qu'a cote.
from indusense.flows.hello import (
    NB_RETRIES,
    dire_bonjour,
    hello,
    reinitialiser_compteur,
)


# [PÉDAGOGIE] BLOC `harnais_prefect` — portee `session` : UN seul serveur temporaire pour
# [PÉDAGOGIE] tout le fichier, au lieu d'un par appel de flow. Sans lui, chaque `hello(...)`
# [PÉDAGOGIE] demarre et arrete son propre serveur : le premier test payait 27 secondes.
@pytest.fixture(scope="session", autouse=True)
def harnais_prefect():
    """Demarre une base Prefect temporaire, partagee par tous les tests.

    C'est l'outil officiel pour tester des flows. Il isole l'execution de
    toute base Prefect reelle : aucun run de test ne pollue l'historique de
    developpement.
    """
    with prefect_test_harness():
        yield


@pytest.fixture(autouse=True)
def compteur_propre():
    """Remet le compteur de tentatives a zero avant CHAQUE test.

    `_tentatives` est un etat de module : sans ce nettoyage, un test qui
    consomme 3 tentatives fausserait le suivant.
    """
    reinitialiser_compteur()
    yield
    reinitialiser_compteur()


# =============================================================================
# LE CAS NOMINAL
# =============================================================================


# [PÉDAGOGIE] BLOC — un flow s'appelle comme une fonction. Rien de plus.
def test_flow_renvoie_le_message():
    """Le flow s'execute et renvoie la salutation."""
    assert hello(nom="Aelion") == "Bonjour Aelion !"


# [PÉDAGOGIE] BLOC — sans echec, une seule execution : les retries ne coutent rien.
def test_aucune_reprise_si_pas_d_echec():
    """Une tache qui reussit du premier coup n'est pas rejouee."""
    from indusense.flows.hello import _tentatives

    hello(nom="Aelion")

    assert _tentatives["n"] == 1


# =============================================================================
# LES RETRIES — la preuve chiffree
# =============================================================================


# [PÉDAGOGIE] BLOC — LE test du jalon : retries=2 signifie 3 executions, pas 2.
def test_retries_autorisent_trois_executions():
    """Avec 2 echecs simules, la 3e tentative reussit.

    C'est la demonstration que `retries=2` compte des RE-tentatives, en PLUS
    de l'execution initiale. Confondre les deux fait dimensionner les
    garde-fous a l'envers.
    """
    from indusense.flows.hello import _tentatives

    resultat = hello(nom="Aelion", echecs_simules=2)

    assert resultat == "Bonjour Aelion !"
    assert _tentatives["n"] == NB_RETRIES + 1 == 3


# [PÉDAGOGIE] BLOC — un seul echec : la reprise suffit, le flow reussit.
def test_un_echec_est_rattrape():
    """Un echec transitoire est absorbe sans intervention."""
    from indusense.flows.hello import _tentatives

    assert hello(nom="Aelion", echecs_simules=1) == "Bonjour Aelion !"
    assert _tentatives["n"] == 2


# [PÉDAGOGIE] BLOC — au-dela des reprises, l'echec remonte. Un retry n'est pas un filet infini.
def test_retries_epuises_font_echouer_le_flow():
    """3 echecs depassent les 2 reprises : l'exception remonte."""
    from indusense.flows.hello import _tentatives

    with pytest.raises(RuntimeError, match="Echec simule"):
        hello(nom="Aelion", echecs_simules=NB_RETRIES + 1)

    # Le compteur s'arrete a 3 : Prefect n'a pas tente une 4e fois.
    assert _tentatives["n"] == NB_RETRIES + 1


# =============================================================================
# LA CONFIGURATION DECLAREE
# =============================================================================


# [PÉDAGOGIE] BLOC — la configuration est lisible sur l'objet tache, pas seulement dans le code.
def test_la_tache_declare_ses_retries():
    """`retries` et `retry_delay_seconds` sont portes par la @task."""
    assert dire_bonjour.retries == NB_RETRIES
    assert dire_bonjour.retry_delay_seconds == 1


# [PÉDAGOGIE] BLOC — un nom explicite rend les logs et l'interface lisibles.
def test_les_noms_sont_explicites():
    """Le flow et la tache portent un nom choisi, pas celui de la fonction."""
    assert hello.name == "hello"
    assert dire_bonjour.name == "dire-bonjour"


# [PÉDAGOGIE] BLOC — la tache reste appelable HORS flow : utile pour la tester isolement.
def test_la_tache_est_appelable_hors_flow():
    """`dire_bonjour.fn(...)` appelle la fonction brute, sans Prefect.

    Utile pour tester la logique metier sans payer le cout de l'orchestration.
    """
    assert dire_bonjour.fn("Aelion") == "Bonjour Aelion !"
