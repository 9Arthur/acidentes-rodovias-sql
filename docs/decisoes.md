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
