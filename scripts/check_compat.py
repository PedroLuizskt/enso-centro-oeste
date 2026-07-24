#!/usr/bin/env python3
"""
Verificacao de compatibilidade do codigo com a versao minima suportada.

O pyproject declara requires-python = ">=3.10", mas o interpretador usado no
desenvolvimento pode ser mais novo e aceitar sintaxe que versoes anteriores
rejeitam. O caso classico e a f-string com quebra de linha dentro da expressao,
liberada apenas no Python 3.12 (PEP 701): o codigo roda sem queixa em 3.12 e
falha com SyntaxError em 3.10/3.11.

Este script compila todos os arquivos .py do projeto contra a gramatica das
versoes alvo, sem executa-los.

Uso:
    python scripts/check_compat.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALVOS = ((3, 10), (3, 11), (3, 12))
IGNORAR = {"__pycache__", ".venv", "venv", "build", "dist", ".git"}


def arquivos_py():
    for p in sorted(ROOT.rglob("*.py")):
        if not any(parte in IGNORAR for parte in p.parts):
            yield p


def main() -> int:
    falhas = []
    total = 0
    for caminho in arquivos_py():
        total += 1
        codigo = caminho.read_text(encoding="utf-8")
        for versao in ALVOS:
            try:
                ast.parse(codigo, filename=str(caminho), feature_version=versao)
            except SyntaxError as exc:
                rel = caminho.relative_to(ROOT)
                falhas.append((rel, versao, exc.lineno, exc.msg))
                break

    print(f"Arquivos verificados: {total}")
    print(f"Versoes alvo: {', '.join(f'{a}.{b}' for a, b in ALVOS)}")
    if falhas:
        print("\n[ERRO] Incompatibilidades encontradas:\n")
        for rel, versao, linha, msg in falhas:
            print(f"  {rel}  (Python {versao[0]}.{versao[1]}, linha {linha})")
            print(f"    {msg}")
        return 1
    print("[OK] Todo o codigo e compativel com Python 3.10+")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
