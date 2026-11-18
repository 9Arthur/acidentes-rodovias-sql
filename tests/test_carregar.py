"""carregar: tabela acidente (ficha 2.4) e carga por COPY sem duplicar (AR-6).

Cada teste usa um schema descartável no banco da DATABASE_URL: a tabela acidente
de verdade (schema public) nunca é tocada.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import psycopg
import pytest
from psycopg.conninfo import make_conninfo

COLUNAS = [
    "id",
    "data_hora",
    "uf",
    "br",
    "km",
    "municipio",
    "causa",
    "tipo",
    "classificacao",
    "fase_dia",
    "condicao_meteo",
    "mortos",
    "feridos",
    "veiculos",
]
BASE = {
    "id": 1,
    "data_hora": pd.Timestamp("2025-01-01 06:20:00"),
    "uf": "SP",
    "br": 116,
    "km": 546.2,
    "municipio": "GUARULHOS",
    "causa": "Pista esburacada",
    "tipo": "Tombamento",
    "classificacao": "Com Vítimas Feridas",
    "fase_dia": "Pleno dia",
    "condicao_meteo": "Céu Claro",
    "mortos": 0,
    "feridos": 1,
    "veiculos": 2,
}
TIPOS = {
    "id": "int64",
    "data_hora": "datetime64[us]",
    "uf": "str",
    "br": "Int16",
    "km": "float64",
    "municipio": "str",
    "causa": "str",
    "tipo": "str",
    "classificacao": "str",
    "fase_dia": "str",
    "condicao_meteo": "str",
    "mortos": "Int16",
    "feridos": "Int16",
    "veiculos": "Int16",
}
HORA = datetime(2025, 1, 1, 6, 20)
TEXTOS = ("Pista esburacada", "Tombamento")
FIM = ("Pleno dia", "Céu Claro")


def quadro(*trocas):
    """Uma linha por dicionário de trocas sobre BASE, com os tipos que o limpar grava."""
    return pd.DataFrame([{**BASE, **t} for t in trocas], columns=COLUNAS).astype(TIPOS)


@pytest.fixture
def esquema():
    """Schema descartável, criado e apagado com conexões próprias (autocommit)."""
    from acidentes.banco import url_do_banco

    nome = f"teste_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(url_do_banco(), autocommit=True) as c:
        c.execute(f"CREATE SCHEMA {nome}")
    yield nome
    with psycopg.connect(url_do_banco(), autocommit=True) as c:
        c.execute(f"DROP SCHEMA {nome} CASCADE")


def url_no_esquema(nome):
    from acidentes.banco import url_do_banco

    return make_conninfo(url_do_banco(), options=f"-c search_path={nome}")


@pytest.fixture
def conn(esquema):
    with psycopg.connect(url_no_esquema(esquema)) as c:
        yield c


def linhas(conn):
    return conn.execute(
        "SELECT id, data_hora, uf, br, km, municipio, causa, tipo, classificacao,"
        " fase_dia, condicao_meteo, mortos, feridos, veiculos FROM acidente ORDER BY id"
    ).fetchall()


def test_ar_6_cria_a_tabela_da_ficha_e_os_indices(conn):
    from acidentes.carregar import criar_tabela

    criar_tabela(conn)
    criar_tabela(conn)
    colunas = conn.execute(
        "SELECT attname, format_type(atttypid, atttypmod), attnotnull"
        " FROM pg_attribute WHERE attrelid = 'acidente'::regclass"
        " AND attnum > 0 AND NOT attisdropped ORDER BY attnum"
    ).fetchall()
    assert colunas == [
        ("id", "bigint", True),
        ("data_hora", "timestamp without time zone", True),
        ("uf", "character(2)", True),
        ("br", "smallint", False),
        ("km", "numeric(7,1)", False),
        ("municipio", "text", False),
        ("causa", "text", False),
        ("tipo", "text", False),
        ("classificacao", "text", False),
        ("fase_dia", "text", False),
        ("condicao_meteo", "text", False),
        ("mortos", "smallint", True),
        ("feridos", "smallint", True),
        ("veiculos", "smallint", False),
    ]
    indices = conn.execute(
        "SELECT replace(indexdef, current_schema() || '.', '') FROM pg_indexes"
        " WHERE schemaname = current_schema() AND tablename = 'acidente'"
        " ORDER BY indexname"
    ).fetchall()
    assert indices == [
        ("CREATE INDEX acidente_br_km ON acidente USING btree (br, km)",),
        ("CREATE UNIQUE INDEX acidente_pkey ON acidente USING btree (id)",),
        ("CREATE INDEX acidente_uf_data_hora ON acidente USING btree (uf, data_hora)",),
    ]


def test_ar_6_carrega_valores_e_nulos(conn):
    from acidentes.carregar import carregar, criar_tabela

    criar_tabela(conn)
    inseridas = carregar(
        conn,
        quadro(
            {"id": 1},
            {"id": 2, "br": None, "km": None, "classificacao": None},
            {"id": 3, "km": 225.0, "municipio": 'SAO "X", Y', "veiculos": None},
        ),
    )
    assert inseridas == 3
    assert linhas(conn) == [
        (1, HORA, "SP", 116, Decimal("546.2"), "GUARULHOS", *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, 2),
        (2, HORA, "SP", None, None, "GUARULHOS", *TEXTOS, None, *FIM, 0, 1, 2),
        (3, HORA, "SP", 116, Decimal("225.0"), 'SAO "X", Y', *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, None),
    ]


def test_ar_6_segunda_carga_nao_duplica_nem_sobrescreve(conn):
    from acidentes.carregar import carregar, criar_tabela

    criar_tabela(conn)
    assert carregar(conn, quadro({"id": 1}, {"id": 2}, {"id": 3})) == 3
    assert carregar(conn, quadro({"id": 1}, {"id": 2}, {"id": 3})) == 0
    outra = quadro(
        {"id": 2, "municipio": "OUTRO"},
        {"id": 3, "municipio": "OUTRO"},
        {"id": 4, "municipio": "OUTRO"},
    )
    assert carregar(conn, outra) == 1
    assert [(x[0], x[5]) for x in linhas(conn)] == [
        (1, "GUARULHOS"),
        (2, "GUARULHOS"),
        (3, "GUARULHOS"),
        (4, "OUTRO"),
    ]


def test_ar_6_carga_com_linha_invalida_nao_grava_nada(conn):
    from acidentes.carregar import carregar, criar_tabela

    criar_tabela(conn)
    assert carregar(conn, quadro({"id": 1})) == 1
    with pytest.raises(psycopg.errors.NotNullViolation):
        carregar(conn, quadro({"id": 2}, {"id": 3, "uf": None}))
    assert [x[0] for x in linhas(conn)] == [1]
    assert conn.execute("SELECT to_regclass('acidente_carga')").fetchone() == (None,)


def test_ar_6_main_carrega_o_parquet_duas_vezes_sem_duplicar(
    esquema, tmp_path, monkeypatch, capsys
):
    import acidentes.carregar as modulo

    origem = tmp_path / "clean" / "acidentes.parquet"
    origem.parent.mkdir()
    quadro({"id": 1}, {"id": 2, "br": None, "km": None}).to_parquet(origem, index=False)
    monkeypatch.setattr(modulo, "ORIGEM", origem)
    monkeypatch.setenv("DATABASE_URL", url_no_esquema(esquema))
    modulo.main()
    modulo.main()
    assert capsys.readouterr().out == (
        "acidente: 2 inseridas, 2 no banco\nacidente: 0 inseridas, 2 no banco\n"
    )
    with psycopg.connect(url_no_esquema(esquema)) as c:
        assert [(x[0], x[3], x[4]) for x in linhas(c)] == [
            (1, 116, Decimal("546.2")),
            (2, None, None),
        ]


def test_ar_6_origem_e_o_parquet_do_limpar():
    from acidentes.carregar import ORIGEM

    assert Path("data/clean/acidentes_2025.parquet") == ORIGEM
