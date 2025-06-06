# token stats

Here are statistics about how many tokens exist in the collections.
`pm` stands for per million.

## 2024

```
+-----+--------+----------+-------+-------------+----------+-------------+------------+
|split|language|collection|   date|   sum_tokens| sum_words|sum_tokens_pm|sum_words_pm|
+-----+--------+----------+-------+-------------+----------+-------------+------------+
| test|  French| documents|2023_08|1.761001846E9|1130451326|  1761.001846| 1130.451326|
| test| English| documents|2023_08|1.648139339E9| 932733087|  1648.139339|  932.733087|
|train|  French| documents|2023_01|2.557447888E9|1640616023|  2557.447888| 1640.616023|
|train| English| documents|2023_01|2.394193906E9|1354823998|  2394.193906| 1354.823998|
| test|  French| documents|2023_06|1.815450509E9|1163542559|  1815.450509| 1163.542559|
| test| English| documents|2023_06|1.693284689E9| 960832171|  1693.284689|  960.832171|
+-----+--------+----------+-------+-------------+----------+-------------+------------+
```

```
+-----+--------+-------------+----------+-------------+------------+
|split|language|   sum_tokens| sum_words|sum_tokens_pm|sum_words_pm|
+-----+--------+-------------+----------+-------------+------------+
| test|  French|3.576452355E9|2293993885|  3576.452355| 2293.993885|
| test| English|3.341424028E9|1893565258|  3341.424028| 1893.565258|
|train|  French|2.557447888E9|1640616023|  2557.447888| 1640.616023|
|train| English|2.394193906E9|1354823998|  2394.193906| 1354.823998|
+-----+--------+-------------+----------+-------------+------------+
```

## 2025

Average per document.

```
+-----+--------+--------+---------------+------------------+-----------------+-----------------+-----------------+
|split|language|   count|     sum_tokens|        avg_tokens|    stddev_tokens|        avg_words|     stddev_words|
+-----+--------+--------+---------------+------------------+-----------------+-----------------+-----------------+
|train|  French|19000580|2.5276152742E10|1330.2832198806564|889.0872247565455|849.6942867533518|549.7494737901972|
+-----+--------+--------+---------------+------------------+-----------------+-----------------+-----------------+
```

Sum over each date.

```
+-----+--------+-------+-------------+----------+-------------+------------+
|split|language|   date|   sum_tokens| sum_words|sum_tokens_pm|sum_words_pm|
+-----+--------+-------+-------------+----------+-------------+------------+
|train|  French|2022-12|3.262787272E9|2091141118|  3262.787272| 2091.141118|
|train|  French|2023-02|3.222316876E9|2065110719|  3222.316876| 2065.110719|
|train|  French|2022-07|2.379143643E9|1515272998|  2379.143643| 1515.272998|
|train|  French|2022-09|1.650183273E9|1052595736|  1650.183273| 1052.595736|
|train|  French|2022-11|3.369244393E9|2148700619|  3369.244393| 2148.700619|
|train|  French|2022-08|2.396089767E9|1525977594|  2396.089767| 1525.977594|
|train|  French|2023-01|3.268659287E9|2094846907|  3268.659287| 2094.846907|
|train|  French|2022-10|3.349512301E9|2136573501|  3349.512301| 2136.573501|
|train|  French|2022-06| 2.37821593E9|1514465079|   2378.21593| 1514.465079|
+-----+--------+-------+-------------+----------+-------------+------------+
```

Sum over all collections.

```
+-----+--------+---------------+-----------+-------------+------------+
|split|language|     sum_tokens|  sum_words|sum_tokens_pm|sum_words_pm|
+-----+--------+---------------+-----------+-------------+------------+
|train|  French|2.5276152742E10|16144684271| 25276.152742|16144.684271|
+-----+--------+---------------+-----------+-------------+------------+
```
