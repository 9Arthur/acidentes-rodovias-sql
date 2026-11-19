-- Comparação entre dois estados: MG e SC, as duas UFs com mais acidentes em 2025, lado a
-- lado. Além da contagem, as taxas (mortos por acidente e parte dos acidentes com vítima
-- fatal), porque o estado com mais acidentes não é necessariamente o mais letal. Acidente
-- sem classificação conta no total e não como fatal. As UFs ficam fixas: trocar a
-- comparação é trocar a lista do WHERE, este comentário e o título da seção 7 em
-- acidentes.relatorio. A ordem é pelo número de acidentes.
SELECT
    uf,
    count(*) AS acidentes,
    sum(mortos) AS mortos,
    round(sum(mortos)::numeric / count(*), 4) AS mortos_por_acidente,
    round(
        count(*) FILTER (WHERE classificacao = 'Com Vítimas Fatais') * 100.0 / count(*), 1
    ) AS pct_com_fatais
FROM acidente
WHERE uf IN ('MG', 'SC')
GROUP BY uf
ORDER BY acidentes DESC, uf;
