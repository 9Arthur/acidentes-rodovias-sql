"""Cria a tabela acidente e carrega o Parquet do limpar por COPY, sem duplicar (AR-6)."""

import pandas as pd
import psycopg

from acidentes import banco, limpar

ORIGEM = limpar.DESTINO
SCHEMA = """
CREATE TABLE IF NOT EXISTS acidente (
    id             BIGINT PRIMARY KEY,
    data_hora      TIMESTAMP NOT NULL,
    uf             CHAR(2) NOT NULL,
    br             SMALLINT,
    km             NUMERIC(7,1),
    municipio      TEXT,
    causa          TEXT,
    tipo           TEXT,
    classificacao  TEXT,
    fase_dia       TEXT,
    condicao_meteo TEXT,
    mortos         SMALLINT NOT NULL DEFAULT 0,
    feridos        SMALLINT NOT NULL DEFAULT 0,
    veiculos       SMALLINT
);
CREATE INDEX IF NOT EXISTS acidente_uf_data_hora ON acidente (uf, data_hora);
CREATE INDEX IF NOT EXISTS acidente_br_km ON acidente (br, km);
"""
LISTA = ", ".join(limpar.COLUNAS)


def criar_tabela(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA)


def carregar(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    """COPY para uma tabela temporária e INSERT ... ON CONFLICT DO NOTHING, numa transação.

    Devolve quantas linhas entraram; as de id já existente ficam como estavam.
    """
    with conn.transaction():
        conn.execute("CREATE TEMP TABLE acidente_carga (LIKE acidente)")
        with conn.cursor().copy(
            f"COPY acidente_carga ({LISTA}) FROM STDIN (FORMAT csv)"
        ) as cp:
            cp.write(df[limpar.COLUNAS].to_csv(index=False, header=False))
        inseridas = conn.execute(
            f"INSERT INTO acidente ({LISTA}) SELECT {LISTA} FROM acidente_carga"
            " ON CONFLICT (id) DO NOTHING"
        ).rowcount
        conn.execute("DROP TABLE acidente_carga")
    return inseridas


def main() -> None:
    df = pd.read_parquet(ORIGEM)
    with banco.conectar() as conn:
        criar_tabela(conn)
        inseridas = carregar(conn, df)
        (total,) = conn.execute("SELECT count(*) FROM acidente").fetchone()
    print(f"acidente: {inseridas} inseridas, {total} no banco")


if __name__ == "__main__":
    main()
