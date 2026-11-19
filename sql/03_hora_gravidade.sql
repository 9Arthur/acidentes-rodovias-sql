-- Hora do dia x gravidade: para cada hora de 0 a 23, o total de acidentes e quantos
-- foram de cada classificação da PRF. As horas vêm de generate_series, para que uma hora
-- sem acidente apareça com zero. Acidente sem classificação conta só no total.
SELECT
    h.hora,
    count(a.id) AS acidentes,
    count(a.id) FILTER (WHERE a.classificacao = 'Sem Vítimas') AS sem_vitimas,
    count(a.id) FILTER (WHERE a.classificacao = 'Com Vítimas Feridas') AS com_feridos,
    count(a.id) FILTER (WHERE a.classificacao = 'Com Vítimas Fatais') AS com_fatais
FROM generate_series(0, 23) AS h (hora)
LEFT JOIN acidente AS a ON extract(HOUR FROM a.data_hora) = h.hora
GROUP BY h.hora
ORDER BY h.hora;
