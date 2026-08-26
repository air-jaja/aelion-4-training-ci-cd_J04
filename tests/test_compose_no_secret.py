import subprocess
from pathlib import Path


def _tracked(path: str) -> bool:
    out = subprocess.run(["git", "ls-files", path], capture_output=True, text=True).stdout
    return bool(out.strip())


def test_env_is_gitignored():
    assert not _tracked(".env"), ".env ne doit jamais être versionné"
    assert _tracked(".env.example"), "seul .env.example est committé"


def test_compose_has_no_plaintext_secret():
    yaml = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}" in yaml  # référencé par variable
    assert "change-me" not in yaml  # aucune valeur en clair
