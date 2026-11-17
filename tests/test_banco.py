"""Conexão com o Postgres: o do compose (local) e o serviço da CI (AR-2)."""


def test_ar_2_url_padrao_e_a_do_compose(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from acidentes.banco import url_do_banco

    assert url_do_banco() == "postgresql://acidentes:acidentes@localhost:5434/acidentes"


def test_ar_2_url_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:s@h:1/b")
    from acidentes.banco import url_do_banco

    assert url_do_banco() == "postgresql://u:s@h:1/b"


def test_banco_responde_select_1():
    from acidentes.banco import conectar

    with conectar() as conn:
        assert conn.execute("SELECT 1").fetchone() == (1,)
