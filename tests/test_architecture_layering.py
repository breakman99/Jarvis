from __future__ import annotations

from pathlib import Path


def test_domain_should_not_depend_on_infrastructure_imports() -> None:
    project_root = Path(__file__).resolve().parents[1]
    domain_root = project_root / "src" / "domain"
    violations: list[str] = []
    for py_file in domain_root.rglob("*.py"):
        rel = py_file.relative_to(project_root)
        text = py_file.read_text(encoding="utf-8")
        if "from src.infrastructure" in text or "import src.infrastructure" in text:
            violations.append(str(rel))
    assert not violations, f"domain 层不应依赖 infrastructure 层: {violations}"

