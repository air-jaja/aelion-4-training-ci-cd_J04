# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_check_image.py
# [PÉDAGOGIE] MODULE  — M27 — controle qualite d'image
# [PÉDAGOGIE] RÔLE    — Tester la logique de decision SANS demon Docker.
# [PÉDAGOGIE] THÉORIE — Separer la mesure (I/O) du verdict (pur) rend le verdict testable
# [PÉDAGOGIE]           • la CI n'a pas toujours Docker ; la logique doit rester verifiable
# [PÉDAGOGIE]           • `evaluer` ne prend que des faits deja collectes
# [PÉDAGOGIE] À VOIR  — Aucun de ces tests n'appelle `docker`. C'est le but.
# [PÉDAGOGIE] PIÈGE   — Tester `mesurer()` ici demanderait Docker : ce n'est pas son role.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_image import (  # noqa: E402
    OCTETS_PAR_MO,
    calculer_budget,
    charger_budget,
    ecrire_budget,
    evaluer,
    formater_rapport,
)

BUDGET = {
    "image": "indusense-api:m27",
    "mesure_mb": 180,
    "marge_pct": 15,
    "max_mb": 207,
    "mesure_le": "2026-08-26",
    "variante": "A",
}

BUDGET_B = {**BUDGET, "variante": "B"}


def _mo(valeur: float) -> int:
    return int(valeur * OCTETS_PAR_MO)


# =============================================================================
# Le calcul du budget
# =============================================================================


# [PÉDAGOGIE] BLOC — le budget derive de la MESURE, jamais d'un chiffre rond choisi a la main.
def test_budget_ajoute_la_marge():
    """180 Mo + 15 % donne exactement 207 Mo."""
    assert calculer_budget(180, marge_pct=15) == 207


# [PÉDAGOGIE] BLOC — marge nulle : le budget reste strictement au-dessus de la mesure.
def test_budget_sans_marge_egale_la_mesure():
    """Sans marge, le budget vaut la mesure : la comparaison accepte l'egalite."""
    assert calculer_budget(180, marge_pct=0) == 180


# [PÉDAGOGIE] BLOC — le piege du flottant : int(180 * 1.15) donnerait 206.
def test_budget_ne_souffre_pas_de_l_erreur_flottante():
    """180 * 1.15 vaut 206.99999999999997 en flottant. Le budget doit valoir 207."""
    assert int(180 * 1.15) == 206  # ce que donnerait un calcul naif
    assert calculer_budget(180, marge_pct=15) == 207


# [PÉDAGOGIE] BLOC — une marge plus large donne un budget plus large. Propriete, pas cas isole.
@pytest.mark.parametrize("marge", [0, 5, 15, 50])
def test_budget_croit_avec_la_marge(marge):
    assert calculer_budget(180, marge_pct=marge) >= 180


# =============================================================================
# Le verdict
# =============================================================================


# [PÉDAGOGIE] BLOC — le cas nominal : rien a signaler.
def test_image_conforme_ne_produit_aucun_probleme():
    problemes = evaluer(_mo(180), "appuser", 10001, BUDGET, healthcheck=True, modele_present=True)

    assert problemes == []


# [PÉDAGOGIE] BLOC — juste sous le budget : accepte. La limite doit etre franche.
def test_taille_au_budget_exact_est_acceptee():
    problemes = evaluer(_mo(207), "appuser", 10001, BUDGET, healthcheck=True, modele_present=True)

    assert problemes == []


# [PÉDAGOGIE] BLOC — au-dessus : refus, avec le depassement CHIFFRE depuis la calibration.
def test_depassement_de_budget_est_signale_avec_lecart():
    problemes = evaluer(_mo(230), "appuser", 10001, BUDGET, healthcheck=True, modele_present=True)

    assert len(problemes) == 1
    assert "230" in problemes[0]
    assert "+50" in problemes[0]  # 230 - 180 mesures a la calibration


# [PÉDAGOGIE] BLOC — USER root declare : refus.
def test_user_root_declare_est_refuse():
    problemes = evaluer(_mo(180), "root", 0, BUDGET, healthcheck=True, modele_present=True)

    assert any("USER declare" in p for p in problemes)


# [PÉDAGOGIE] BLOC — le piege : aucun USER dans le Dockerfile. Le champ est VIDE, pas "root".
def test_user_absent_est_refuse():
    """Un Dockerfile sans USER laisse root, mais .Config.User est une chaine vide."""
    problemes = evaluer(_mo(180), "", None, BUDGET, healthcheck=True, modele_present=True)

    assert any("USER declare" in p for p in problemes)


# [PÉDAGOGIE] BLOC — "0" est root ecrit en UID. Meme verdict.
def test_user_zero_est_refuse():
    problemes = evaluer(_mo(180), "0", 0, BUDGET, healthcheck=True, modele_present=True)

    assert any("USER declare" in p for p in problemes)


# [PÉDAGOGIE] BLOC — declare non-root mais s'executant en root : le controle en deux temps sert
# [PÉDAGOGIE] exactement a ca.
def test_uid_effectif_root_est_refuse_malgre_user_declare():
    """USER appuser declare, mais le conteneur tourne en UID 0."""
    problemes = evaluer(_mo(180), "appuser", 0, BUDGET, healthcheck=True, modele_present=True)

    assert any("UID 0" in p for p in problemes)


