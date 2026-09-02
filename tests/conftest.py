# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — tests/conftest.py
# [PÉDAGOGIE] MODULE  — Sprint 3 — lisibilite de la suite de tests
# [PÉDAGOGIE] RÔLE    — Afficher CHAQUE cas de test avec son issue, puis un tableau de synthese
# [PÉDAGOGIE]           par fichier avec taux d'execution et de reussite.
# [PÉDAGOGIE] THÉORIE — une suite affichee en points ne renseigne pas : on ne sait ni QUOI a
# [PÉDAGOGIE]           tourne, ni ce qui a ete SAUTE
# [PÉDAGOGIE]           • un test ignore n'est pas un test reussi : il ne prouve RIEN
# [PÉDAGOGIE]           • le taux d'execution mesure ce qui a tourne, pas ce qui a reussi
# [PÉDAGOGIE] À VOIR  — Le taux d'execution chute des qu'une stack manque : c'est le signal.
# [PÉDAGOGIE] PIÈGE   — Confondre « taux d'execution » et « couverture de code ». La couverture
# [PÉDAGOGIE]           de code se mesure avec pytest-cov, sur les LIGNES du code source.
# [PÉDAGOGIE] GARDE   — Aucune dependance ajoutee : uniquement des hooks pytest.
# [PÉDAGOGIE] ============================================================================

"""Affichage detaille de la suite de tests.

Trois niveaux, choisis par `--recap` :

    --recap=detail   chaque cas de test, groupe par fichier (defaut)
    --recap=resume   seulement le tableau de synthese
    --recap=off      rien (comportement pytest standard)

DEUX TAUX, A NE PAS CONFONDRE :

    Taux d'execution = (passes + echoues) / total
        Combien de tests ont REELLEMENT tourne. Les ignores le font chuter.
        C'est la mesure demandee ici : elle rend visible ce qui n'a pas ete verifie.

    Taux de reussite = passes / (passes + echoues)
        Parmi ceux qui ont tourne, combien passent.

    Couverture de code = mesure DIFFERENTE, sur les lignes du code source.
        Elle s'obtient avec pytest-cov : `uv run pytest --cov=indusense`.
        Un test ignore ne couvre rien, donc les deux notions se rejoignent
        dans les faits — mais elles ne mesurent pas la meme chose.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

# [PÉDAGOGIE] CONSTANTE / CONTRAT — un symbole, un libelle et une couleur par issue.
# [PÉDAGOGIE] Le symbole suffit quand la couleur est indisponible (redirection, CI, daltonisme).
ISSUES: dict[str, tuple[str, str, dict]] = {
    "passed": ("v", "OK", {"green": True}),
    "failed": ("X", "ECHEC", {"red": True}),
    "error": ("E", "ERREUR", {"red": True, "bold": True}),
    "skipped": ("-", "IGNORE", {"yellow": True}),
    "xfailed": ("x", "ECHEC ATTENDU", {"yellow": True}),
    "xpassed": ("!", "PASSE INATTENDU", {"yellow": True}),
}

# fichier -> issue -> nombre
_compte: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
# fichier -> [(nom du test, issue, duree)]
_detail: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
_duree: dict[str, float] = defaultdict(float)


# [PÉDAGOGIE] BLOC `pytest_addoption` — expose une option en ligne de commande. Elle peut
# [PÉDAGOGIE] aussi etre fixee une fois pour toutes dans `addopts` de pyproject.toml.
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--recap",
        action="store",
        default="detail",
        choices=("detail", "resume", "off"),
        help="niveau du recapitulatif : detail (chaque test), resume (tableau), off",
    )


# [PÉDAGOGIE] BLOC `pytest_runtest_logreport` — appele apres CHAQUE phase (setup, call,
# [PÉDAGOGIE] teardown) de CHAQUE test. Sans filtrage on compterait trois fois le meme test.
@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Accumule l'issue de chaque test, par fichier."""
    fichier, _, nom = report.nodeid.partition("::")
    _duree[fichier] += report.duration

    issue = None
    # Un test ignore l'est des le `setup` ; un test normal se juge sur `call`.
    if report.when == "setup" and report.skipped:
        issue = "skipped"
    elif report.when == "setup" and report.failed:
        # Echec dans une fixture : le test n'a jamais demarre.
        issue = "error"
    elif report.when == "call":
        if report.passed:
            issue = "xpassed" if hasattr(report, "wasxfail") else "passed"
        elif report.failed:
            issue = "failed"
        elif report.skipped:
            issue = "xfailed" if hasattr(report, "wasxfail") else "skipped"

    if issue:
        _compte[fichier][issue] += 1
        _detail[fichier].append((nom, issue, report.duration))


def _taux(issues: dict[str, int]) -> tuple[int, int, int, float, float]:
    """Calcule total, executes, reussis, taux d'execution, taux de reussite."""
    total = sum(issues.values())
    executes = total - issues.get("skipped", 0)
    reussis = issues.get("passed", 0) + issues.get("xfailed", 0)
    t_exec = 100 * executes / total if total else 0.0
    t_reussite = 100 * reussis / executes if executes else 0.0
    return total, executes, reussis, t_exec, t_reussite


