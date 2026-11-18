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
        "SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,"
        " pg_get_expr(d.adbin, d.adrelid) FROM pg_attribute a"
        " LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum"
        " WHERE a.attrelid = 'acidente'::regclass"
        " AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"
    ).fetchall()
    assert colunas == [
        ("id", "bigint", True, None),
        ("data_hora", "timestamp without time zone", True, None),
        ("uf", "character(2)", True, None),
        ("br", "smallint", False, None),
        ("km", "numeric(7,1)", False, None),
        ("municipio", "text", False, None),
        ("causa", "text", False, None),
        ("tipo", "text", False, None),
        ("classificacao", "text", False, None),
        ("fase_dia", "text", False, None),
        ("condicao_meteo", "text", False, None),
        ("mortos", "smallint", True, "0"),
        ("feridos", "smallint", True, "0"),
        ("veiculos", "smallint", False, None),
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
            {"id": 4, "municipio": "A\nB"},
            {"id": 5, "municipio": "A\rB"},
        ),
    )
    assert inseridas == 5
    assert linhas(conn) == [
        (1, HORA, "SP", 116, Decimal("546.2"), "GUARULHOS", *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, 2),
        (2, HORA, "SP", None, None, "GUARULHOS", *TEXTOS, None, *FIM, 0, 1, 2),
        (3, HORA, "SP", 116, Decimal("225.0"), 'SAO "X", Y', *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, None),
        (4, HORA, "SP", 116, Decimal("546.2"), "A\nB", *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, 2),
        (5, HORA, "SP", 116, Decimal("546.2"), "A\rB", *TEXTOS)
        + ("Com Vítimas Feridas", *FIM, 0, 1, 2),
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


def test_ar_6_id_repetido_no_parquet_derruba_a_carga(conn):
    from acidentes.carregar import carregar, criar_tabela

    criar_tabela(conn)
    with pytest.raises(psycopg.errors.UniqueViolation):
        carregar(conn, quadro({"id": 1}, {"id": 1, "municipio": "OUTRO"}))
    assert linhas(conn) == []
    assert conn.execute("SELECT to_regclass('acidente_carga')").fetchone() == (None,)


def test_ar_6_conexao_de_teste_fica_no_schema_descartavel(esquema, conn):
    from acidentes.banco import url_do_banco

    assert conn.execute("SELECT current_schema()").fetchone() == (esquema,)
    with psycopg.connect(url_do_banco()) as sem_options:
        assert sem_options.execute("SELECT current_schema()").fetchone() == ("public",)


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
