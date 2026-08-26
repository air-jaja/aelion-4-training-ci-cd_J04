# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — FORMATION/EXERCICES/tp_api_m25_v1_20260823/tests/test_model_card_gate.py
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

import subprocess
import sys
from pathlib import Path

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
ROOT = Path(__file__).parents[1]
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
VALIDATOR = ROOT / "scripts" / "validate_model_card.py"
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
TEMPLATE = ROOT / "tests" / "fixtures" / "model_card_template.md"


# [PÉDAGOGIE] BLOC `run_gate` — orchestration : rendre l'ordre, les dépendances et les points
# [PÉDAGOGIE] d'échec visibles.
# [PÉDAGOGIE] CONTRAT — entrées : card, project_root, require_c5 ; preuve : chaque étape doit
# [PÉDAGOGIE] annoncer sa preuve avant que la suivante ne commence.
def run_gate(
    card: Path, project_root: Path, *, require_c5: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(VALIDATOR),
        str(card),
        "--project-root",
        str(project_root),
    ]
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if require_c5:
        command.append("--require-c5")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return subprocess.run(command, check=False, capture_output=True, text=True)


# [PÉDAGOGIE] BLOC `test_template_passes_structure_but_keeps_c5_not_ready` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_template_passes_structure_but_keeps_c5_not_ready() -> None:
    result = run_gate(TEMPLATE, ROOT)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert result.returncode == 0, result.stderr
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert "STRUCTURE=PASS" in result.stdout
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert "C5_EVIDENCE=NOT_READY" in result.stdout


# [PÉDAGOGIE] BLOC `test_strict_c5_rejects_the_unmeasured_template` — ce test transforme un
# [PÉDAGOGIE] comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : la dernière assertion est
# [PÉDAGOGIE] l'oracle : son échec doit pointer la garantie cassée.
def test_strict_c5_rejects_the_unmeasured_template() -> None:
    result = run_gate(TEMPLATE, ROOT, require_c5=True)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert result.returncode == 2
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert "C5_PREUVES_REELLES_INCOMPLETES" in result.stderr


# [PÉDAGOGIE] BLOC `test_strict_c5_accepts_measured_fields_with_local_evidence` — ce test
# [PÉDAGOGIE] transforme un comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : tmp_path ; preuve : la dernière assertion est l'oracle : son
# [PÉDAGOGIE] échec doit pointer la garantie cassée.
def test_strict_c5_accepts_measured_fields_with_local_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    run_id = "0123456789abcdef0123456789abcdef"
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for filename, content in {
        "artifact.txt": "model=rf.joblib version=0.1.0",
        "data.txt": "split=temporel sha256=abc",
        "metrics.txt": "pr_auc=mesuree threshold=mesure",
        "mlflow.txt": f"run_id={run_id}",
    }.items():
        (evidence / filename).write_text(content, encoding="utf-8")

    card = tmp_path / "model_card.md"
    card.write_text(
        TEMPLATE.read_text(encoding="utf-8")
        .replace(
            "Artefact et version : [à produire]",
            "Artefact et version : [mesuré] preuve=evidence/artifact.txt",
        )
        .replace(
            "Données, split temporel et empreinte : [à produire]",
            "Données, split temporel et empreinte : [mesuré] preuve=evidence/data.txt",
        )
        .replace(
            "Métriques et seuil : [à produire]",
            "Métriques et seuil : [mesuré] preuve=evidence/metrics.txt",
        )
        .replace(
            "MLflow run_id : [à produire]",
            f"MLflow run_id : [mesuré] {run_id} preuve=evidence/mlflow.txt",
        ),
        encoding="utf-8",
    )

    result = run_gate(card, tmp_path, require_c5=True)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert result.returncode == 0, result.stderr
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert "C5_EVIDENCE=READY_FOR_REVIEW" in result.stdout


# [PÉDAGOGIE] BLOC `test_marine_value_outside_benchmark_section_is_rejected` — ce test transforme
# [PÉDAGOGIE] un comportement attendu en contrat de non-régression.
# [PÉDAGOGIE] CONTRAT — entrées : tmp_path ; preuve : la dernière assertion est l'oracle : son
# [PÉDAGOGIE] échec doit pointer la garantie cassée.
def test_marine_value_outside_benchmark_section_is_rejected(tmp_path: Path) -> None:
    card = tmp_path / "model_card.md"
    card.write_text(
        TEMPLATE.read_text(encoding="utf-8").replace(
            "Finalité et utilisateurs : [à produire]",
            "Finalité et utilisateurs : [à produire] seuil 0,41",
        ),
        encoding="utf-8",
    )
    result = run_gate(card, tmp_path)
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert result.returncode == 2
    # [PÉDAGOGIE] ORACLE — l'assertion compare le résultat observé au contrat attendu par ce test.
    assert "BENCHMARK_MARINE_HORS_SECTION_4" in result.stderr
