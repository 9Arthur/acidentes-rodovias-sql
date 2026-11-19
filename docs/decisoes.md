# Decisões técnicas

Cada decisão tem um código (`AR-n`), o que foi decidido e por quê. Os testes que a provam levam o código no nome (`test_ar_1_...`).

## AR-1 — Arquivo da PRF com sha256 fixado

`acidentes.baixar` usa `data/raw/datatran2025.zip` se ele existir; se não, baixa do endereço de download do Google Drive onde a PRF publica o arquivo. Nos dois casos confere o sha256 fixado no código e para se ele divergir. O download vai para um arquivo `.parcial`, que só é renomeado depois de conferido. Se o download for interrompido ou o hash divergir, o `.parcial` é apagado.

Por quê: a PRF atualiza o arquivo do ano todo mês. Sem o hash, os números da análise mudariam sem aviso; com ele, usar um arquivo novo exige trocar o hash de propósito. O hash fixado é o do arquivo baixado em 17/11/2026 (72.529 acidentes).

## AR-2 — Conexão pela `DATABASE_URL`

A conexão usa a variável `DATABASE_URL`; sem ela, ou com ela vazia, a URL do Postgres do `docker-compose.yml` (`localhost:5434`). Não há `.env`: a senha é a do container local, que não é segredo, e a CI passa a URL do seu Postgres pelo ambiente.

## AR-3 — Dados fora do Git

`data/raw/` e `data/clean/` estão no `.gitignore`. O arquivo de origem se obtém de novo pelo `acidentes.baixar` e é conferido pelo hash; os testes usam dados sintéticos.

## AR-4 — Dependências com pelo menos 14 dias de publicação

O `exclude-newer` do `pyproject.toml` faz o `uv` ignorar versões publicadas depois da data de corte, que é 14 dias antes do dia em que a dependência foi escolhida. Versão recém-publicada é onde aparecem release quebrada e pacote comprometido; e o `uv.lock` resolve igual em qualquer máquina.

## AR-5 — Limpeza explícita, sem nulo automático

`acidentes.limpar` lê o CSV com todas as colunas como texto e sem a conversão automática de nulos do pandas, que transformaria `NA` e vazio em nulo sem contar. As regras são explícitas e cada uma tem teste:

- Os espaços no começo e no fim de cada valor saem antes das outras regras.
- `""`, `NA`, `N/A`, `Ignorado` e `Não Informado` viram nulo. No arquivo de 2025 aparecem `Ignorado` em 1.000 linhas da condição meteorológica e `NA` em 1 classificação.
- `data_inversa` e `horario` viram `data_hora`, com formato fixo: uma data fora do formato interrompe a execução em vez de virar nulo.
- `km` com vírgula decimal vira número.
- BR 0 (167 linhas, todas com km 0) vira BR e km nulos: a linha continua nas contagens, mas não entra nas análises por rodovia e trecho.
- Linha sem `id` é descartada e contada.
- Saem só as 14 colunas do schema, em `data/clean/acidentes_2025.parquet`.

Por quê: no arquivo, `Ignorado` e `NA` significam "sem informação". Tratados como categoria, distorceriam as taxas por condição meteorológica.

Antes de ler, o `limpar` passa pelo `acidentes.baixar`: só o arquivo com o sha256 da AR-1 chega à limpeza. Por isso ele não valida o encoding, variações das sentinelas nem o formato dos números; esses pontos foram conferidos no arquivo fixado (latin-1, as sentinelas acima, `km` só com vírgula decimal), e trocar o arquivo exige conferi-los de novo.

## AR-6 — Carga idempotente por COPY

`acidentes.carregar` cria a tabela `acidente` (o schema da ficha, com `IF NOT EXISTS`) e carrega o Parquet do `limpar`: `COPY` do CSV gerado pelo pandas para uma tabela temporária com as colunas, os tipos, o `NOT NULL` e os índices da `acidente`, inclusive a chave primária (`LIKE ... INCLUDING INDEXES`), depois `INSERT ... ON CONFLICT (id) DO NOTHING` dela para a `acidente`, tudo num bloco de transação (o `COMMIT` é de quem abriu a conexão). Rodar a carga duas vezes mantém as 72.529 linhas. Uma linha inválida (por exemplo, `uf` nula) ou um `id` repetido no próprio Parquet desfaz a carga inteira; `mortos` ou `feridos` nulos também, porque o `DEFAULT 0` só vale quando a coluna fica fora do `INSERT`, e o `COPY` envia as 14.

