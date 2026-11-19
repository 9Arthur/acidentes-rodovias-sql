"""Gera o RELATORIO.md e os 3 gráficos a partir das 10 consultas de sql/ (AR-8)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from matplotlib.figure import Figure

from acidentes import banco, consultas

DESTINO = Path("RELATORIO.md")
IMAGENS = Path("docs/img")
TITULOS = {
    "01_acidentes_por_mes": "Acidentes por mês e tendência",
    "02_top_brs": "Top 10 BRs por acidentes e por mortos",
    "03_hora_gravidade": "Hora do dia × gravidade",
    "04_dia_semana_tipo": "Dia da semana × tipo de acidente",
    "05_meteo_mortos": "Condição meteorológica × mortos por acidente",
    "06_trechos": "Trechos com mais acidentes",
    "07_comparacao_ufs": "Comparação entre dois estados (MG × SC)",
    "08_media_movel": "Média móvel de 7 dias",
    "09_causas_por_uf": "Ranking de causas por UF",
    "10_fase_dia": "Letalidade por fase do dia",
}
GRAFICOS = {
    "01_acidentes_por_mes": "acidentes_por_mes.png",
    "03_hora_gravidade": "hora_fatais.png",
    "08_media_movel": "media_movel_7d.png",
}
# Tabela com mais linhas que isto vai recolhida num <details>, para o relatório não virar
# uma lista de 365 dias.
RECOLHER = 30
AZUL = "#4c72b0"
AZUL_CLARO = "#c5d1e0"
VERMELHO = "#c44e52"


def celula(valor) -> str:
    # Cobre os tipos que as 10 consultas devolvem: date (nenhuma devolve datetime),
    # Decimal, int e texto sem quebra de linha.
    if valor is None:
        return ""
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return format(valor, "f")
    return str(valor).replace("|", "\\|")


def tabela(colunas: list[str], linhas: list[tuple]) -> str:
    saida = ["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
    saida += ["| " + " | ".join(celula(v) for v in linha) + " |" for linha in linhas]
    texto = "\n".join(saida) + "\n"
    if len(linhas) > RECOLHER:
        return f"<details>\n<summary>{len(linhas)} linhas</summary>\n\n{texto}\n</details>\n"
    return texto


def figura(nome: str, colunas: list[str], linhas: list[tuple]) -> Figure:
    """Monta o gráfico de uma consulta; quem chama decide onde gravar."""
    dados = {c: [linha[i] for linha in linhas] for i, c in enumerate(colunas)}
    # Figure direto, sem pyplot: não depende de backend com tela nem de estado global.
    fig = Figure(figsize=(10, 4.5))
    ax = fig.subplots()
    if nome == "01_acidentes_por_mes":
        rotulos = [m.strftime("%m/%Y") for m in dados["mes"]]
        ax.bar(rotulos, dados["acidentes"], color=AZUL)
        ax.set_ylabel("acidentes")
        ax.set_title("Acidentes por mês")
        ax.tick_params(axis="x", labelrotation=45)
    elif nome == "03_hora_gravidade":
        # A gravidade por hora é a proporção de acidentes com vítima fatal; a contagem
        # absoluta de fatais só repetiria o volume. Hora sem acidente fica sem ponto.
        pct = [
            None if a == 0 else 100 * f / a
            for a, f in zip(dados["acidentes"], dados["com_fatais"], strict=True)
        ]
        ax.bar(dados["hora"], dados["acidentes"], color=AZUL_CLARO)
        ax.set_ylabel("acidentes", color=AZUL)
        ax.set_ylim(bottom=0)
        fatais = ax.twinx()
        fatais.plot(dados["hora"], pct, color=VERMELHO, marker="o")
        fatais.set_ylabel("% com vítimas fatais", color=VERMELHO)
        fatais.set_ylim(bottom=0)
        ax.set_xticks(range(24))
        ax.set_xlabel("hora do dia")
        ax.set_title("Acidentes por hora e % deles com vítimas fatais")
    elif nome == "08_media_movel":
        media = [None if v is None else float(v) for v in dados["media_7d"]]
        ax.plot(dados["dia"], dados["acidentes"], color=AZUL_CLARO, label="por dia")
        ax.plot(dados["dia"], media, color=AZUL, label="média de 7 dias")
        ax.set_ylabel("acidentes por dia")
        ax.set_ylim(bottom=0)
        ax.legend(loc="lower right")
        ax.set_title("Acidentes por dia e média móvel de 7 dias")
    else:
        raise ValueError(f"sem regra de gráfico para a consulta {nome}")
    fig.tight_layout()
    return fig


def gerar(conn, destino: Path, imagens: Path) -> list[Path]:
    """Roda as 10 consultas, escreve o relatório e os gráficos; devolve os arquivos."""
    imagens.mkdir(parents=True, exist_ok=True)
    gerados = []
    partes = [
        "# Relatório — acidentes nas rodovias federais (PRF, 2025)\n",
        "Gerado na raiz do repositório por `uv run python -m acidentes.relatorio`.\n",
    ]
    for numero, (nome, titulo) in enumerate(TITULOS.items(), start=1):
        colunas, linhas = consultas.executar(conn, nome)
        partes.append(f"## {numero}. {titulo}\n")
        partes.append(f"Consulta: `sql/{nome}.sql`\n")
        if nome in GRAFICOS:
            caminho = imagens / GRAFICOS[nome]
            # Sem a versão do matplotlib nos metadados: o PNG não muda só por ela.
            figura(nome, colunas, linhas).savefig(
                caminho, dpi=100, metadata={"Software": None}
            )
            gerados.append(caminho)
            link = caminho.relative_to(destino.parent).as_posix()
            partes.append(f"![{titulo}]({link})\n")
        partes.append(tabela(colunas, linhas))
    destino.write_text("\n".join(partes), encoding="utf-8")
    return [destino, *gerados]


def main() -> None:
    with banco.conectar() as conn:
        gerados = gerar(conn, DESTINO, IMAGENS)
    for caminho in gerados:
        print(caminho)


if __name__ == "__main__":
    main()
