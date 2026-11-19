-- Dia da semana x tipo de acidente: os 3 tipos mais frequentes de cada dia, com a parte
-- de cada um no total do dia. O dia sai de data_hora (ISODOW: 1 = segunda, 7 = domingo),
-- porque o schema não guarda o dia da semana. Empate na contagem é desfeito pelo nome do
-- tipo em ordem de bytes (COLLATE "C"), que não depende do idioma do servidor.
WITH por_dia AS (
    SELECT
        extract(ISODOW FROM data_hora)::int AS isodow,
        tipo,
        count(*) AS acidentes
    FROM acidente
    GROUP BY 1, 2
),
posicoes AS (
    SELECT
        isodow,
        tipo,
        acidentes,
        round(acidentes * 100.0 / sum(acidentes) OVER (PARTITION BY isodow), 1)
            AS pct_do_dia,
        row_number() OVER (
            PARTITION BY isodow ORDER BY acidentes DESC, tipo COLLATE "C"
        ) AS posicao
    FROM por_dia
)
SELECT
    isodow,
    (ARRAY['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'])[isodow]
        AS dia,
    tipo,
    acidentes,
    pct_do_dia
FROM posicoes
WHERE posicao <= 3
ORDER BY isodow, posicao;