# [PÉDAGOGIE] BLOC — un UID non-root mais inattendu est signale sans etre confondu avec root.
def test_uid_inattendu_est_signale():
    problemes = evaluer(_mo(180), "appuser", 1000, BUDGET, healthcheck=True, modele_present=True)

    assert any("UID effectif 1000" in p for p in problemes)


# [PÉDAGOGIE] BLOC — UID indeterminable (image sans shell) : on ne bloque pas dessus.
def test_uid_indeterminable_ne_bloque_pas():
    """Une image distroless n'a pas `id` : on ne peut pas conclure, on n'invente pas."""
    problemes = evaluer(_mo(180), "appuser", None, BUDGET, healthcheck=True, modele_present=True)

    assert problemes == []


# [PÉDAGOGIE] BLOC — sonde absente : signalee.
def test_healthcheck_absent_est_signale():
    problemes = evaluer(_mo(180), "appuser", 10001, BUDGET, healthcheck=False, modele_present=True)

    assert any("HEALTHCHECK" in p for p in problemes)


# [PÉDAGOGIE] BLOC — plusieurs ecarts sont TOUS rapportes, pas seulement le premier.
def test_tous_les_problemes_sont_rapportes():
    """Un rapport partiel ferait perdre un cycle de correction par probleme."""
    problemes = evaluer(_mo(300), "root", 0, BUDGET, healthcheck=False, modele_present=True)

    assert len(problemes) == 4


# =============================================================================
# Le rapport et la persistance
# =============================================================================


# [PÉDAGOGIE] BLOC — le rapport s'affiche meme quand tout va bien : on veut voir la marge.
def test_rapport_affiche_la_marge_restante():
    rapport = formater_rapport(_mo(180), BUDGET, [])

    assert "180 Mo" in rapport
    assert "+27" in rapport  # 207 - 180


# [PÉDAGOGIE] BLOC — aller-retour : ce qui est ecrit est relu a l'identique.
def test_budget_ecrit_puis_relu(tmp_path):
    chemin = tmp_path / "docker" / "image_budget.json"
    ecrit = ecrire_budget(chemin, "indusense-api:m27", _mo(180), marge_pct=15)
    relu = charger_budget(chemin)

    assert relu == ecrit
    assert relu["max_mb"] == 207


# [PÉDAGOGIE] BLOC — le budget est du JSON lisible : il doit se relire dans une revue de PR.
def test_budget_est_json_indente(tmp_path):
    chemin = tmp_path / "image_budget.json"
    ecrire_budget(chemin, "indusense-api:m27", _mo(180), marge_pct=15)
    contenu = chemin.read_text(encoding="utf-8")

    assert contenu.startswith("{\n")
    assert json.loads(contenu)["mesure_mb"] == 180


# [PÉDAGOGIE] BLOC — budget absent : message actionnable, pas une trace obscure.
def test_budget_absent_explique_comment_calibrer(tmp_path):
    with pytest.raises(SystemExit) as capture:
        charger_budget(tmp_path / "inexistant.json")

    assert "--calibrate" in str(capture.value)


# =============================================================================
# La presence du modele — une attente qui DEPEND de la variante
# =============================================================================


# [PÉDAGOGIE] BLOC — variante A : le modele doit etre dans l'image.
def test_variante_a_exige_le_modele_embarque():
    """Sans modele, une image de variante A est incomplete."""
    problemes = evaluer(_mo(180), "appuser", 10001, BUDGET, healthcheck=True, modele_present=False)

    assert any("modele absent" in p for p in problemes)


# [PÉDAGOGIE] BLOC — variante A avec modele : conforme.
def test_variante_a_avec_modele_est_conforme():
    problemes = evaluer(_mo(180), "appuser", 10001, BUDGET, healthcheck=True, modele_present=True)

    assert problemes == []


# [PÉDAGOGIE] BLOC — variante B : l'ABSENCE est normale. Le service repondra 503 sur /ready.
def test_variante_b_accepte_l_absence_de_modele():
    """En variante B, le modele est monte au demarrage : l'image ne le contient pas."""
    problemes = evaluer(
        _mo(180), "appuser", 10001, BUDGET_B, healthcheck=True, modele_present=False
    )

    assert problemes == []


# [PÉDAGOGIE] BLOC — variante B avec modele embarque : incoherence signalee.
def test_variante_b_refuse_un_modele_embarque():
    """Embarquer le modele en variante B alourdit l'image et la fige pour rien."""
    problemes = evaluer(_mo(180), "appuser", 10001, BUDGET_B, healthcheck=True, modele_present=True)

    assert any("variante B" in p for p in problemes)


# [PÉDAGOGIE] BLOC — budget ancien, sans champ « variante » : on suppose A (retro-compatibilite).
def test_budget_sans_variante_suppose_la_variante_a():
    budget_ancien = {k: v for k, v in BUDGET.items() if k != "variante"}
    problemes = evaluer(
        _mo(180), "appuser", 10001, budget_ancien, healthcheck=True, modele_present=False
    )

    assert any("modele absent" in p for p in problemes)


# [PÉDAGOGIE] BLOC — la variante figure dans le rapport : on doit savoir ce qu'on a construit.
def test_rapport_affiche_la_variante():
    rapport = formater_rapport(_mo(180), BUDGET_B, [])

    assert "Variante   : B" in rapport
