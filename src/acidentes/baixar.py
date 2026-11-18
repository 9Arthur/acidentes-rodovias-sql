"""Baixa o CSV de acidentes de 2025 da PRF e confere o sha256 fixado (AR-1)."""

import hashlib
import shutil
import urllib.request
from pathlib import Path

URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1-G3MdmHBt6CprDwcW99xxC4BZ2DU5ryR&export=download"
)
SHA256 = "52c8a631ac9d428bf845e2fa996b8c61f66b219f7014a61d292f9d95d186bb0f"
DESTINO = Path("data/raw/datatran2025.zip")


class HashDivergente(Exception):
    """O arquivo não é o que a análise usou: o sha256 difere do fixado."""


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(url: str, destino: Path, sha_esperado: str) -> Path:
    """Usa o arquivo em destino se existir; se não, baixa. Nos dois casos confere o sha256."""
    if destino.exists():
        visto = sha256_arquivo(destino)
        if visto == sha_esperado:
            return destino
        raise HashDivergente(f"{destino}: sha256 {visto}, esperado {sha_esperado}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    try:
        with (
            urllib.request.urlopen(url, timeout=120) as resposta,
            parcial.open("wb") as f,
        ):
            shutil.copyfileobj(resposta, f)
        visto = sha256_arquivo(parcial)
    except BaseException:
        parcial.unlink(missing_ok=True)
        raise
    if visto == sha_esperado:
        parcial.replace(destino)
        return destino
    parcial.unlink()
    raise HashDivergente(f"{url}: sha256 {visto}, esperado {sha_esperado}")


def main() -> None:
    caminho = baixar(URL, DESTINO, SHA256)
    print(f"{caminho}: sha256 {SHA256} conferido")


if __name__ == "__main__":
    main()
