-- Ranking de causas por UF: as 3 causas com mais acidentes em cada estado
-- (RANK() OVER (PARTITION BY uf ...)). RANK mantém os empates: se duas causas dividem o
-- 2º lugar, as duas aparecem, e a UF pode ter mais de 3 linhas. Dentro da mesma posição a
-- ordem é pelo nome da causa em ordem de bytes (COLLATE "C"), que não depende do idioma
-- do servidor. Causa nula contaria como uma causa à parte (no arquivo de 2025 não há
-- nenhuma).
WITH por_uf AS (
    SELECT uf, causa, count(*) AS acidentes
    FROM acidente
    GROUP BY uf, causa
),
ranking AS (
    SELECT
        uf,
        causa,
        acidentes,
        rank() OVER (PARTITION BY uf ORDER BY acidentes DESC) AS posicao
    FROM por_uf
)
SELECT uf, posicao, causa, acidentes
FROM ranking
WHERE posicao <= 3
ORDER BY uf, posicao, causa COLLATE "C";
