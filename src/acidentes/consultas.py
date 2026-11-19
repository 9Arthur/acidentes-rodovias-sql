"""Executa as consultas da pasta sql/, uma pergunta por arquivo (AR-7)."""

from pathlib import Path

import psycopg

PASTA = Path(__file__).resolve().parents[2] / "sql"


def ler(nome: str) -> str:
    return (PASTA / f"{nome}.sql").read_text(encoding="utf-8")


def executar(conn: psycopg.Connection, nome: str) -> tuple[list[str], list[tuple]]:
    """Roda sql/<nome>.sql e devolve os nomes das colunas e as linhas.

    Não faz commit nem rollback: a transação é de quem abriu a conexão.
    """
    cursor = conn.execute(ler(nome))
    return [coluna.name for coluna in cursor.description], cursor.fetchall()
