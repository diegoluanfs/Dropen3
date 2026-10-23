"""Protect the English-only user-interface and source-code naming convention."""
from __future__ import annotations
import re
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'dropen3'
ACCENTED_PORTUGUESE = re.compile('[áàãâéêíóôõúçÁÀÃÂÉÊÍÓÔÕÚÇ]')
LEGACY_NON_ENGLISH_IDENTIFIERS = re.compile(
    r'\b(?:secoes|titulo|conteudo|tem_data|tem_midia|tem_method|mode_tabela|'
    r'pre_impacto|fps_gravacao|largura|pontos|histerese|contorno)\b'
)


def test_application_source_uses_english_language_conventions():
    violations = []
    for source in SOURCE.rglob('*.py'):
        content = source.read_text(encoding='utf-8')
        if ACCENTED_PORTUGUESE.search(content) or LEGACY_NON_ENGLISH_IDENTIFIERS.search(content):
            violations.append(source.relative_to(SOURCE).as_posix())
    assert not violations, f'Non-English language markers remain in application source: {violations}'
