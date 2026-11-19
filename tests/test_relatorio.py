"""relatorio: RELATORIO.md e os 3 gráficos gerados a partir das consultas de sql/ (AR-8)."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

PNG = b"\x89PNG\r\n\x1a\n"


def test_ar_8_gera_o_relatorio_e_os_tres_graficos(conn_50, tmp_path):
    from acidentes.relatorio import gerar

    destino = tmp_path / "RELATORIO.md"
    imagens = tmp_path / "docs" / "img"
    gerados = gerar(conn_50, destino, imagens)
    assert gerados == [
        destino,
        imagens / "acidentes_por_mes.png",
        imagens / "hora_fatais.png",
        imagens / "media_movel_7d.png",
    ]
    assert sorted(p.name for p in imagens.iterdir()) == [
        "acidentes_por_mes.png",
        "hora_fatais.png",
        "media_movel_7d.png",
    ]
    for png in gerados[1:]:
        assert png.read_bytes().startswith(PNG)
    texto = destino.read_text(encoding="utf-8")
    assert texto.splitlines()[2] == (
        "Gerado na raiz do repositório por `uv run python -m acidentes.relatorio`."
    )
    titulos = [x for x in texto.splitlines() if x.startswith("## ")]
    assert titulos == [
        "## 1. Acidentes por mês e tendência",
        "## 2. Top 10 BRs por acidentes e por mortos",
        "## 3. Hora do dia × gravidade",
        "## 4. Dia da semana × tipo de acidente",
        "## 5. Condição meteorológica × mortos por acidente",
        "## 6. Trechos com mais acidentes",
        "## 7. Comparação entre dois estados (MG × SC)",
        "## 8. Média móvel de 7 dias",
        "## 9. Ranking de causas por UF",
        "## 10. Letalidade por fase do dia",
    ]
    assert "![Acidentes por mês e tendência](docs/img/acidentes_por_mes.png)" in texto
    assert "![Hora do dia × gravidade](docs/img/hora_fatais.png)" in texto
    assert "![Média móvel de 7 dias](docs/img/media_movel_7d.png)" in texto
    assert (
        "| uf | acidentes | mortos | mortos_por_acidente | pct_com_fatais |\n"
        "|---|---|---|---|---|\n"
        "| MG | 15 | 5 | 0.3333 | 20.0 |\n"
        "| SC | 6 | 4 | 0.6667 | 33.3 |\n"
    ) in texto
    assert "<summary>343 linhas</summary>" in texto
    assert "| 2025-01-06 | 6 |  |" in texto
    assert texto.count("<details>") == 1


def test_ar_8_tabela_formata_e_recolhe_as_longas():
    from acidentes.relatorio import tabela

    assert tabela(
        ["a", "b", "c", "d"], [(date(2025, 1, 2), Decimal("0.50"), None, "x|y")]
    ) == ("| a | b | c | d |\n|---|---|---|---|\n| 2025-01-02 | 0.50 |  | x\\|y |\n")
    curta = tabela(["n"], [(i,) for i in range(30)])
    longa = tabela(["n"], [(i,) for i in range(31)])
    assert "<details>" not in curta
    assert longa.startswith("<details>\n<summary>31 linhas</summary>\n\n| n |\n")
    assert longa.endswith("| 30 |\n\n</details>\n")


def test_ar_8_main_usa_os_destinos_do_modulo(conn_50, tmp_path, monkeypatch, capsys):
    from acidentes import relatorio as modulo
    from acidentes.banco import url_do_banco

    (esquema,) = conn_50.execute("SELECT current_schema()").fetchone()
    conninfo = make_conninfo(url_do_banco(), options=f"-c search_path={esquema}")
    monkeypatch.setattr(modulo.banco, "conectar", lambda: psycopg.connect(conninfo))
    monkeypatch.setattr(modulo, "DESTINO", tmp_path / "RELATORIO.md")
    monkeypatch.setattr(modulo, "IMAGENS", tmp_path / "img")
    modulo.main()
    assert capsys.readouterr().out.splitlines() == [
        str(tmp_path / "RELATORIO.md"),
        str(tmp_path / "img" / "acidentes_por_mes.png"),
        str(tmp_path / "img" / "hora_fatais.png"),
        str(tmp_path / "img" / "media_movel_7d.png"),
    ]


def test_ar_8_destinos_do_relatorio():
    from pathlib import Path

    from acidentes.relatorio import DESTINO, IMAGENS

    assert Path("RELATORIO.md") == DESTINO
    assert Path("docs/img") == IMAGENS


def test_ar_8_grafico_por_mes():
    from acidentes.relatorio import figura

    colunas = ["mes", "acidentes", "variacao", "variacao_pct"]
    linhas = [(date(2025, 1, 1), 6, None, None), (date(2025, 2, 1), 4, -2, None)]
    (ax,) = figura("01_acidentes_por_mes", colunas, linhas).axes
    assert [p.get_height() for p in ax.patches] == [6, 4]
    assert ax.get_ylabel() == "acidentes"
    assert ax.get_ylim()[0] == 0


def test_ar_8_grafico_da_hora_mostra_a_proporcao_de_fatais():
    from acidentes.relatorio import figura

    colunas = ["hora", "acidentes", "sem_vitimas", "com_feridos", "com_fatais"]
    linhas = [(0, 4, 0, 3, 1), (1, 0, 0, 0, 0), (2, 5, 1, 2, 2)]
    barras, fatais = figura("03_hora_gravidade", colunas, linhas).axes
    assert [p.get_height() for p in barras.patches] == [4, 0, 5]
    assert list(fatais.lines[0].get_ydata()) == [25.0, None, 40.0]
    assert (barras.get_ylabel(), fatais.get_ylabel()) == (
        "acidentes",
        "% com vítimas fatais",
    )
    assert (barras.get_ylim()[0], fatais.get_ylim()[0]) == (0, 0)


def test_ar_8_grafico_da_media_movel_mostra_os_dias_e_a_media():
    from acidentes.relatorio import figura

    dias = [date(2025, 1, n) for n in range(1, 9)]
    contagens = [7, 0, 0, 0, 0, 0, 7, 14]
    medias = [None] * 6 + [Decimal("2.00"), Decimal("3.00")]
    linhas = list(zip(dias, contagens, medias, strict=True))
    (ax,) = figura("08_media_movel", ["dia", "acidentes", "media_7d"], linhas).axes
    por_dia, media = ax.lines
    assert list(por_dia.get_ydata()) == contagens
    assert list(media.get_ydata()) == [None] * 6 + [2.0, 3.0]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == [
        "por dia",
        "média de 7 dias",
    ]
    assert ax.get_ylim()[0] == 0


def test_ar_8_consulta_sem_regra_de_grafico_da_erro_com_o_nome():
    from acidentes.relatorio import figura

    with pytest.raises(ValueError, match="02_top_brs"):
        figura("02_top_brs", ["br"], [(116,)])
