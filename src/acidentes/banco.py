"""Conexão com o PostgreSQL (AR-2)."""

import os

import psycopg

URL_LOCAL = "postgresql://acidentes:acidentes@localhost:5434/acidentes"


def url_do_banco() -> str:
    """A URL do ambiente (CI) ou, sem ela, a do Postgres do docker-compose."""
    return os.environ.get("DATABASE_URL", URL_LOCAL)


def conectar() -> psycopg.Connection:
    return psycopg.connect(url_do_banco())
