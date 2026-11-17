"""limpar: CSV da PRF (texto) para as 14 colunas do schema, com as regras da AR-5."""

import zipfile

import pandas as pd
import pytest

CABECALHO = [
    "id",
    "data_inversa",
    "dia_semana",
    "horario",
    "uf",
    "br",
    "km",
    "municipio",
    "causa_acidente",
    "tipo_acidente",
    "classificacao_acidente",
    "fase_dia",
    "sentido_via",
    "condicao_metereologica",
    "mortos",
    "feridos",
    "veiculos",
]
BASE = {
    "id": "652493",
    "data_inversa": "2025-01-01",
    "dia_semana": "quarta-feira",
    "horario": "06:20:00",
    "uf": "SP",
    "br": "116",
    "km": "225",
    "municipio": "GUARULHOS",
    "causa_acidente": "Pista esburacada",
    "tipo_acidente": "Tombamento",
    "classificacao_acidente": "Com Vítimas Feridas",
    "fase_dia": "Pleno dia",
    "sentido_via": "Crescente",
    "condicao_metereologica": "Céu Claro",
    "mortos": "0",
    "feridos": "1",
    "veiculos": "2",
}


def bruto(*trocas):
    """Uma linha por dicionario de trocas sobre BASE, tudo como texto, como sai do ler_csv."""
    return pd.DataFrame([{**BASE, **t} for t in trocas], columns=CABECALHO, dtype=str)


def test_numero_br():
    from acidentes.limpar import numero_br

    assert numero_br("546,2") == 546.2
    assert numero_br("225") == 225.0
    assert numero_br("") is None
    assert numero_br("NA") is None


def test_ar_5_colunas_do_schema_na_ordem():
    from acidentes.limpar import limpar

    limpo, _ = limpar(bruto({}))
    assert list(limpo.columns) == [
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


def test_ar_5_valores_de_uma_linha_completa():
    from acidentes.limpar import limpar

    limpo, descartadas = limpar(bruto({"km": "546,2"}))
    linha = limpo.iloc[0]
    assert descartadas == 0
    assert linha["id"] == 652493
    assert linha["data_hora"] == pd.Timestamp("2025-01-01 06:20:00")
    assert linha["uf"] == "SP"
    assert linha["br"] == 116
    assert linha["km"] == 546.2
    assert linha["causa"] == "Pista esburacada"
    assert linha["classificacao"] == "Com Vítimas Feridas"
    assert linha["condicao_meteo"] == "Céu Claro"
    assert (linha["mortos"], linha["feridos"], linha["veiculos"]) == (0, 1, 2)


def test_ar_5_sentinelas_viram_nulo():
    from acidentes.limpar import limpar

    limpo, _ = limpar(
        bruto(
            {
                "id": "1",
                "classificacao_acidente": "NA",
                "condicao_metereologica": "Ignorado",
            },
            {
                "id": "2",
                "municipio": "",
                "causa_acidente": "N/A",
                "tipo_acidente": "Não Informado",
            },
            {"id": "3"},
        )
    )
    assert limpo["classificacao"].isna().tolist() == [True, False, False]
    assert limpo["condicao_meteo"].isna().tolist() == [True, False, False]
    assert limpo["municipio"].isna().tolist() == [False, True, False]
    assert limpo["causa"].isna().tolist() == [False, True, False]
    assert limpo["tipo"].isna().tolist() == [False, True, False]


def test_ar_5_br_zero_vira_nulo_junto_com_o_km():
    from acidentes.limpar import limpar

    limpo, _ = limpar(
        bruto({"id": "1", "br": "0", "km": "0"}, {"id": "2", "br": "101", "km": "0"})
    )
    assert limpo["br"].isna().tolist() == [True, False]
    assert limpo["km"].isna().tolist() == [True, False]
    assert limpo["km"].iloc[1] == 0.0


def test_ar_5_linha_sem_id_e_descartada_e_contada():
    from acidentes.limpar import limpar

    limpo, descartadas = limpar(
        bruto({"id": "10"}, {"id": ""}, {"id": "NA"}, {"id": "11"})
    )
    assert descartadas == 2
    assert limpo["id"].tolist() == [10, 11]


def test_ar_5_ler_csv_nao_converte_na_sozinho(tmp_path):
    from acidentes.limpar import ler_csv

    texto = "id;classificacao_acidente;condicao_metereologica;km\r\n7;NA;Céu Claro;546,2\r\n8;;Ignorado;\r\n"
    caminho = tmp_path / "datatran.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("datatran.csv", texto.encode("latin-1"))
    lido = ler_csv(caminho)
    assert lido["classificacao_acidente"].tolist() == ["NA", ""]
    assert lido["condicao_metereologica"].tolist() == ["Céu Claro", "Ignorado"]
    assert lido["km"].tolist() == ["546,2", ""]
    assert lido["id"].tolist() == ["7", "8"]


def test_ar_5_main_grava_o_parquet(tmp_path, monkeypatch, capsys):
    import acidentes.limpar as modulo

    origem = tmp_path / "raw" / "datatran.zip"
    origem.parent.mkdir()
    csv = bruto({"id": "1"}, {"id": ""}, {"id": "2", "br": "0"}).to_csv(
        sep=";", index=False
    )
    with zipfile.ZipFile(origem, "w") as z:
        z.writestr("datatran.csv", csv.encode("latin-1"))
    destino = tmp_path / "clean" / "acidentes.parquet"
    monkeypatch.setattr(modulo, "ORIGEM", origem)
    monkeypatch.setattr(modulo, "DESTINO", destino)
    modulo.main()
    gravado = pd.read_parquet(destino)
    assert gravado["id"].tolist() == [1, 2]
    assert gravado["br"].isna().tolist() == [False, True]
    assert capsys.readouterr().out == f"{destino}: 2 linhas, 1 descartada(s) sem id\n"


@pytest.mark.parametrize("coluna", ["br", "veiculos"])
def test_ar_5_inteiros_aceitam_nulo(coluna):
    from acidentes.limpar import limpar

    limpo, _ = limpar(bruto({"id": "1", coluna: "NA"}, {"id": "2"}))
    assert limpo[coluna].isna().tolist() == [True, False]
