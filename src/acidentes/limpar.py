"""Limpa o CSV de acidentes da PRF e grava as colunas do schema em Parquet (AR-5)."""

import io
import zipfile
from pathlib import Path

import pandas as pd

from acidentes import baixar

ORIGEM = baixar.DESTINO
DESTINO = Path("data/clean/acidentes_2025.parquet")
SENTINELAS = frozenset({"", "NA", "N/A", "Ignorado", "Não Informado"})
TEXTO = {
    "uf": "uf",
    "municipio": "municipio",
    "causa_acidente": "causa",
    "tipo_acidente": "tipo",
    "classificacao_acidente": "classificacao",
    "fase_dia": "fase_dia",
    "condicao_metereologica": "condicao_meteo",
}
INTEIROS = ["br", "mortos", "feridos", "veiculos"]
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


def decimal_virgula(texto: str) -> float | None:
    """Número com vírgula decimal ("546,2") para float; sentinela vira None."""
    t = texto.strip()
    if t in SENTINELAS:
        return None
    return float(t.replace(",", "."))


def ler_csv(caminho_zip: Path) -> pd.DataFrame:
    """Lê o único CSV do zip (latin-1, ';') com todas as colunas como texto, sem nulo automático."""
    with zipfile.ZipFile(caminho_zip) as z:
        (nome,) = [n for n in z.namelist() if n.lower().endswith(".csv")]
        dados = z.read(nome)
    return pd.read_csv(
        io.BytesIO(dados), sep=";", encoding="latin-1", dtype=str, keep_default_na=False
    )


def _texto(coluna: pd.Series) -> pd.Series:
    limpa = coluna.str.strip()
    return limpa.mask(limpa.isin(SENTINELAS))


def limpar(bruto: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Aplica a AR-5; devolve as colunas do schema e quantas linhas sem id foram descartadas."""
    sem_id = bruto["id"].str.strip().isin(SENTINELAS)
    df = bruto[~sem_id]
    limpo = pd.DataFrame(index=df.index)
    limpo["id"] = df["id"].str.strip().astype("int64")
    limpo["data_hora"] = pd.to_datetime(
        df["data_inversa"].str.strip() + " " + df["horario"].str.strip(),
        format="%Y-%m-%d %H:%M:%S",
    )
    for coluna in INTEIROS:
        limpo[coluna] = pd.to_numeric(_texto(df[coluna])).astype("Int16")
    limpo["km"] = df["km"].map(decimal_virgula).astype("float64")
    br_zero = limpo["br"] == 0
    limpo.loc[br_zero, ["br", "km"]] = pd.NA
    for origem, destino in TEXTO.items():
        limpo[destino] = _texto(df[origem])
    return limpo[COLUNAS].reset_index(drop=True), int(sem_id.sum())


def main() -> None:
    origem = baixar.baixar(baixar.URL, ORIGEM, baixar.SHA256)
    limpo, descartadas = limpar(ler_csv(origem))
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    limpo.to_parquet(DESTINO, index=False)
    print(f"{DESTINO}: {len(limpo)} linhas, {descartadas} descartada(s) sem id")


if __name__ == "__main__":
    main()
