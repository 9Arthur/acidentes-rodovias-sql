"""baixar(): arquivo da PRF com o sha256 fixado (AR-1); o download é testado num servidor HTTP local."""

import hashlib
import http.server
import threading
from pathlib import Path

import pytest

CONTEUDO = b"conteudo de teste no lugar do zip da PRF"
SHA_CONTEUDO = hashlib.sha256(CONTEUDO).hexdigest()
SHA_ERRADO = "0" * 64


@pytest.fixture
def servidor():
    """Servidor local que devolve CONTEUDO em qualquer caminho e anota cada pedido."""
    pedidos = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            pedidos.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", str(len(CONTEUDO)))
            self.end_headers()
            self.wfile.write(CONTEUDO)

        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/arquivo.zip", pedidos
    srv.shutdown()
    srv.server_close()


def test_sha256_arquivo_vetor_conhecido(tmp_path):
    from acidentes.baixar import sha256_arquivo

    arq = tmp_path / "abc.txt"
    arq.write_bytes(b"abc")
    assert (
        sha256_arquivo(arq)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_ar_1_usa_arquivo_existente_sem_baixar(tmp_path, servidor):
    from acidentes.baixar import baixar

    url, pedidos = servidor
    destino = tmp_path / "datatran.zip"
    destino.write_bytes(CONTEUDO)
    assert baixar(url, destino, SHA_CONTEUDO) == destino
    assert pedidos == []


def test_ar_1_baixa_quando_ausente(tmp_path, servidor):
    from acidentes.baixar import baixar

    url, pedidos = servidor
    destino = tmp_path / "raw" / "datatran.zip"
    assert baixar(url, destino, SHA_CONTEUDO) == destino
    assert destino.read_bytes() == CONTEUDO
    assert pedidos == ["/arquivo.zip"]
    assert list(destino.parent.iterdir()) == [destino]


def test_ar_1_hash_divergente_no_download_nao_deixa_arquivo(tmp_path, servidor):
    from acidentes.baixar import HashDivergente, baixar

    url, pedidos = servidor
    destino = tmp_path / "raw" / "datatran.zip"
    with pytest.raises(HashDivergente, match=SHA_CONTEUDO):
        baixar(url, destino, SHA_ERRADO)
    assert pedidos == ["/arquivo.zip"]
    assert list(destino.parent.iterdir()) == []


def test_ar_1_hash_divergente_em_arquivo_existente_mantem_o_arquivo(tmp_path, servidor):
    from acidentes.baixar import HashDivergente, baixar

    url, pedidos = servidor
    destino = tmp_path / "datatran.zip"
    destino.write_bytes(b"outro arquivo")
    with pytest.raises(
        HashDivergente, match=hashlib.sha256(b"outro arquivo").hexdigest()
    ):
        baixar(url, destino, SHA_CONTEUDO)
    assert destino.read_bytes() == b"outro arquivo"
    assert pedidos == []


def test_ar_1_main_usa_as_constantes_do_modulo(monkeypatch, tmp_path, servidor, capsys):
    import acidentes.baixar as modulo

    url, pedidos = servidor
    destino = tmp_path / "datatran.zip"
    monkeypatch.setattr(modulo, "URL", url)
    monkeypatch.setattr(modulo, "DESTINO", destino)
    monkeypatch.setattr(modulo, "SHA256", SHA_CONTEUDO)
    modulo.main()
    assert destino.read_bytes() == CONTEUDO
    assert pedidos == ["/arquivo.zip"]
    assert capsys.readouterr().out == f"{destino}: sha256 {SHA_CONTEUDO} conferido\n"


def test_ar_1_constantes_do_arquivo_da_prf():
    from acidentes.baixar import DESTINO, SHA256, URL

    assert SHA256 == "52c8a631ac9d428bf845e2fa996b8c61f66b219f7014a61d292f9d95d186bb0f"
    assert URL == (
        "https://drive.usercontent.google.com/download"
        "?id=1-G3MdmHBt6CprDwcW99xxC4BZ2DU5ryR&export=download"
    )
    assert Path("data/raw/datatran2025.zip") == DESTINO


def test_ar_1_download_grava_no_parcial(tmp_path, servidor, monkeypatch):
    import acidentes.baixar as modulo

    url, _ = servidor
    destino = tmp_path / "datatran.zip"
    alvos = []
    copia_original = modulo.shutil.copyfileobj

    def copia(origem, arquivo):
        alvos.append(Path(arquivo.name).name)
        copia_original(origem, arquivo)

    monkeypatch.setattr(modulo.shutil, "copyfileobj", copia)
    assert modulo.baixar(url, destino, SHA_CONTEUDO) == destino
    assert alvos == ["datatran.zip.parcial"]
