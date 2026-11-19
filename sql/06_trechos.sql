-- Trechos com mais acidentes: UF + BR + km arredondado para o inteiro. A UF entra no
-- trecho porque a quilometragem de cada BR recomeça em cada estado: no arquivo de 2025,
-- 3.481 pares (BR, km inteiro) aparecem em mais de uma UF. round() em numeric arredonda
-- o meio para longe do zero (224,5 vira 225). Linhas sem BR e km (AR-5) ficam de fora;
-- empate na contagem é desfeito por UF, BR e km.
SELECT uf, br, round(km)::int AS km, count(*) AS acidentes
FROM acidente
WHERE br IS NOT NULL AND km IS NOT NULL
GROUP BY uf, br, round(km)::int
ORDER BY acidentes DESC, uf, br, km
LIMIT 10;
