"""Fixture compartilhada: a tabela acidente com as 50 linhas de tests/fixtures/acidentes_50.csv."""

import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

FIXTURE = Path(__file__).parent / "fixtures" / "acidentes_50.csv"


@pytest.fixture(scope="module")
def conn_50():
    """Schema descartável com a tabela acidente e as 50 linhas da fixture.

    Depois da carga a conexão fica em autocommit: um erro de SQL num teste não deixa a
    transação abortada para os seguintes.
    """
    from acidentes.banco import url_do_banco
    from acidentes.carregar import criar_tabela

    nome = f"teste_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(url_do_banco(), autocommit=True) as c:
        c.execute(f"CREATE SCHEMA {nome}")
    try:
        conninfo = make_conninfo(url_do_banco(), options=f"-c search_path={nome}")
        with psycopg.connect(conninfo) as c:
            criar_tabela(c)
            with c.cursor().copy("COPY acidente FROM STDIN (FORMAT csv, HEADER)") as cp:
                cp.write(FIXTURE.read_bytes())
            c.commit()
            c.autocommit = True
            yield c
    finally:
        with psycopg.connect(url_do_banco(), autocommit=True) as c:
            c.execute(f"DROP SCHEMA {nome} CASCADE")
