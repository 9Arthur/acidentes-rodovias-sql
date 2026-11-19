-- Condição meteorológica x mortos por acidente: a taxa (mortos / acidentes), não a
-- contagem, porque há muito mais acidentes com céu claro do que com chuva. Acidentes sem
-- condição informada ("Ignorado" na origem, AR-5) ficam de fora: "sem informação" não é
-- uma condição. A coluna acidentes mostra em quantos casos cada taxa se apoia.
SELECT
    condicao_meteo,
    count(*) AS acidentes,
    sum(mortos) AS mortos,
    round(sum(mortos)::numeric / count(*), 4) AS mortos_por_acidente
FROM acidente
WHERE condicao_meteo IS NOT NULL
GROUP BY condicao_meteo
ORDER BY mortos_por_acidente DESC, condicao_meteo COLLATE "C";
