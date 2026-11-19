"""Consultas de sql/ contra a fixture de 50 acidentes (AR-7).

Os esperados foram calculados à mão sobre tests/fixtures/acidentes_50.csv, antes das
consultas; cada teste compara o resultado inteiro (colunas e linhas, na ordem).
"""

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

FIXTURE = Path(__file__).parent / "fixtures" / "acidentes_50.csv"
T1 = "Colisão traseira"
T2 = "Saída de leito carroçável"
T3 = "Colisão transversal"
T4 = "Tombamento"
T5 = "Atropelamento de Pedestre"


@pytest.fixture(scope="module")
def conn():
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


def test_ar_7_pasta_sql_tem_as_seis_consultas_comentadas():
    from acidentes.consultas import PASTA

    arquivos = sorted(PASTA.glob("*.sql"))
    assert [a.name for a in arquivos] == [
        "01_acidentes_por_mes.sql",
        "02_top_brs.sql",
        "03_hora_gravidade.sql",
        "04_dia_semana_tipo.sql",
        "05_meteo_mortos.sql",
        "06_trechos.sql",
    ]
    for arquivo in arquivos:
        assert arquivo.read_text(encoding="utf-8").startswith("-- ")


def test_ar_7_executar_le_o_arquivo_da_pasta(tmp_path, monkeypatch, conn):
    import acidentes.consultas as modulo

    (tmp_path / "exemplo.sql").write_text(
        "SELECT 1 AS um, 'b' AS dois", encoding="utf-8"
    )
    monkeypatch.setattr(modulo, "PASTA", tmp_path)
    assert modulo.executar(conn, "exemplo") == (["um", "dois"], [(1, "b")])


def test_ar_7_consulta_1_acidentes_por_mes(conn):
    from acidentes.consultas import executar

    d = Decimal
    assert executar(conn, "01_acidentes_por_mes") == (
        ["mes", "acidentes", "variacao", "variacao_pct"],
        [
            (date(2025, 1, 1), 6, None, None),
            (date(2025, 2, 1), 4, -2, d("-33.3")),
            (date(2025, 3, 1), 0, -4, d("-100.0")),
            (date(2025, 4, 1), 5, 5, None),
            (date(2025, 5, 1), 5, 0, d("0.0")),
            (date(2025, 6, 1), 3, -2, d("-40.0")),
            (date(2025, 7, 1), 4, 1, d("33.3")),
            (date(2025, 8, 1), 6, 2, d("50.0")),
            (date(2025, 9, 1), 4, -2, d("-33.3")),
            (date(2025, 10, 1), 5, 1, d("25.0")),
            (date(2025, 11, 1), 3, -2, d("-40.0")),
            (date(2025, 12, 1), 5, 2, d("66.7")),
        ],
    )


def test_ar_7_consulta_2_top_brs(conn):
    from acidentes.consultas import executar

    assert executar(conn, "02_top_brs") == (
        ["br", "acidentes", "mortos", "rank_acidentes", "rank_mortos"],
        [
            (116, 8, 2, 1, 4),
            (101, 7, 4, 2, 1),
            (381, 6, 1, 3, 6),
            (40, 5, 3, 4, 2),
            (262, 4, 1, 5, 6),
            (153, 4, 0, 5, 11),
            (364, 3, 2, 7, 4),
            (50, 3, 1, 7, 6),
            (277, 3, 1, 7, 6),
            (60, 2, 1, 10, 6),
            (70, 1, 3, 11, 2),
        ],
    )


def test_ar_7_consulta_3_hora_gravidade(conn):
    from acidentes.consultas import executar

    com_acidente = {
        0: (3, 0, 3, 0),
        7: (10, 6, 4, 0),
        12: (11, 6, 5, 0),
        18: (9, 0, 8, 0),
        19: (15, 0, 5, 10),
        23: (2, 0, 0, 2),
    }
    assert executar(conn, "03_hora_gravidade") == (
        ["hora", "acidentes", "sem_vitimas", "com_feridos", "com_fatais"],
        [(h, *com_acidente.get(h, (0, 0, 0, 0))) for h in range(24)],
    )


def test_ar_7_consulta_4_dia_semana_tipo(conn):
    from acidentes.consultas import executar

    d = Decimal
    assert executar(conn, "04_dia_semana_tipo") == (
        ["isodow", "dia", "tipo", "acidentes", "pct_do_dia"],
        [
            (1, "segunda", T1, 4, d("44.4")),
            (1, "segunda", T3, 2, d("22.2")),
            (1, "segunda", T2, 2, d("22.2")),
            (2, "terça", T5, 3, d("50.0")),
            (2, "terça", T2, 3, d("50.0")),
            (3, "quarta", T3, 2, d("28.6")),
            (3, "quarta", T1, 2, d("28.6")),
            (3, "quarta", T4, 2, d("28.6")),
            (4, "quinta", T1, 5, d("100.0")),
            (5, "sexta", T1, 3, d("37.5")),
            (5, "sexta", T2, 3, d("37.5")),
            (5, "sexta", T3, 1, d("12.5")),
            (6, "sábado", T4, 4, d("50.0")),
            (6, "sábado", T5, 2, d("25.0")),
            (6, "sábado", T2, 2, d("25.0")),
            (7, "domingo", T5, 3, d("42.9")),
            (7, "domingo", T1, 2, d("28.6")),
            (7, "domingo", T3, 1, d("14.3")),
        ],
    )


def test_ar_7_consulta_5_meteo_mortos(conn):
    from acidentes.consultas import executar

    d = Decimal
    assert executar(conn, "05_meteo_mortos") == (
        ["condicao_meteo", "acidentes", "mortos", "mortos_por_acidente"],
        [
            ("Chuva", 10, 7, d("0.7000")),
            ("Nublado", 9, 4, d("0.4444")),
            ("Céu Claro", 25, 6, d("0.2400")),
            ("Neve", 1, 0, d("0.0000")),
        ],
    )


def test_ar_7_consulta_6_trechos(conn):
    from acidentes.consultas import executar

    assert executar(conn, "06_trechos") == (
        ["uf", "br", "km", "acidentes"],
        [
            ("SP", 116, 225, 4),
            ("MG", 381, 500, 3),
            ("SC", 101, 50, 3),
            ("GO", 153, 300, 2),
            ("MG", 40, 688, 2),
            ("MG", 116, 225, 2),
            ("MG", 262, 400, 2),
            ("MT", 364, 3, 2),
            ("PR", 277, 600, 2),
            ("RJ", 101, 50, 2),
        ],
    )
