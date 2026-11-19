-- Top 10 BRs por acidentes e por mortos. Cada BR recebe as duas posições (RANK: empate
-- divide a posição e pula as seguintes), e ficam as que estão entre as 10 primeiras em
-- pelo menos um dos dois rankings; assim aparece também a BR com poucos acidentes e
-- muitos mortos. Linhas sem BR (BR 0 na origem, AR-5) ficam de fora.
WITH por_br AS (
    SELECT br, count(*) AS acidentes, sum(mortos) AS mortos
    FROM acidente
    WHERE br IS NOT NULL
    GROUP BY br
),
ranking AS (
    SELECT
        br,
        acidentes,
        mortos,
        rank() OVER (ORDER BY acidentes DESC) AS rank_acidentes,
        rank() OVER (ORDER BY mortos DESC) AS rank_mortos
    FROM por_br
)
SELECT br, acidentes, mortos, rank_acidentes, rank_mortos
FROM ranking
WHERE rank_acidentes <= 10 OR rank_mortos <= 10
ORDER BY rank_acidentes, rank_mortos, br;