def _style_fichier(issues: dict[str, int]) -> dict:
    """Couleur du nom de fichier : celle de son issue LA PLUS GRAVE."""
    if issues.get("failed") or issues.get("error"):
        return {"red": True}
    if issues.get("skipped") and not issues.get("passed"):
        return {"yellow": True}
    if issues.get("skipped"):
        return {"cyan": True}
    return {"green": True}


# [PÉDAGOGIE] BLOC `pytest_terminal_summary` — appele une seule fois, a la toute fin.
def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Affiche le detail par cas, puis le tableau de synthese."""
    niveau = config.getoption("--recap")
    if niveau == "off" or not _compte:
        return

    tr = terminalreporter

    # =========================================================================
    # NIVEAU 1 — le detail : chaque cas de test, groupe par fichier
    # =========================================================================
    if niveau == "detail":
        tr.write_sep("=", "Detail des cas de test", bold=True)
        for fichier in sorted(_detail):
            issues = _compte[fichier]
            total, _, _, t_exec, _ = _taux(issues)

            tr.write("\n  " + fichier, bold=True, **_style_fichier(issues))
            tr.write(f"  ({total} cas, {t_exec:.0f} % executes)\n")

            for nom, issue, duree in _detail[fichier]:
                symbole, libelle, style = ISSUES[issue]
                tr.write(f"    {symbole} ", **style)
                tr.write(f"{nom:<62}")
                tr.write(f"{libelle:<16}", **style)
                tr.write(f"{duree * 1000:>7.0f} ms\n")

    # =========================================================================
    # NIVEAU 2 — la synthese : un tableau, une ligne par fichier
    # =========================================================================
    tr.write_sep("=", "Synthese par fichier de test", bold=True)

    largeur = max(max(len(f) for f in _compte), 30) + 2
    entete = (
        f"  {'Fichier':<{largeur}}{'Cas':>5}{'OK':>6}{'KO':>5}"
        f"{'Ign.':>6}{'Exec.':>9}{'Reuss.':>9}{'Duree':>9}"
    )
    tr.write(entete + "\n", bold=True)
    tr.write("  " + "-" * (len(entete) - 2) + "\n")

    cumul: dict[str, int] = defaultdict(int)

    for fichier in sorted(_compte):
        issues = _compte[fichier]
        total, executes, reussis, t_exec, t_reussite = _taux(issues)
        echoues = issues.get("failed", 0) + issues.get("error", 0)
        ignores = issues.get("skipped", 0)

        for issue, nombre in issues.items():
            cumul[issue] += nombre

        tr.write(f"  {fichier:<{largeur}}", **_style_fichier(issues))
        tr.write(f"{total:>5}")
        tr.write(f"{reussis:>6}", **({"green": True} if reussis else {}))
        tr.write(f"{echoues:>5}", **({"red": True} if echoues else {}))
        tr.write(f"{ignores:>6}", **({"yellow": True} if ignores else {}))
        # Le taux d'execution est la colonne qui compte : il tombe des qu'un
        # test est saute, donc des qu'une garantie n'est PAS verifiee.
        tr.write(f"{t_exec:>8.0f}%", **({"green": True} if t_exec == 100 else {"yellow": True}))
        tr.write(
            f"{t_reussite:>8.0f}%", **({"green": True} if t_reussite == 100 else {"red": True})
        )
        tr.write(f"{_duree[fichier]:>8.2f}s\n")

    # --- Ligne de total -------------------------------------------------------
    tr.write("  " + "-" * (len(entete) - 2) + "\n")
    total, executes, reussis, t_exec, t_reussite = _taux(cumul)
    echoues = cumul.get("failed", 0) + cumul.get("error", 0)
    ignores = cumul.get("skipped", 0)

    tr.write(f"  {'TOTAL':<{largeur}}", bold=True)
    tr.write(f"{total:>5}", bold=True)
    tr.write(f"{reussis:>6}", green=True, bold=True)
    tr.write(f"{echoues:>5}", **({"red": True, "bold": True} if echoues else {"bold": True}))
    tr.write(f"{ignores:>6}", **({"yellow": True, "bold": True} if ignores else {"bold": True}))
    tr.write(f"{t_exec:>8.0f}%", **({"green": True} if t_exec == 100 else {"yellow": True}))
    tr.write(f"{t_reussite:>8.0f}%", **({"green": True} if t_reussite == 100 else {"red": True}))
    tr.write(f"{sum(_duree.values()):>8.2f}s\n")

    # =========================================================================
    # RAPPEL — un test ignore ne prouve rien
    # =========================================================================
    if ignores:
        tr.write(
            f"\n  {ignores} cas sur {total} n'ont PAS ete executes "
            f"(taux d'execution : {t_exec:.0f} %).\n",
            yellow=True,
        )
        tr.write("  Un test ignore ne prouve rien. Detail : pytest -rs\n", yellow=True)
    else:
        tr.write("\n  Taux d'execution : 100 % — tous les cas ont tourne.\n", green=True)
