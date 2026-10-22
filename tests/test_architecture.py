import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "dropen3"


def test_all_source_modules_parse():
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_no_portuguese_identifiers_in_public_workflow_names():
    forbidden = ("histerese", "angulo", "pontos", "contorno", "impacto", "desenhar", "calcular", "processar", "selecionar")
    for path in ROOT.rglob("*.py"):
        code = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(code):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                assert not any(word in node.name for word in forbidden), (path, node.name)