Por quê: o `COPY` é o jeito rápido de carregar no Postgres, mas não aceita `ON CONFLICT`; direto na tabela final, a segunda carga pararia na chave primária. O `id` é o da PRF (chave natural), então uma linha já carregada fica como está.

Os testes rodam cada um num schema descartável (o `search_path` vai nas `options` da conexão), para nunca tocar na tabela `acidente` do banco local.

## AR-7 — Consultas em `sql/`, executadas por `acidentes.consultas`

Cada pergunta da análise é um arquivo comentado em `sql/`, com o número na frente do nome (`01_acidentes_por_mes.sql`). `acidentes.consultas.executar(conn, nome)` lê o arquivo e devolve os nomes das colunas e as linhas.

Cada consulta é testada contra `tests/fixtures/acidentes_50.csv`: 50 acidentes sintéticos, carregados num schema descartável, com o resultado inteiro (colunas e linhas, na ordem) comparado ao esperado calculado à mão. A fixture tem os casos que mudam o resultado: mês sem acidente, empates na contagem e nos mortos, o mesmo km da mesma BR em duas UFs, km terminado em ,5, linhas sem BR, sem classificação e sem condição meteorológica, UFs fora da comparação, causas empatadas dentro e fora das 3 primeiras posições e as quatro fases do dia.

As escolhas de cada consulta estão no comentário do arquivo:

- por mês: variação sobre o mês anterior com `LAG`, e os meses sem acidente preenchidos com zero por `generate_series`;
- BRs: dois `RANK`, por acidentes e por mortos; ficam as BRs que estão entre as 10 primeiras em pelo menos um;
- hora do dia: as 24 horas, com a classificação da PRF como gravidade;
- dia da semana: `ISODOW` de `data_hora` e os 3 tipos mais frequentes de cada dia;
- condição meteorológica: mortos por acidente, sem as linhas sem condição informada;
- trecho: UF + BR + km inteiro, porque o mesmo par (BR, km) aparece em mais de uma UF;
- comparação entre estados: MG e SC, as duas UFs com mais acidentes, com as taxas ao lado da contagem;
- janela móvel: média de 7 dias por `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`, com os dias sem acidente preenchidos com zero e a média nula nos 6 primeiros dias, em que a janela ainda não está completa;
- causas por UF: `RANK() OVER (PARTITION BY uf ...)`, as 3 primeiras posições com os empates mantidos;
- fase do dia: mortos por 100 acidentes e a parte dos acidentes com vítima fatal.

Nas consultas 4, 5, 9 e 10, o empate de texto é desfeito com `COLLATE "C"`, para que a ordem não dependa do idioma configurado no servidor. A consulta 9 tem na fixture um empate em que as duas ordens divergem: em bytes, `Condutor Dormindo` vem antes de `Condutor deixou ...`; no idioma do servidor, depois.

Por quê: um arquivo por pergunta deixa cada consulta legível e revisável sozinha. Comparar o resultado inteiro, e não só "devolve linhas", pega o erro de lógica (empate, nulo, arredondamento), que é onde consulta de análise erra sem dar erro.

## AR-8 — Relatório gerado por script, com matplotlib

`acidentes.relatorio` roda as 10 consultas por `acidentes.consultas.executar` e escreve o `RELATORIO.md` (uma seção por consulta, com a tabela do resultado) e três gráficos em `docs/img/`: acidentes por mês, acidentes e acidentes com vítimas fatais por hora, e a média móvel de 7 dias. Tabela com mais de 30 linhas vai recolhida num `<details>`. O relatório e os PNGs são gerados no banco carregado com o arquivo de 2025 e commitados; os testes geram os mesmos arquivos a partir da fixture, numa pasta temporária.

Os gráficos usam o `matplotlib` pela `Figure`, sem `pyplot`: não depende de tela nem de estado global. O PNG é gravado sem a versão do `matplotlib` nos metadados, para só mudar quando o gráfico muda. O `matplotlib` entrou com o corte de 14 dias da AR-4 (`exclude-newer` em 05/11/2026).

Por quê: o relatório sai das mesmas consultas testadas; editado à mão, ele poderia divergir delas sem ninguém perceber.
