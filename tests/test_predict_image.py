# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/test_predict_image.py
# [PÉDAGOGIE] MODULE  — M26 — validation des entrees binaires
# [PÉDAGOGIE] RÔLE    — Prouver que /predict-image refuse ce qui n'est pas une image,
# [PÉDAGOGIE]           meme quand le client PRETEND le contraire.
# [PÉDAGOGIE] THÉORIE — Un client hostile controle entierement ce qu'il declare
# [PÉDAGOGIE]           • le nom de fichier, l'extension et le Content-Type sont des AFFIRMATIONS
# [PÉDAGOGIE]           • les premiers octets d'un vrai format sont imposes par ce format
# [PÉDAGOGIE] À VOIR  — Un executable renomme en .png passe la validation du Content-Type
# [PÉDAGOGIE]           et echoue sur la signature : c'est tout l'interet du controle.
# [PÉDAGOGIE] PIÈGE   — Croire qu'une signature valide garantit une image saine. Elle ecarte
# [PÉDAGOGIE]           le grossier, pas une image malformee concue pour le decodeur.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
# FICHIER : tests/test_predict_image.py
# RÔLE    : les trois validations de /predict-image, dans l'ordre du code.
# -----------------------------------------------------------------------------
#   1. fichier vide                  -> 422  (deja en place)
#   2. Content-Type non-image        -> 422  (deja en place)
#   3. contenu non-image             -> 422  (l'ajout de ce jalon)
#
# La validation 3 existe parce que la 2 est declarative : elle croit le client
# sur parole. Un attaquant envoie simplement Content-Type: image/png.
# =============================================================================

import pytest
from fastapi.testclient import TestClient

from indusense.api.main import _ressemble_a_une_image, app

client = TestClient(app)

CLE = {"X-API-Key": "dev-key"}

# Signatures minimales de vrais formats. Le contenu apres l'en-tete importe peu
# ici : on teste la reconnaissance de format, pas le decodage.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"\x00" * 32


# =============================================================================
# PARTIE 1 — La fonction de reconnaissance, isolee
# =============================================================================


# [PÉDAGOGIE] BLOC — les formats attendus sont reconnus. Test parametre : un cas par format.
@pytest.mark.parametrize(
    ("nom", "contenu"),
    [("PNG", PNG), ("JPEG", JPEG), ("GIF", GIF), ("WEBP", WEBP)],
)
def test_signatures_connues_sont_reconnues(nom, contenu):
    """Les formats d'image courants sont acceptes."""
    assert _ressemble_a_une_image(contenu), f"{nom} non reconnu"


# [PÉDAGOGIE] BLOC — ce qui n'est pas une image doit etre rejete.
@pytest.mark.parametrize(
    ("nom", "contenu"),
    [
        ("texte brut", b"Ceci est du texte, pas une image."),
        ("executable Windows", b"MZ\x90\x00\x03\x00\x00\x00"),
        ("ELF Linux", b"\x7fELF\x02\x01\x01\x00"),
        ("archive ZIP", b"PK\x03\x04\x14\x00\x00\x00"),
        ("PDF", b"%PDF-1.7\n"),
        ("script shell", b"#!/bin/sh\nrm -rf /\n"),
    ],
)
def test_contenus_non_image_sont_rejetes(nom, contenu):
    """Aucun de ces formats ne doit passer pour une image."""
    assert not _ressemble_a_une_image(contenu), f"{nom} accepte a tort"


# [PÉDAGOGIE] BLOC — le piege du prefixe partiel : "RIFF" seul n'est pas du WEBP.
def test_riff_sans_webp_est_rejete():
    """Un conteneur RIFF non-WEBP (un WAV, par exemple) est refuse."""
    wav = b"RIFF" + b"\x24\x00\x00\x00" + b"WAVE" + b"\x00" * 32

    assert not _ressemble_a_une_image(wav)


# [PÉDAGOGIE] BLOC — cas limite : un contenu plus court que la signature ne doit pas planter.
def test_contenu_tres_court_ne_leve_pas():
    """Un fichier de deux octets renvoie False, sans exception."""
    assert not _ressemble_a_une_image(b"\x89P")


# =============================================================================
# PARTIE 2 — Le comportement de la route
# =============================================================================


# [PÉDAGOGIE] BLOC — rappel : la validation 1 (fichier vide) reste en place.
def test_fichier_vide_refuse():
    """Un fichier sans contenu renvoie 422."""
    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": ("vide.png", b"", "image/png")},
    )

    assert reponse.status_code == 422


# [PÉDAGOGIE] BLOC — rappel : la validation 2 (Content-Type) reste en place.
def test_content_type_non_image_refuse():
    """Un Content-Type explicitement non-image renvoie 422."""
    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": ("doc.txt", b"du texte", "text/plain")},
    )

    assert reponse.status_code == 422


# [PÉDAGOGIE] BLOC — LE test du jalon : le client ment sur le Content-Type.
def test_contenu_non_image_refuse_malgre_content_type_valide():
    """Un executable declare 'image/png' est refuse sur sa signature.

    C'est le scenario d'attaque reel : le client controle entierement le nom du
    fichier ET le Content-Type. Seuls les octets ne mentent pas.
    """
    executable = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64

    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": ("innocent.png", executable, "image/png")},
    )

    assert reponse.status_code == 422
    assert "contenu" in reponse.json()["detail"].lower()


# [PÉDAGOGIE] BLOC — sans Content-Type, la validation 2 ne s'applique pas : la 3 prend le relais.
def test_contenu_non_image_refuse_sans_content_type():
    """Omettre le Content-Type ne contourne pas la validation."""
    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": ("mystere.bin", b"pas une image du tout", None)},
    )

    assert reponse.status_code == 422


# [PÉDAGOGIE] BLOC — le cas nominal ne doit pas etre casse par l'ajout.
@pytest.mark.parametrize(
    ("nom_fichier", "contenu", "mime"),
    [
        ("photo.png", PNG, "image/png"),
        ("photo.jpg", JPEG, "image/jpeg"),
        ("anim.gif", GIF, "image/gif"),
        ("photo.webp", WEBP, "image/webp"),
    ],
)
def test_vraie_image_acceptee(nom_fichier, contenu, mime):
    """Une image authentique passe les trois validations."""
    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": (nom_fichier, contenu, mime)},
    )

    assert reponse.status_code == 200
    assert reponse.json()["size_bytes"] == len(contenu)


# [PÉDAGOGIE] BLOC — l'ordre des validations : le fichier vide est vu AVANT la signature.
def test_fichier_vide_prioritaire_sur_signature():
    """Un fichier vide renvoie le message du cas vide, pas celui de la signature."""
    reponse = client.post(
        "/predict-image",
        headers=CLE,
        files={"file": ("vide.png", b"", "image/png")},
    )

    assert "vide" in reponse.json()["detail"].lower()


# [PÉDAGOGIE] BLOC — la route reste protegee : l'ajout ne doit pas ouvrir de porte.
def test_route_reste_protegee_par_la_cle():
    """Sans cle API, la route repond 401 avant toute validation."""
    reponse = client.post(
        "/predict-image",
        files={"file": ("photo.png", PNG, "image/png")},
    )

    assert reponse.status_code == 401
