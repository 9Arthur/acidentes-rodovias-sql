-- Acidentes por mês e tendência: a contagem de cada mês e a variação sobre o mês
-- anterior, em acidentes e em porcentagem (LAG). Os meses vêm de generate_series, do
-- primeiro ao último acidente, para que um mês sem acidente apareça com zero em vez de
-- sumir da série. Sem mês anterior, ou com zero nele, a porcentagem fica nula.
WITH meses AS (
    SELECT generate_series(
        date_trunc('month', min(data_hora)),
        date_trunc('month', max(data_hora)),
        interval '1 month'
    ) AS mes
    FROM acidente
),
por_mes AS (
    SELECT m.mes, count(a.id) AS acidentes
    FROM meses AS m
    LEFT JOIN acidente AS a ON date_trunc('month', a.data_hora) = m.mes
    GROUP BY m.mes
)
SELECT
    mes::date AS mes,
    acidentes,
    acidentes - lag(acidentes) OVER w AS variacao,
    round(
        (acidentes - lag(acidentes) OVER w) * 100.0
        / nullif(lag(acidentes) OVER w, 0),
        1
    ) AS variacao_pct
FROM por_mes
WINDOW w AS (ORDER BY mes)
ORDER BY mes;
