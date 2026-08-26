# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — FORMATION/EXERCICES/tp_api_m25_v1_20260823/scripts/validate_model_card.py
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

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
ALLOWED_STATUSES = {"mesure", "a produire", "non mesure", "a confirmer", "benchmark externe"}
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
REQUIRED_SECTIONS = {
    "niveau metier",
    "niveau technique / maintenance",
    "niveau conformite ai act",
}
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
C5_FIELDS = {
    "artefact et version",
    "donnees, split temporel et empreinte",
    "metriques et seuil",
    "mlflow run_id",
}
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
MARINE_MARKERS = ("0,41", "0.41", "0,62", "0.62", "16,6", "202,6", "612,8", "0,158", "0,352")
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
FIELD_RE = re.compile(r"^-\s*([^:]+):\s*\[([^]]+)]\s*(.*)$")
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
RUN_ID_RE = re.compile(r"\b(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\b", re.I)
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
PROOF_RE = re.compile(r"\bpreuve=([^\s;]+)")


# [PÉDAGOGIE] BLOC `normalized` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : value ; preuve : l'appelant doit pouvoir vérifier la sortie ou
# [PÉDAGOGIE] l'effet de bord annoncé.
def normalized(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return re.sub(r"\s+", " ", plain.strip().lower())


# [PÉDAGOGIE] TYPE `Field` — regroupe un état cohérent et le contrat des opérations associées.
# [PÉDAGOGIE] THÉORIE — nommer ce type rend les invariants visibles et facilite les tests à la
# [PÉDAGOGIE] frontière.
@dataclass(frozen=True)
class Field:
    section: str
    name: str
    status: str
    value: str
    line: int


# [PÉDAGOGIE] BLOC `parse_card` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : text ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def parse_card(text: str) -> tuple[set[str], list[Field]]:
    sections: set[str] = set()
    fields: list[Field] = []
    current = ""
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for line_number, line in enumerate(text.splitlines(), start=1):
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if line.startswith("## "):
            current = normalized(re.sub(r"^\d+\.\s*", "", line[3:]))
            sections.add(current)
            continue
        match = FIELD_RE.match(line)
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if match:
            fields.append(
                Field(
                    section=current,
                    name=normalized(match.group(1)),
                    status=normalized(match.group(2)),
                    value=match.group(3).strip(),
                    line=line_number,
                )
            )
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return sections, fields


# [PÉDAGOGIE] BLOC `resolve_proof` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : project_root, raw_path ; preuve : l'appelant doit pouvoir
# [PÉDAGOGIE] vérifier la sortie ou l'effet de bord annoncé.
def resolve_proof(project_root: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path.strip("\"'"))
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if candidate.is_absolute():
        # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et
        # [PÉDAGOGIE] son sens doivent rester stables.
        return None
    resolved = (project_root / candidate).resolve()
    # [PÉDAGOGIE] ERREUR — cette frontière distingue le chemin nominal de la stratégie explicite
    # [PÉDAGOGIE] de récupération.
    try:
        resolved.relative_to(project_root)
    except ValueError:
        # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et
        # [PÉDAGOGIE] son sens doivent rester stables.
        return None
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return resolved


# [PÉDAGOGIE] BLOC `validate` — garde-fou : refuser tôt un état incomplet plutôt que propager une
# [PÉDAGOGIE] erreur ambiguë.
# [PÉDAGOGIE] CONTRAT — entrées : card, project_root, require_c5 ; preuve : le message et le code
# [PÉDAGOGIE] d'échec doivent permettre de corriger la cause.
def validate(card: Path, project_root: Path, require_c5: bool) -> tuple[list[str], bool]:
    text = card.read_text(encoding="utf-8")
    sections, fields = parse_card(text)
    errors: list[str] = []

    missing_sections = sorted(REQUIRED_SECTIONS - sections)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if missing_sections:
        errors.append("SECTIONS_MANQUANTES=" + ",".join(missing_sections))

    by_name = {field.name: field for field in fields}
    missing_c5 = sorted(C5_FIELDS - set(by_name))
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if missing_c5:
        errors.append("CHAMPS_C5_MANQUANTS=" + ",".join(missing_c5))

    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for field in fields:
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if field.status not in ALLOWED_STATUSES:
            errors.append(f"L{field.line}:STATUT_INCONNU={field.status}")
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if field.status == "mesure":
            proof_match = PROOF_RE.search(field.value)
            # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
            # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
            if not proof_match:
                errors.append(f"L{field.line}:PREUVE_REQUISE={field.name}")
                continue
            proof = resolve_proof(project_root, proof_match.group(1))
            # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
            # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
            if proof is None or not proof.is_file():
                errors.append(f"L{field.line}:PREUVE_ABSENTE_OU_HORS_PROJET={proof_match.group(1)}")
            # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
            # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
            if field.name == "mlflow run_id":
                run_match = RUN_ID_RE.search(field.value)
                # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
                # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
                if not run_match:
                    errors.append(f"L{field.line}:RUN_ID_INVALIDE")
                # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
                # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
                elif proof and proof.is_file():
                    evidence = proof.read_text(encoding="utf-8", errors="replace")
                    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire
                    # [PÉDAGOGIE] séparément le cas vrai et le cas faux.
                    if run_match.group(0) not in evidence:
                        errors.append(f"L{field.line}:RUN_ID_ABSENT_DE_LA_PREUVE")

    conformite = by_name.get("classification reglementaire")
    required_phrase = "a confirmer avec le referent conformite"
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if conformite is None:
        errors.append("CLASSIFICATION_REGLEMENTAIRE_MANQUANTE")
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    elif conformite.status != "a confirmer" or required_phrase not in normalized(conformite.value):
        errors.append("CLASSIFICATION_AI_ACT_NON_PRUDENTE")

    current = ""
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for line_number, line in enumerate(text.splitlines(), start=1):
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if line.startswith("## "):
            current = normalized(re.sub(r"^\d+\.\s*", "", line[3:]))
        # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément
        # [PÉDAGOGIE] le cas vrai et le cas faux.
        if (
            any(marker in line for marker in MARINE_MARKERS)
            and current != "benchmark externe distinct"
        ):
            errors.append(f"L{line_number}:BENCHMARK_MARINE_HORS_SECTION_4")

    c5_ready = (
        all(name in by_name and by_name[name].status == "mesure" for name in C5_FIELDS)
        and not errors
    )
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return errors, c5_ready


# [PÉDAGOGIE] BLOC `main` — orchestration : rendre l'ordre, les dépendances et les points d'échec
# [PÉDAGOGIE] visibles.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : chaque étape doit annoncer
# [PÉDAGOGIE] sa preuve avant que la suivante ne commence.
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide structure et provenance d'une Model Card M25."
    )
    parser.add_argument("card", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--require-c5", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    card = args.card if args.card.is_absolute() else (project_root / args.card)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not card.is_file():
        print(f"MODEL_CARD_ABSENTE={card}", file=sys.stderr)
        # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et
        # [PÉDAGOGIE] son sens doivent rester stables.
        return 2

    errors, c5_ready = validate(card.resolve(), project_root, args.require_c5)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if errors:
        # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur
        # [PÉDAGOGIE] un invariant stable.
        for error in errors:
            print(f"ERROR={error}", file=sys.stderr)
        print("STRUCTURE=FAIL")
        print("C4_EVIDENCE=NOT_READY")
        print("C5_EVIDENCE=NOT_READY")
        # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et
        # [PÉDAGOGIE] son sens doivent rester stables.
        return 2

    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if args.require_c5 and not c5_ready:
        print("ERROR=C5_PREUVES_REELLES_INCOMPLETES", file=sys.stderr)
        print("STRUCTURE=PASS")
        print("C4_EVIDENCE=READY_FOR_REVIEW")
        print("C5_EVIDENCE=NOT_READY")
        # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et
        # [PÉDAGOGIE] son sens doivent rester stables.
        return 2

    print("STRUCTURE=PASS")
    print("C4_EVIDENCE=READY_FOR_REVIEW")
    print(f"C5_EVIDENCE={'READY_FOR_REVIEW' if c5_ready else 'NOT_READY'}")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return 0


# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if __name__ == "__main__":
    # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
    # [PÉDAGOGIE] suivantes.
    raise SystemExit(main())
