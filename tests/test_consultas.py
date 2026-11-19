"""Consultas de sql/ contra a fixture de 50 acidentes (AR-7).

Os esperados foram calculados à mão sobre tests/fixtures/acidentes_50.csv, antes das
consultas; cada teste compara o resultado inteiro (colunas e linhas, na ordem).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

T1 = "Colisão traseira"
T2 = "Saída de leito carroçável"
T3 = "Colisão transversal"
T4 = "Tombamento"
T5 = "Atropelamento de Pedestre"


@pytest.fixture
def conn(conn_50):
    return conn_50


def test_ar_7_pasta_sql_tem_as_dez_consultas_comentadas():
    from acidentes.consultas import PASTA

    arquivos = sorted(PASTA.glob("*.sql"))
    assert [a.name for a in arquivos] == [
        "01_acidentes_por_mes.sql",
        "02_top_brs.sql",
        "03_hora_gravidade.sql",
        "04_dia_semana_tipo.sql",
        "05_meteo_mortos.sql",
        "06_trechos.sql",
        "07_comparacao_ufs.sql",
        "08_media_movel.sql",
        "09_causas_por_uf.sql",
        "10_fase_dia.sql",
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


def test_ar_7_consulta_7_comparacao_ufs(conn):
    from acidentes.consultas import executar

    d = Decimal
    assert executar(conn, "07_comparacao_ufs") == (
        ["uf", "acidentes", "mortos", "mortos_por_acidente", "pct_com_fatais"],
        [
            ("MG", 15, 5, d("0.3333"), d("20.0")),
            ("SC", 5, 4, d("0.8000"), d("40.0")),
        ],
    )


def test_ar_7_consulta_8_media_movel(conn):
    from acidentes.consultas import executar

    d = Decimal
    colunas, linhas = executar(conn, "08_media_movel")
    assert colunas == ["dia", "acidentes", "media_7d"]
    inicio = date(2025, 1, 6)
    assert [x[0] for x in linhas] == [inicio + timedelta(n) for n in range(343)]
    com_acidente = {
        date(2025, 1, 6): 6,
        date(2025, 2, 3): 3,
        date(2025, 2, 4): 1,
        date(2025, 4, 8): 5,
        date(2025, 5, 7): 5,
        date(2025, 6, 4): 2,
        date(2025, 6, 5): 1,
        date(2025, 7, 10): 4,
        date(2025, 8, 8): 6,
        date(2025, 9, 12): 2,
        date(2025, 9, 13): 2,
        date(2025, 10, 11): 5,
        date(2025, 11, 8): 1,
        date(2025, 11, 9): 2,
        date(2025, 12, 14): 5,
    }
    assert [x[1] for x in linhas] == [com_acidente.get(x[0], 0) for x in linhas]
    assert [x[2] for x in linhas[:6]] == [None] * 6
    assert None not in [x[2] for x in linhas[6:]]
    por_dia = {x[0]: x for x in linhas}
    assert [por_dia[date(2025, m, dia)] for m, dia in [(1, 12), (1, 13)]] == [
        (date(2025, 1, 12), 0, d("0.86")),
        (date(2025, 1, 13), 0, d("0.00")),
    ]
    assert [
        por_dia[date(2025, m, dia)] for m, dia in [(2, 4), (2, 9), (2, 10), (2, 11)]
    ] == [
        (date(2025, 2, 4), 1, d("0.57")),
        (date(2025, 2, 9), 0, d("0.57")),
        (date(2025, 2, 10), 0, d("0.14")),
        (date(2025, 2, 11), 0, d("0.00")),
    ]
    assert [por_dia[date(2025, m, dia)] for m, dia in [(6, 10), (6, 11), (12, 14)]] == [
        (date(2025, 6, 10), 0, d("0.43")),
        (date(2025, 6, 11), 0, d("0.14")),
        (date(2025, 12, 14), 5, d("0.71")),
    ]
    assert sum(1 for x in linhas[6:] if x[2] > 0) == 69
    assert max(x[2] for x in linhas[6:]) == d("0.86")


def test_ar_7_consulta_9_causas_por_uf(conn):
    from acidentes.consultas import executar

    rea = "Reação tardia ou ineficiente do condutor"
    assert executar(conn, "09_causas_por_uf") == (
        ["uf", "posicao", "causa", "acidentes"],
        [
            ("AC", 1, rea, 2),
            ("DF", 1, rea, 2),
            ("ES", 1, rea, 1),
            ("GO", 1, rea, 6),
            ("MG", 1, "Ausência de reação do condutor", 4),
            ("MG", 2, "Condutor Dormindo", 3),
            ("MG", 2, "Condutor deixou de manter distância do veículo da frente", 3),
            ("MT", 1, rea, 4),
            ("PB", 1, rea, 1),
            ("PR", 1, rea, 4),
            ("RJ", 1, rea, 2),
            ("RO", 1, rea, 1),
            ("SC", 1, rea, 3),
            ("SC", 2, "Animais na Pista", 2),
            ("SP", 1, "Velocidade Incompatível", 2),
            ("SP", 2, "Acessar a via sem observar a presença dos outros veículos", 1),
            ("SP", 2, "Ingestão de álcool pelo condutor", 1),
            ("SP", 2, "Manobra de mudança de faixa", 1),
            ("SP", 2, rea, 1),
            ("TO", 1, rea, 1),
        ],
    )


def test_ar_7_consulta_10_fase_dia(conn):
    from acidentes.consultas import executar

    d = Decimal
    assert executar(conn, "10_fase_dia") == (
        ["fase_dia", "acidentes", "mortos", "mortos_por_100", "pct_com_fatais"],
        [
            ("Plena Noite", 16, 15, d("93.8"), d("62.5")),
            ("Anoitecer", 13, 5, d("38.5"), d("15.4")),
            ("Amanhecer", 10, 0, d("0.0"), d("0.0")),
            ("Pleno dia", 11, 0, d("0.0"), d("0.0")),
        ],
    )
