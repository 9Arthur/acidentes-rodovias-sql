-- Janela móvel de 7 dias: acidentes por dia e a média dos 7 dias que terminam em cada um
-- (AVG com ROWS BETWEEN 6 PRECEDING AND CURRENT ROW). Os dias vêm de generate_series, do
-- primeiro ao último acidente, para que um dia sem acidente entre com zero na média em
-- vez de sumir da janela. Nos 6 primeiros dias a janela ainda não tem 7 dias, e a média
-- fica nula em vez de ser calculada sobre menos dias.
WITH dias AS (
    SELECT generate_series(
        min(data_hora)::date, max(data_hora)::date, interval '1 day'
    )::date AS dia
    FROM acidente
),
por_dia AS (
    SELECT d.dia, count(a.id) AS acidentes
    FROM dias AS d
    LEFT JOIN acidente AS a ON a.data_hora::date = d.dia
    GROUP BY d.dia
)
SELECT
    dia,
    acidentes,
    CASE
        WHEN count(*) OVER janela = 7 THEN round(avg(acidentes) OVER janela, 2)
    END AS media_7d
FROM por_dia
WINDOW janela AS (ORDER BY dia ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY dia;
