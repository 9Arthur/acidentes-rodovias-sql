-- Letalidade por fase do dia: mortos por acidente (a mesma medida das consultas 5 e 7) e
-- a parte dos acidentes com vítima fatal em cada fase (amanhecer, pleno dia, anoitecer,
-- plena noite). A pergunta é se o acidente é mais grave em alguma fase, não onde há mais
-- acidentes; por isso as taxas, com a contagem ao lado. Acidente sem classificação conta
-- no total e não como fatal. Empate na taxa é desfeito pelo nome da fase em ordem de bytes
-- (COLLATE "C"). Fase nula contaria como uma fase à parte (no arquivo de 2025 não há
-- nenhuma).
SELECT
    fase_dia,
    count(*) AS acidentes,
    sum(mortos) AS mortos,
    round(sum(mortos)::numeric / count(*), 4) AS mortos_por_acidente,
    round(
        count(*) FILTER (WHERE classificacao = 'Com Vítimas Fatais') * 100.0 / count(*), 1
    ) AS pct_com_fatais
FROM acidente
GROUP BY fase_dia
ORDER BY mortos_por_acidente DESC, fase_dia COLLATE "C";
