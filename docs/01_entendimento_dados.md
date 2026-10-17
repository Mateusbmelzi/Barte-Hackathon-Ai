# 01 — Entendimento dos dados (EDA) — Fechamento Tarvo set/2026

Autor: agente Analista de dados. Data: 16/10/2026.
Escopo: só entender e documentar. Nenhum arquivo de dados foi alterado. Scripts de análise ficaram no scratchpad (fora do repositório).

Legenda usada no documento:
- **FATO**: visto no dado, calculado por script. Todos os números vêm de cálculo, não de estimativa.
- **INTERP.**: interpretação minha, ainda sem confirmação.
- **S##**: regra confirmada pelo financeiro (ver `docs/00_slack_respostas_financeiro.md`).
- Arredondamento: sempre `Decimal` com `ROUND_HALF_UP`, linha a linha, depois soma (S11).

> Nota de ambiente (FATO): o `python` padrão do PATH (3.11, venv `hermes-agent`) **não tem pandas**. Quem tem pandas 3.0.5 + openpyxl é o Python 3.14 em `C:\Users\mateu\AppData\Local\Python\bin\python`. O dev precisa fixar o interpretador (ou um venv do projeto) no README.

---

## 0. Resumo executivo (números-chave sob as regras confirmadas)

> **Atualização 17/10, 13h:** os números abaixo são do relatório Orbe original (arquivo 01). Com os ajustes tardios do arquivo 06, os valores vigentes são checkout R$ 203.735,34 (1.900 linhas) e notas checkout R$ 203.740,84 — ver `docs/05_ajustes_tardios.md` e `saida/`.

| Item | Valor | Base |
|---|---|---|
| Comissão CHECKOUT (21 lojistas faturáveis, taxa contratada, half-up) | **R$ 207.039,73** (soma algébrica) | S01, S02, S03, S07, S11, S17 |
| CHECKOUT com nota a emitir (20 lojistas com saldo > 0) | **R$ 207.045,23** | S04 |
| Casa do Estudante: saldo do mês | **−R$ 5,50**, sem nota, vira pendência | S04, S07 |
| Atlas Idiomas: fora do faturamento | 57 linhas, bruto R$ 262.138,61, valor_taxa Orbe R$ 7.876,05 | S03 |
| Divergências CHECKOUT | **210 linhas, R$ 16.973,65 líquido** (R$ 17.081,18 em vendas e antecipações, −R$ 107,53 em estornos) | S01, S06, S07 |
| Comissão REMESSA (50% por operação, half-up; 228 operações válidas) | **R$ 39.543,45**, numa nota só para a Ponte Câmbio | S04, S05, S11 |
| Divergência REMESSA (Mundo Aberto, valor cheio) | **R$ 1.418,85** em 23 operações | S05, S10 |
| Spread negativo (fora da comissão, contestar) | 4 operações, **−R$ 1.834,05** | S05, S15 |
| Operação repetida (conta uma vez) | PC-0926-0162, Spread R$ 821,88 | S05, S15 |
| Extrato Aurora | 84 lançamentos (L9..L92), o saldo fecha | — |
| Extrato Meridiano | 100 lançamentos; o OFX não traz o saldo inicial | — |

---

## 1. Arquivo 01 — `01_orbe_relatorio_comissoes_set2026.csv` (adquirente Orbe)

### 1.1 Formato real (FATO)
- Encoding: ASCII puro (0 bytes > 127; nomes já vêm sem acento). Sem BOM. Fim de linha CRLF.
- Separador `;`. Decimal `,`. Sem separador de milhar (0 ocorrências de `.` nos valores).
- Datas `DD/MM/AAAA`.
- 1 linha de cabeçalho e 1.943 linhas de dados, sem rodapé. O arquivo está ordenado por `data_movimento`.
- Colunas (14):

| Coluna | Significado provável | Observação (FATO) |
|---|---|---|
| id_transacao | id único da linha (ref_origem) | 1.943 únicos. Prefixo `TX` para venda/estorno (1.899) e `AN` para antecipação/reversão (44) |
| data_movimento | data do lançamento | 30 datas (01 a 30/09), inclusive fins de semana |
| cod_estabelecimento | EC Orbe (chave para a planilha de taxas) | 22 códigos |
| nome_estabelecimento | nome livre | 31 grafias para 22 ECs (ver §3) |
| tipo_lancamento | VENDA / ESTORNO / ANTECIPACAO / REVERSAO ANTECIPACAO | — |
| modalidade | CREDITO A VISTA / CREDITO PARCELADO / DEBITO / PIX | vazia nas 44 linhas de antecipação e reversão |
| qtd_parcelas | 1..12 | vazia nas 44 de antecipação e reversão; parcelado vai de 2 a 12 |
| bandeira | VISA/MASTERCARD/ELO/HIPERCARD/AMEX | vazia em 227 linhas (183 Pix + 44 antecipação/reversão) |
| valor_bruto | valor da transação; negativo em estorno e reversão | 65 negativos |
| taxa_aplicada_pct | taxa em % (2,69 = 2,69%) | 22 valores distintos |
| valor_taxa | taxa em R$ que a Orbe aplicou | — |
| valor_liquido | bruto − taxa | confere em 1.943 de 1.943 |
| id_referencia | venda ou antecipação original (em estorno e reversão) | preenchido só nas 65 negativas |
| data_venda_original | data da venda original | preenchido só nas 65 negativas |

### 1.2 Volumes e totais (FATO)

| tipo_lancamento | modalidade | n | valor_bruto | valor_taxa | valor_liquido |
|---|---|---:|---:|---:|---:|
| VENDA | CREDITO A VISTA | 575 | 966.500,34 | 25.768,46 | 940.731,88 |
| VENDA | CREDITO PARCELADO | 920 | 5.317.556,89 | 185.936,67 | 5.131.620,22 |
| VENDA | DEBITO | 168 | 82.523,09 | 1.230,27 | 81.292,82 |
| VENDA | PIX | 177 | 182.618,90 | 1.622,93 | 180.995,97 |
| **VENDA** | | **1.840** | **6.549.199,22** | **214.558,33** | **6.334.640,89** |
| ESTORNO | CRED. A VISTA / PARCELADO / DEBITO / PIX | 16 / 31 / 6 / 6 | | | |
| **ESTORNO** | | **59** | **−216.346,03** | **−7.108,69** | **−209.237,34** |
| **ANTECIPACAO** | (vazia) | **38** | **1.451.981,71** | **30.491,41** | **1.421.490,30** |
| **REVERSAO ANTECIPACAO** | (vazia) | **6** | **−288.606,34** | **−6.060,69** | **−282.545,65** |
| **TOTAL** | | **1.943** | **7.496.228,56** | **231.880,36** | **7.264.348,20** |

Parcelado por faixa (VENDA): 597 entre 2x e 6x e 323 entre 7x e 12x. Distribuição de qtd_parcelas em todo o parcelado: 2x=146, 3x=99, 4x=131, 5x=123, 6x=117, 7x=53, 8x=51, 9x=64, 10x=53, 11x=61, 12x=53.

### 1.3 Arredondamento da Orbe (FATO, regra S11)
- Comparei `valor_taxa` com `valor_bruto × taxa/100`: **1.943 de 1.943 linhas batem com TRUNCAMENTO** (em direção a zero). Em 942 linhas o truncamento e o half-up dão o mesmo valor. Nas outras 1.001, o valor da Orbe só bate com o truncamento. Nenhuma linha bate só com half-up.
- Impacto: a soma por truncamento fica R$ 9,37 abaixo da soma por half-up com as mesmas taxas aplicadas.
- Por S11, truncamento não é divergência. Consequência: nas linhas sem divergência de taxa, a comissão da Tarvo (half-up) fica **R$ 7,99 acima** do `valor_taxa` da Orbe, com diferença de centavo em 855 linhas. **Não marcar isso como divergência.**

---

## 2. Arquivo 02 — `02_tabela_taxas_contratadas.xlsx` (planilha manual)

### 2.1 Estrutura (FATO)
- 2 abas, as duas visíveis: `Taxas vigentes` (A1:L32) e `ANTIGO 2025 - nao usar` (A1:F13). Não há linhas ou colunas ocultas, nomes definidos, filtros nem validações.
- `Taxas vigentes`:
  - A1 é o título: "atualizar sempre que o comercial fechar!!". A2 diz "última atualização: 02/09 - Bia" (cinza, itálico).
  - Linha 4 tem os grupos: **D4:I4 mesclada** "CARTÃO / PIX (MDR)" e J4 "REMESSA" (sem mesclar).
  - Linha 5 é o cabeçalho real: Lojista, CNPJ, EC Orbe, Débito, Crédito à vista, Créd. 2-6x, Créd. 7-12x, Pix, Antecipação, Spread remessa, Vigência, Obs.
  - Dados nas linhas 6 a 30. A32 traz a nota "* spread em branco = padrão" (o padrão é 1,5%, confirmado em S05).
  - **Linha 30 riscada** (strike, cinza): Globo Trotter Viagens Ltda, CNPJ 22348118000148, EC 1157874034, "INATIVO desde jul/26". Esse EC e esse CNPJ não aparecem em nenhum outro arquivo.
  - **Comentário em A13** (Casa do Estudante): "conversar com Diego (comercial) sobre condição especial". L13 diz "cliente estratégico - ver c/ comercial". A condição é a taxa zero de set a dez (S07), que **não está escrita na planilha**.
- Problemas de tipo e formato (FATO):
  - Taxas em número fracionário (0,0149 com formato `0.00%`) em quase tudo. Mas **Oxford Prep (L20) e Sol Nascente (L21) têm as taxas como TEXTO** ("1,49%").
  - CNPJ misturado: com máscara ("22.224.579/0001-09"), só dígitos em texto, ou **número**. **Fluente (L14) = 3229837000103 e Campus Global (L25) = 8780784000120 perderam o zero à esquerda.** O dev tem que fazer `zfill(14)`.
  - Spread de Canguru (L29) = texto "padrão". Spread vazio em vários lojistas (padrão 1,5%, S05).
  - Vigência como texto: "01/01/2026", "01/06/2026", "até 14/09/2026", "a partir de 15/09/2026". Globo Trotter não tem vigência.
  - Bridge tem **2 linhas** (L6 até 14/09 com crédito à vista 2,59%; L7 a partir de 15/09 com 2,19%), com mesmo CNPJ e mesmo EC. Obs: "só mudou o crédito à vista".
  - Sem EC Orbe: Horizonte Viagens (L8), Kiwi (L9, "EC pendente"), Novo Horizonte (L28), e os dois só de remessa, Ponte Aérea (L16) e Nórdica (L23). O de-para dos 3 primeiros foi confirmado em S03.
  - O carimbo "última atualização 02/09" é anterior à data da linha "a partir de 15/09". Ou a renegociação foi lançada antes, ou o carimbo está velho (INTERP.).
- `ANTIGO 2025 - nao usar` (FATO): 12 lojistas com Débito 1,69 / Crédito à vista 2,99 / Parcelado 3,49 / Pix 0,99. É a única fonte com o **CNPJ da Atlas Idiomas (39566044000119)**. Por S03, não se usa para faturar.

### 2.2 Taxas por lojista na aba vigente (FATO, em %)

| Linha | Lojista | CNPJ (14 díg.) | EC | Déb | Vista | 2-6x | 7-12x | Pix | Antec | Spread |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | Escola Bridge de Idiomas Ltda (até 14/09) | 22224579000109 | 1075624862 | 1,49 | 2,59 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 7 | Bridge Idiomas (NOVA) (a partir de 15/09) | 22224579000109 | 1075624862 | 1,49 | **2,19** | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 8 | Horizonte Viagens | 78576234000179 | (vazio) | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 9 | Kiwi Experience | 07752116000126 | (vazio) | 1,49 | 2,59 | 3,19 | 3,79 | 0,89 | 2,10 | (vazio) |
| 10 | Rota Global Intercâmbio Ltda | 95927868000148 | 1074504011 | 1,49 | 2,49 | 2,99 | 3,59 | 0,89 | 2,10 | 1,50 |
| 11 | Vela | 20987545000140 | 1086291869 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 12 | Andes Expedições Ltda | 85694108000184 | 1058961395 | **1,39** | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 13 | Casa do Estudante Viagens Ltda | 00520815000100 | 1018325654 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | 1,50 |
| 14 | Fluente Idiomas Online Ltda | 03229837000103 | 1066100982 | 1,49 | 2,69 | 3,19 | 3,79 | **0,79** | 2,10 | — |
| 15 | Mundo Aberto | 17217888000111 | 1037647039 | 1,49 | 2,49 | 2,99 | 3,79 | 0,89 | 2,10 | **1,20** |
| 16 | Ponte Aérea Estudantil Ltda | 95739378000118 | — | — | — | — | — | — | — | (vazio) |
| 17 | EduAbroad | 16181276000153 | 1020660828 | 1,49 | 2,69 | 3,19 | **3,49** | 0,89 | 2,10 | 1,30 |
| 18 | Dublin Hub Intercâmbio Ltda | 68567965000102 | 1014537966 | 1,49 | 2,59 | 3,19 | 3,79 | 0,89 | 2,10 | 1,50 |
| 19 | Maple Study Assessoria Educacional Ltda | 34671260000100 | 1041180753 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | 1,50 |
| 20 | Oxford Prep Cursos Ltda (texto) | 23109187000161 | 1000960410 | 1,49 | 2,59 | **3,09** | 3,79 | 0,89 | 2,10 | — |
| 21 | Sol Nascente Viagens Ltda (texto) | 89779285000114 | 1064304917 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 22 | Trilha Jovem Turismo Ltda | 21394880000106 | 1068443135 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | — |
| 23 | Nórdica Educação Internacional Ltda | 14760206000124 | — | — | — | — | — | — | — | 1,25 |
| 24 | Bagagem Livre Turismo Ltda | 50900987000179 | 1087276103 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | 1,50 |
| 25 | Campus Global Ltda | 08780784000120 | 1070531381 | 1,49 | 2,69 | **2,99** | 3,79 | 0,89 | 2,10 | — |
| 26 | Lisboa Cursos e Viagens Ltda | 61720397000180 | 1023622151 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | 1,60 |
| 27 | Bem-Vindo Exchange Ltda | 67869675000142 | 1098729012 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | 1,50 |
| 28 | Novo Horizonte Intercambio | 66564512000199 | (vazio) | 1,49 | **2,39** | **2,89** | 3,79 | 0,89 | 2,10 | 1,40 |
| 29 | Canguru | 53857560000123 | 1061760196 | 1,49 | 2,69 | 3,19 | 3,79 | 0,89 | 2,10 | "padrão" |
| 30 | ~~Globo Trotter Viagens Ltda~~ (inativo) | 22348118000148 | 1157874034 | ~~1,49~~ | ~~2,69~~ | ~~3,19~~ | ~~3,79~~ | ~~0,89~~ | ~~2,10~~ | — |

Faixas (FATO): "Créd. 2-6x" e "Créd. 7-12x" casam com `CREDITO PARCELADO` por `qtd_parcelas`, e Antecipação casa com tipo ANTECIPACAO. Nos lojistas sem divergência, a taxa aplicada pela Orbe bate exatamente com essa leitura. Exemplos: EduAbroad cobra 3,49 em 7-12x (16 linhas), Fluente cobra 0,79 no Pix (8 linhas), Andes cobra 1,39 no débito (7 linhas).

---

## 3. Arquivo 03 — `03_email_ponte_cambio_relatorio_set2026.eml` (Ponte Câmbio)

### 3.1 E-mail (FATO)
- MIME multipart. O corpo é text/plain utf-8 quoted-printable. O assunto vem codificado (RFC 2047): "Relatório mensal de operações - TARVO - 09/2026".
- Enviado em 02/10/2026 07:15 por relatorios@pontecambio.com.br. Ponte Câmbio S.A., CNPJ **75.374.179/0001-46** (tomadora da nota de remessa, S04).
- Corpo, em paráfrase: repasse de **50% do spread realizado** em **06/10/2026**, mediante a nota fiscal de intermediação. Operações "APROVADO C/ RESSALVA" seguem normalmente para liquidação. Divergências devem ser respondidas em até 5 dias úteis.
- Anexo base64 `PonteCambio_Relatorio_TARVO_092026.xlsx` (30.021 bytes), extraído com o pacote `email` do Python.

### 3.2 Anexo, aba `Operações` (FATO)
- A1:A3 é o cabeçalho do relatório (parceiro, CNPJ da Tarvo 84.626.315/0001-39, competência 09/2026, gerado em 02/10/2026 07:12). A linha 5 é o cabeçalho das colunas. Os dados vão da **linha 6 à 238 (233 linhas)**. A linha 239 é vazia. Rodapé: A240 "Total de operações:" = 233 e A241 "Spread total R$:" = 78.073,59. Ler com `header=4` e filtrar `Nº Operação` que começa com `PC-`.
- Colunas: Nº Operação | Data Contratação | Data Liquidação (datas Excel, formato DD/MM/YYYY) | CNPJ Cliente (texto, **70 com máscara e 163 só dígitos**, todos com 14 dígitos) | Cliente (**truncado em 20 caracteres**, com acento) | Moeda | Valor ME | Taxa Cliente | PTAX Ref. | Valor R$ | Spread R$ | Spread % (fração) | Spread Estimado R$ (D-1) | IOF R$ | Status Compliance | Observação.
- Identidades verificadas em 233 de 233 linhas:
  - `Valor R$ = round(Valor ME × Taxa Cliente, 2)`
  - `Spread R$ = round(Valor ME × (Taxa Cliente − PTAX), 2)`
  - `Spread % = round((Taxa Cliente − PTAX)/PTAX, 6)`. **A base do % é PTAX × ME, não o Valor R$.**
  - `IOF R$ = 0,38% do Valor R$`
- Aba `Resumo`: Qtd, Volume ME e Spread R$ por moeda. **Bate exatamente** com a soma das 233 linhas, **incluindo a duplicata**.

### 3.3 Volumes (FATO)
- 233 linhas e 232 Nº de operação distintos. Datas de contratação de 01/09 a 30/09, liquidação de 02/09 a 01/10.
- Totais das 233 linhas: Valor ME 1.155.457,17; Valor R$ 5.645.804,52; **Spread R$ 78.073,59**; Spread Estimado D-1 80.892,62; IOF 21.454,07.
- Por moeda (n / Spread R$): USD 37 / 14.007,38; EUR 33 / 16.074,48; GBP 36 / 17.739,02; CAD 42 / 10.705,21; AUD 48 / 11.329,45; NZD 37 / 8.218,05.
- Status: APROVADO 217 (Spread 73.244,22); **APROVADO C/ RESSALVA 16** (Spread 4.829,37). Pelo e-mail e por S05, o status não muda nada.
- Observação: "Taxa travada no pedido (D-1)" em 4 linhas, que são exatamente as de spread negativo; "reprocessada" em 1 linha, que é a duplicata.
- 6 operações contratadas em 30/09 liquidam em 01/10 (Spread 2.078,71). Vale a data de contratação (S05), então entram em setembro.

### 3.4 Anomalias Ponte (FATO)
| Anomalia | Operações | Valores | Regra |
|---|---|---|---|
| **Nº de operação repetido** | PC-0926-0162 (linhas Excel 76 e 77, Bagagem Livre, USD 10.429,99). A 2ª linha traz "reprocessada" | Spread R$ 821,88 duplicado | Conta uma vez e entra na lista para a Ponte corrigir (S05, S15). **Prova bancária**: o TED de 22/09 para a Ponte e os PIX da Bagagem cobrem a operação **uma vez só** (ver §6.3) |
| **Spread negativo** | PC-0926-0210 (Ponte Aérea, −687,52), PC-0926-0326 (Canguru, −509,22), PC-0926-0491 (Dublin Hub, −292,28), PC-0926-0545 (Novo Horizonte, −345,03) | Total **−1.834,05**. Spread % entre −1,55% e −1,65%. Spread Estimado D-1 positivo nas 4 (total 1.622,90) | Fora da comissão e da nota, pendência de contestação (S05, S15) |
| **Spread acima do contratado** | Mundo Aberto: as 23 operações a ~1,50% contra 1,20% contratado | Ver §3.5 | Divergência (S05, S10, S13) |
| Spread por lojista | Os outros 13 CNPJs batem com a planilha, com diferença máxima de 0,0016 p.p. (arredondamento do %). Kiwi, Canguru ("padrão") e Ponte Aérea, que têm o spread em branco ou "padrão", aparecem a 1,50% | — | Padrão = 1,5% (S05) |

### 3.5 Comissão e divergência REMESSA sob as regras confirmadas (FATO)
- Base: 233 − 1 duplicata − 4 negativas = **228 operações**, Spread R$ **79.085,76**.
- **Comissão = Σ round_half_up(Spread R$ / 2) = R$ 39.543,45.**
  - Atenção: 114 operações têm centavo ímpar, então cai em meio centavo. Com half-even (Decimal) dá 39.542,89. Com `round()` do Python sobre float dá 39.542,85. **Só o half-up é correto (S11).**
- Comparativos: os 50% do total bruto do relatório (78.073,59 / 2) dariam 39.036,80. Sem duplicata e com os negativos dentro, 38.625,85.
- **Divergência Mundo Aberto (valor cheio, S10)** = Σ round_half_up((Spread % − 1,20%) × PTAX × Valor ME) = **R$ 1.418,85** em 23 operações. A outra fórmula, Spread R$ − 1,2% × PTAX × ME, dá 1.418,88. A diferença de R$ 0,03 vem do Spread % estar arredondado a 6 casas. Pela instrução do gestor, a fórmula é a primeira.
- Tolerância (subsídio para S10): nos outros 205 casos válidos, |Δp.p.| é no máximo 0,0016 p.p. e |Δ R$| no máximo 0,74 (média 0,12; nenhum ≥ R$ 1,00). Em Mundo Aberto, o Δ mínimo é 0,299 p.p. Um limite de **|Δ| < 0,01 p.p.** (ou < R$ 1,00) separa as duas populações sem alarme de centavo.

Comissão REMESSA por lojista (gabarito, half-up por operação):

| CNPJ | Lojista | Ops válidas | Spread R$ válido | Comissão 50% | Excluídas |
|---|---|---:|---:|---:|---|
| 00520815000100 | Casa do Estudante Viagens Ltda | 18 | 6.151,74 | 3.075,91 | — |
| 07752116000126 | Kiwi Experience | 15 | 5.336,64 | 2.668,36 | — |
| 14760206000124 | Nórdica Educação Internacional Ltda | 18 | 5.828,25 | 2.914,18 | — |
| 16181276000153 | EduAbroad | 16 | 5.040,46 | 2.520,25 | — |
| 17217888000111 | Mundo Aberto | 23 | 7.095,25 | 3.547,69 | — (divergência 1.418,85) |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | 25 | 8.589,91 | 4.295,03 | — |
| 50900987000179 | Bagagem Livre Turismo Ltda | 8 | 2.585,33 | 1.292,67 | duplicata PC-0926-0162 |
| 53857560000123 | Canguru | 22 | 7.528,01 | 3.764,05 | negativa PC-0926-0326 |
| 61720397000180 | Lisboa Cursos e Viagens Ltda | 16 | 6.392,62 | 3.196,36 | — |
| 66564512000199 | Novo Horizonte Intercambio | 10 | 4.414,89 | 2.207,48 | negativa PC-0926-0545 |
| 67869675000142 | Bem-Vindo Exchange Ltda | 2 | 726,44 | 363,22 | — |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | 13 | 3.545,15 | 1.772,61 | negativa PC-0926-0491 |
| 95739378000118 | Ponte Aérea Estudantil Ltda | 14 | 6.014,55 | 3.007,30 | negativa PC-0926-0210 |
| 95927868000148 | Rota Global Intercâmbio Ltda | 28 | 9.836,52 | 4.918,34 | — |
| **Total** | 14 lojistas | **228** | **79.085,76** | **39.543,45** | |

Nota de remessa (S04): **1 nota para Ponte Câmbio S.A. (75374179000146), R$ 39.543,45**.

---

## 4. Arquivo 04 — `04_plano_de_contas_fenix_erp.csv` (ERP Fênix)

- FATO: encoding **cp1252/latin-1** (bytes 0xC7, 0xE2, 0xE3... que não são UTF-8 válido). Separador `;`. CRLF. 1 cabeçalho e 52 contas. Colunas: COD_CONTA; DESCRICAO; TIPO (SINTETICA/ANALITICA); NATUREZA (D/C); ACEITA_LANCTO (S/N); COD_SUPERIOR; DT_CRIACAO (todas 15/01/2024).
- 32 ANALITICA, todas com ACEITA_LANCTO=S. 20 SINTETICA, todas com N. Todo COD_SUPERIOR existe.
- Contas lançáveis: 1.1.01.001 Banco Aurora; 1.1.01.002 Banco Meridiano; 1.1.02.001 Aplicação automática Meridiano; 1.1.03.001 Recebíveis Orbe; 1.1.03.002 Comissões a receber câmbio; 1.1.03.003 Adiantamentos; 1.1.09.001 Transferências entre contas próprias; 1.1.09.002 Créditos não identificados; 2.1.01.001 Repasses a lojistas a pagar; 2.1.01.002 Devoluções e créditos a lojistas; 2.1.02.001 Recursos de lojistas p/ remessas; 2.1.03.001 PIS; .002 COFINS; .003 ISS; .004 IRRF; 2.1.04.001 Salários a pagar; .002 INSS; .003 FGTS; 2.1.05.001 Fornecedores; 3.1.01 Receita MDR; 3.1.02 Receita antecipação; 3.1.03 Receita intermediação câmbio; 3.2.01 Rendimentos; 4.1.01 Salários; 4.2.01 Tarifas; 4.2.02 Aluguel/condomínio; 4.2.03 Cloud; 4.2.04 Softwares; 4.2.05 Seguros; 4.2.06 Contábeis/jurídicos; 4.3.01 IOF; 4.3.02 Juros e multas.
- FATO de formato: as contas de receita 3.1.01/02/03 e 3.2.01 são analíticas em nível 3. Não seguem o padrão `x.x.xx.xxx` das outras.

---

## 5. Arquivos 05a/05b — extratos

### 5.1 Aurora — `05a_extrato_banco_aurora_cc4471_set2026.csv`
- Formato (FATO): **UTF-8 sem BOM** (tem "Õ" em "ANDES EXPEDICÕES"). Fim de linha **LF**. Separador `;`. Decimal `,` com milhar `.` ("612.334,81"). Sinal negativo à esquerda. Datas DD/MM/AAAA. Toda linha tem 5 campos.
- Layout físico:
  - L1 a L6: cabeçalho do banco (cliente Tarvo, CNPJ 84.626.315/0001-39, ag 0318, cc 4471-0, período). L6 é vazia.
  - L7: cabeçalho das colunas (Data; Lançamento; Documento; Valor (R$); Saldo (R$)).
  - **L8 = SALDO ANTERIOR 612.334,81 (31/08)**.
  - **L9 a L92 = 84 lançamentos**. `ref_origem` = "L{número físico}".
  - L93 vazia, L94 SALDO FINAL −1.920.088,60, L95 aviso.
- Documento preenchido só nos TEDs da Orbe (21 números de 6 dígitos).
- **O saldo fecha** (FATO): 612.334,81 + (−2.532.423,41) = −1.920.088,60. O saldo corrido confere linha a linha (0 diferenças). Fica negativo a partir de L30, com mínimo −2.289.532,94 em L84. Pela S16 é conta garantida.
- Créditos 3.576.996,29; débitos −6.109.419,70.

| Categoria (padrão de descrição) | n | Soma R$ | Linhas | Conta (contrapartida, S12) | Base |
|---|---:|---:|---|---|---|
| TED RECEBIDA 99.876.669/0001-09 ORBE ADQUIRENCIA SA | 21 | 3.557.246,29 | L9, L11, L13, L14, L17, L25, L31, L43, L45, L46, L49, L51, L52, L56, L59, L64, L75, L85, L88, L89, L91 | 1.1.03.001 | S16 |
| PIX ENVIADO <lojista> | 44 (22 lojistas × 2) | −4.230.267,61 | L18–L24, L26–L30, L32–L41, L60–L63, L66–L74, L76–L84 | 2.1.01.001 | INTERP. forte |
| TRANSF ENTRE CONTAS P/ BCO MERIDIANO | 4 | −1.450.000,00 | L12, L44, L58, L92 | 1.1.09.001 | — |
| PAGTO SALARIOS - FOLHA 08/2026 | 1 | −184.732,18 | L15 | 2.1.04.001 | S08, S12 |
| PAGTO ISS SAO PAULO DAMSP 08/2026 | 1 | −21.877,40 | L42 | 2.1.03.003 | S08 |
| GPS INSS 08/2026 | 1 | −51.320,66 | L54 | 2.1.04.002 | S08 |
| GRF FGTS 08/2026 | 1 | −14.778,57 | L55 | 2.1.04.003 | S08 |
| DEBITO DARF 0561 IRRF | 1 | −22.104,35 | L57 | 2.1.03.004 | S08 |
| DEBITO DARF 8109 PIS | 1 | −9.811,20 | L86 | 2.1.03.001 | S08 |
| DEBITO DARF 2172 COFINS | 1 | −45.282,46 | L87 | 2.1.03.002 | S08 |
| BOLETO CONDOMINIO ED. FARIA LIMA 3311 | 1 | −28.450,00 | L16 | 4.2.02 | S12 |
| DEB AUT AMAZON WEB SERVICES BR | 1 | −41.208,77 | L47 | 4.2.03 | S12 |
| CARTAO PJ - GOOGLE WORKSPACE | 1 | −2.210,00 | L48 | 4.2.04 | S12 |
| PIX ENVIADO CONTABILIDADE EXATA LTDA | 1 | −6.800,00 | L53 | 4.2.06 | S12 |
| TAR PACOTE SERVICOS PJ / TAR TED/PIX AVULSAS 09/2026 | 2 | −576,50 | L10 (−389,00), L90 (−187,50) | 4.2.01 | S12 |
| PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO | 1 | 7.350,00 | L50 | 1.1.09.002 + pendência | S09 (CNPJ não aparece em nenhum outro arquivo) |
| DEVOLUCAO PIX - MUNDO ABERTO INTERC | 1 | 12.400,00 | L65 | 2.1.01.001 (proposta) + pendência | S09; proposta do Lucca ainda sem resposta |

### 5.2 Meridiano — `05b_extrato_banco_meridiano_cc90233_set2026.ofx`
- Formato (FATO): OFX 1.02 SGML, cabeçalho `CHARSET:1252`, CRLF, tags sem fechamento nos campos folha. Únicos bytes não-ASCII: 0xC2 (Â) e 0xC9 (É), em cp1252.
- Banco 0477, agência 0091, conta 90233-5. DTSTART 01/09 e DTEND 30/09. Todo DTPOSTED tem hora 12:00:00[-3:BRT].
- 100 STMTTRN: 72 CREDIT e 28 DEBIT. O sinal de TRNAMT bate com TRNTYPE em 100 de 100. FITID único (`MRD2026090003`…`MRD2026090696`, crescente). CHECKNUM único.
- **Só existe LEDGERBAL = 1.320.453,26 (30/09). Não há saldo inicial nem AVAILBAL.** Movimento líquido +1.116.335,23, então o saldo inicial implícito seria 204.118,03, mas **não dá para validar** (créditos 7.318.364,90; débitos −6.202.029,67).

| Categoria (MEMO) | n | Soma R$ | Conta (contrapartida) | Base |
|---|---:|---:|---|---|
| PIX RECEB <lojista> (casa com operações Ponte) | 64 | 5.611.447,12 | 2.1.02.001 | conciliado (§6.3) |
| PIX RECEB PONTE AEREA ESTUDANTIL L (sem acento), 17/09, **MRD2026090425** | 1 | 18.240,00 | **sem conta óbvia**: nenhuma operação Ponte corresponde | anomalia nova (§7) |
| TED ENVIADA PONTE CAMBIO SA LIQ OPERACOES | 21 | −5.611.447,12 | 2.1.02.001 | conciliado (§6.3) |
| TED RECEBIDA TARVO PAGAMENTOS LTDA - MESMA TITULARIDADE | 3 | 1.150.000,00 | 1.1.09.001 | — |
| TED RECEB PONTE CAMBIO SA REPASSE COMISSAO 08/2026 (MRD2026090132) | 1 | 61.884,12 | 1.1.03.002 | S08, S12 |
| APLICACAO AUTOMATICA CDB DI | 3 | −588.124,00 | 1.1.02.001 | — |
| RESGATE AUTOMATICO CDB DI | 3 | 472.881,00 | 1.1.02.001 | — |
| RENDIMENTO APLIC AUTOMATICA (MRD2026090680) | 1 | 3.912,66 | 3.2.01 | — |
| TARIFA MANUTENCAO CONTA PJ (−129,90) / TARIFA PACOTE CAMBIO (−450,00) | 2 | −579,90 | 4.2.01 | S12 |
| SEGURO EMPRESARIAL PARC 09/12 (MRD2026090292) | 1 | −1.830,44 | 4.2.05 | S12 (sem indício de provisão) |
| IOF S/ OPERACAO CREDITO (MRD2026090586) | 1 | −48,21 | 4.3.01 | — |

Total dos PIX recebidos de lojistas: 65 lançamentos e 5.629.687,12 (64 conciliados + 1 de 18.240,00 sem lastro).

---

## 6. Conciliações (FATO)

### 6.1 Aurora ↔ Meridiano (transferências)
| Aurora | Meridiano | Status |
|---|---|---|
| L12 02/09 −350.000,00 | MRD2026090107 02/09 +350.000,00 | casa |
| L44 11/09 −420.000,00 | MRD2026090274 11/09 +420.000,00 | casa |
| L58 21/09 −380.000,00 | MRD2026090454 21/09 +380.000,00 | casa |
| **L92 30/09 −300.000,00** | — | **em trânsito**: entra no Meridiano em 01/10 (S09). Classificar em 1.1.09.001 |

### 6.2 Orbe ↔ Aurora
- TEDs Orbe somam 3.557.246,29 (21). O valor_liquido Orbe do mês soma 7.264.348,20. **Não concilia por data.** Testei todas as 4.095 combinações de grupos (tipo × faixa), 3 defasagens (D, D−1, D−2) e 3 colunas (bruto, taxa, líquido): nenhuma explica nem 3 TEDs.
- PIX enviados aos lojistas (44 lançamentos, 4.230.267,61): testei toda janela contínua de dias da Orbe por EC (líquido e bruto), em 1.936 testes, com **0 acertos**.
- Pela S16, isso é esperado: crédito é liquidado ao longo dos meses e não se concilia parcela a parcela neste fechamento. Os créditos Orbe só são classificados em 1.1.03.001.
- Indício útil (FATO): o Aurora paga exatamente **22 favorecidos**, um para cada um dos 22 ECs da Orbe. Há "NOVO HORIZONTE INTERCAMBIO" e não existe um "HORIZONTE INTERCAMBIO" isolado, o que é consistente com S03.

### 6.3 Meridiano ↔ Ponte
- **TED ENVIADA PONTE do dia D = Σ (Valor R$ + IOF R$) das operações contratadas em D**. Bate nas 21 datas, **com a duplicata contada uma vez**. Com a duplicata, só 22/09 diverge: TED 325.387,31 contra 381.198,78, diferença de 55.811,47 = 55.600,19 + IOF 211,28 da PC-0926-0162. Total de TEDs = 5.611.447,12 = total Ponte sem a duplicata.
- **PIX RECEB por lojista na data d (01, 08, 15, 22 e 29/09) = Σ (Valor R$ + IOF) das operações do lojista contratadas em [d, próximo d)**. Bate em **70 de 70** pares lojista × semana. No total, as somas por lojista batem com o Ponte sem a duplicata, exceto Ponte Aérea: +18.240,00 do PIX MRD2026090425, que não corresponde a nenhuma operação.
- Interpretação (INTERP.): o lojista adianta o valor da semana para a Tarvo, e a Tarvo paga a Ponte no dia da contratação. Os spreads negativos foram pagos normalmente pelos lojistas.

---

## 7. Anomalias com exemplos reais

| # | Anomalia (FATO) | Exemplos | Quantificação | Tratamento confirmado |
|---|---|---|---|---|
| A1 | **Rota Global cobrada +0,50 p.p. desde 12/09** em todo crédito (vista 2,99 contra 2,49; 2-6x 3,49 contra 2,99; 7-12x 4,09 contra 3,59). Até 11/09 a taxa estava certa. Débito, Pix e antecipação estão certos | TX88423890 (12/09), TX88444545 (30/09). Estornos que herdam a taxa: TX88446419, TX88446585, TX88446596, TX88446647 | 83 vendas +1.644,72; 4 estornos −98,44; líquido **1.546,28** | divergência (S06) |
| A2 | **Bridge com vigência ignorada**: 5 vendas à vista de 15 a 18/09 a 2,59% (deveria ser 2,19%). De 23/09 em diante vem 2,19% | TX88428053, TX88428930, TX88429199, TX88429931, TX88431123 | **29,95** | divergência |
| A3 | **Casa do Estudante: tarifa zero não aplicada pela Orbe** (a Orbe cobrou a taxa cheia) | 113 vendas, 4 antecipações (ex. AN88445802) | divergência 12.578,94 + 2.827,57 − 9,09 (estorno de set, TX88446763) = **15.397,42** | divergência, Helena devolve (S07) |
| A4 | **Atlas Idiomas (EC 1076801732) sem contrato na aba vigente**. Taxas aplicadas: déb 1,99 / vista 3,49 / 2-6x 3,99 / 7-12x 4,49 / Pix 0,99. Começou em 10/09 (1ª linha TX88421353) | 57 linhas; 4 antecipações em 15/09 (AN88445637, AN88445646, AN88445703, AN88445766), somando 179.592,82 contra 55.357,50 de vendas acumuladas até a data | bruto 262.138,61, valor_taxa 7.876,05 | não faturar, pendência para o comercial (S03) |
| A5 | **Estornos de vendas de agosto**: id_referencia não existe no arquivo | TX88444848 (ref TX87651902, 22/08), TX88444966, TX88444985, TX88445015, TX88445053, TX88445084, TX88445133, TX88445268, TX88445463 | 9 linhas, bruto −29.927,08, taxa Orbe −941,70, comissão contratada −941,71 | abatem setembro (S02) |
| A6 | Estornos e reversões de setembro: os 56 com referência no arquivo batem 100% em EC, valor (inverso), taxa, data original, modalidade e parcelas. **A bandeira diverge em 39 de 44 estornos de cartão** (ex. TX88444937 AMEX contra a venda TX88410045 VISA) | — | — | não usar bandeira como chave (INTERP.) |
| A7 | Reversões de antecipação revertem 100% do valor | AN88445093 → AN88445076 (Kiwi, 52.314,21) etc. | 6 linhas, −288.606,34 | anulam a taxa da antecipação revertida (S04) |
| A8 | **Nomes inconsistentes no mesmo EC** (31 grafias para 22 ECs) | 1037647039: "MUNDO ABERTO INTERC LTDA", "MUNDO ABERTO INTERCAMBIO", "Mundo Aberto"; 1020660828: "EDU ABROAD CONSULTORIA"/"EDUABROAD"; 1075624862: "BRIDGE IDIOMAS"/"ESCOLA BRIDGE IDIOMAS" | — | chave = EC |
| A9 | **3 ECs Orbe sem EC na planilha** | 1038867654, 1043300981, 1043396662 | 233 linhas | de-para em S03. Com ele, as taxas aplicadas batem 100% com o contrato |
| A10 | Ponte: duplicata, spread negativo, Mundo Aberto | §3.4 | §3.5 | S05 |
| A11 | **PIX de 18.240,00 "PONTE AEREA ESTUDANTIL L"** (grafia sem acento, valor redondo, fora do ciclo semanal) sem operação Ponte correspondente | MRD2026090425 (17/09) | 18.240,00 | **em aberto** (§9) |
| A12 | Crédito sem identificação no Aurora | L50 (CNPJ 38686002000180) | 7.350,00 | 1.1.09.002 + pendência (S09) |
| A13 | Devolução de PIX Mundo Aberto | L65 | 12.400,00 | pendência (S09) |
| A14 | Transferência sem par | L92 | 300.000,00 | em trânsito (S09) |
| A15 | IDs de venda da Atlas fora da sequência cronológica: 16 vendas com id de 4 a 27 dias "antes" da data | TX88413380 (30/09, id típico de 03/09), TX88410188 (12/09) | — | sem impacto em valor. Só curiosidade, não usar id como data (INTERP.) |
| A16 | Planilha: CNPJ como número sem zero à esquerda (L14, L25), taxas como texto (L20, L21), "padrão" (L29), vigência textual (L6, L7), linha riscada (L30) | — | — | o parser tem que tratar |
| A17 | Duplicidade na Orbe: **nenhuma** (0 linhas repetidas por EC + data + tipo + modalidade + parcelas + bandeira + bruto). Coincidência de valor: 7 pares em ECs ou modalidades diferentes (ex. TX88416568 × TX88421861, Lisboa 1.155,61, vista × parcelado 3x) | — | — | não tratar como duplicata |
| A18 | Orbe cobrando **menos** que o contrato | **nenhum caso** (0 linhas com aplicada < contratada) | — | regra do caso ainda em aberto (§9) |

Pix contra cartão (FATO): o Pix tem taxa única por lojista (0,89; Fluente 0,79; Atlas 0,99), sem bandeira e com parcelas = 1. Nenhum Pix diverge entre os lojistas com contrato, exceto Casa (A3).

---

## 8. Chaves de ligação e de-para de lojistas

Chaves (FATO e S03):
- **Orbe → planilha: `cod_estabelecimento` = coluna "EC Orbe"** (string de 10 dígitos). 18 ECs batem direto. 3 ECs só se ligam pelo de-para da S03. Atlas não tem linha vigente. Globo Trotter (EC riscado) não aparece na Orbe.
- **Ponte → planilha: `CNPJ Cliente` sem máscara = CNPJ da planilha com `zfill(14)`.** Os 14 CNPJs da Ponte estão todos na planilha.
- **Bancos → lojista**: só por nome truncado (Aurora até 26 caracteres, Meridiano até 24). Não há CNPJ nos extratos de PIX. Serve para conferência, nunca como chave de cálculo.

| # | Lojista (planilha) | CNPJ | EC Orbe | Nome(s) na Orbe | Nome na Ponte | Aurora (PIX ENVIADO) | Meridiano (PIX RECEB) | Orbe | Ponte |
|---|---|---|---|---|---|---|---|:-:|:-:|
| 1 | Escola Bridge de Idiomas Ltda / Bridge Idiomas (NOVA) | 22224579000109 | 1075624862 | BRIDGE IDIOMAS; ESCOLA BRIDGE IDIOMAS | — | ESCOLA BRIDGE DE IDIOMAS L | — | S | N |
| 2 | Horizonte Viagens | 78576234000179 | (vazio) → 1043396662 (S03) | HORIZONTE VIAGENS TURISMO | — | HORIZONTE VIAGENS E TURISM | — | S | N |
| 3 | Kiwi Experience | 07752116000126 | (vazio) → 1038867654 (S03) | KIWI EXPERIENCE TURISMO | KIWI EXPERIENCE TURI | KIWI EXPERIENCE TURISMO LT | KIWI EXPERIENCE TURISMO | S | S |
| 4 | Rota Global Intercâmbio Ltda | 95927868000148 | 1074504011 | ROTA GLOBAL INTERCAMBIO | ROTA GLOBAL INTERCÂM | ROTA GLOBAL INTERCAMBIO LT | ROTA GLOBAL INTERCÂMBIO | S | S |
| 5 | Vela | 20987545000140 | 1086291869 | VELA TURISMO EDUCACIONAL | — | VELA TURISMO EDUCACIONAL L | — | S | N |
| 6 | Andes Expedições Ltda | 85694108000184 | 1058961395 | ANDES EXPEDICOES | — | ANDES EXPEDICÕES LTDA | — | S | N |
| 7 | Casa do Estudante Viagens Ltda | 00520815000100 | 1018325654 | CASA DO ESTUDANTE VIAG; CASA DO ESTUDANTE VIAGENS | CASA DO ESTUDANTE VI | CASA DO ESTUDANTE VIAGENS | CASA DO ESTUDANTE VIAGEN | S | S |
| 8 | Fluente Idiomas Online Ltda | 03229837000103 (planilha: 3229837000103) | 1066100982 | FLUENTE IDIOMAS ONLINE | — | FLUENTE IDIOMAS ONLINE LTD | — | S | N |
| 9 | Mundo Aberto | 17217888000111 | 1037647039 | MUNDO ABERTO INTERC LTDA; MUNDO ABERTO INTERCAMBIO; Mundo Aberto | MUNDO ABERTO INTERCÂ | MUNDO ABERTO INTERCAMBIO L (+ DEVOLUCAO PIX - MUNDO ABERTO INTERC) | MUNDO ABERTO INTERCÂMBIO | S | S |
| 10 | Ponte Aérea Estudantil Ltda (só remessa) | 95739378000118 | — | — | PONTE AÉREA ESTUDANT | — | PONTE AÉREA ESTUDANTIL L; PONTE AEREA ESTUDANTIL L (18.240) | N | S |
| 11 | EduAbroad | 16181276000153 | 1020660828 | EDU ABROAD CONSULTORIA; EDUABROAD | EDU ABROAD CONSULTOR | EDU ABROAD CONSULTORIA LTD | EDU ABROAD CONSULTORIA L | S | S |
| 12 | Dublin Hub Intercâmbio Ltda | 68567965000102 | 1014537966 | DUBLIN HUB INTERCAMBIO | DUBLIN HUB INTERCÂMB | DUBLIN HUB INTERCAMBIO LTD | DUBLIN HUB INTERCÂMBIO L | S | S |
| 13 | Maple Study Assessoria Educacional Ltda | 34671260000100 | 1041180753 | MAPLE STUDY; MAPLE STUDY ASSESSORIA | MAPLE STUDY ASSESSOR | MAPLE STUDY ASSESSORIA EDU | MAPLE STUDY ASSESSORIA E | S | S |
| 14 | Oxford Prep Cursos Ltda | 23109187000161 | 1000960410 | OXFORD PREP CURSOS | — | OXFORD PREP CURSOS LTDA | — | S | N |
| 15 | Sol Nascente Viagens Ltda | 89779285000114 | 1064304917 | SOL NASCENTE VIAGENS | — | SOL NASCENTE VIAGENS LTDA | — | S | N |
| 16 | Trilha Jovem Turismo Ltda | 21394880000106 | 1068443135 | TRILHA JOVEM TURISMO | — | TRILHA JOVEM TURISMO LTDA | — | S | N |
| 17 | Nórdica Educação Internacional Ltda (só remessa) | 14760206000124 | — | — | NÓRDICA EDUCAÇÃO INT | — | NORDICA EDUCACAO INTERNA | N | S |
| 18 | Bagagem Livre Turismo Ltda | 50900987000179 | 1087276103 | BAGAGEM LIVRE TURISMO | BAGAGEM LIVRE TURISM | BAGAGEM LIVRE TURISMO LTDA | BAGAGEM LIVRE TURISMO LT | S | S |
| 19 | Campus Global Ltda | 08780784000120 (planilha: 8780784000120) | 1070531381 | CAMPUS GLOBAL | — | CAMPUS GLOBAL LTDA | — | S | N |
| 20 | Lisboa Cursos e Viagens Ltda | 61720397000180 | 1023622151 | LISBOA CURSOS E VIAGENS; LISBOA CURSOS VIAGENS | LISBOA CURSOS E VIAG | LISBOA CURSOS E VIAGENS LT | LISBOA CURSOS E VIAGENS | S | S |
| 21 | Bem-Vindo Exchange Ltda | 67869675000142 | 1098729012 | BEM VINDO EXCHANGE; BEM-VINDO EXCHANGE | BEM-VINDO EXCHANGE L | BEM-VINDO EXCHANGE LTDA | BEM-VINDO EXCHANGE LTDA | S | S |
| 22 | Novo Horizonte Intercambio | 66564512000199 | (vazio) → 1043300981 (S03) | **HORIZONTE INTERCAMBIO** (cuidado: parece "Horizonte Viagens") | NOVO HORIZONTE INTER | NOVO HORIZONTE INTERCAMBIO | NOVO HORIZONTE INTERCÂMB | S | S |
| 23 | Canguru | 53857560000123 | 1061760196 | CANGURU INTERCAMBIO; CANGURU INTERCAMBIOS | CANGURU INTERCÂMBIOS | CANGURU INTERCAMBIOS LTDA | CANGURU INTERCÂMBIOS LTD | S | S |
| 24 | ~~Globo Trotter Viagens Ltda~~ (inativo) | 22348118000148 | 1157874034 | — | — | — | — | N | N |
| 25 | **Atlas Idiomas** (só na aba 2025) | 39566044000119 (aba 2025) | (não está na vigente) → Orbe 1076801732 | ATLAS IDIOMAS | — | ATLAS IDIOMAS LTDA | — | S | N |

Armadilhas de nome (FATO): "HORIZONTE INTERCAMBIO" (Orbe), "Horizonte Viagens" (planilha) e "Novo Horizonte" são 3 nomes parecidos para 2 empresas. Um casamento por similaridade erraria: o EC 1043300981 aplica 2,39 e 2,89, que são exclusivos do contrato da Novo Horizonte. "MUNDO ABERTO" tem 3 grafias, e "PONTE AÉREA"/"PONTE AEREA" aparecem com e sem acento no Meridiano.

---

## 9. Gabarito CHECKOUT por lojista (regras confirmadas)

> **Valores com o arquivo 06 (`06_orbe_ajustes_tardios_set2026.csv`): ver `docs/05_ajustes_tardios.md`.** A tabela abaixo é a análise original, só com o arquivo 01 (checkout 207.039,73; 1.886 linhas). Com o 06 o checkout fecha em 203.735,34 (1.900 linhas) e muda a comissão de 7 lojistas (Dublin, Maple, Mundo Aberto, Bridge, EduAbroad, Oxford, Kiwi).

Regra aplicada: `comissão_linha = round_half_up(valor_bruto × taxa contratada vigente na data da venda original, 2)`. Para VENDA e ANTECIPACAO a data é `data_movimento`; para ESTORNO, `data_venda_original`; a REVERSÃO usa a taxa da antecipação revertida (2,10). Bridge troca a vigência em 15/09. Casa do Estudante tem taxa 0 em linhas com data de referência ≥ 01/09. Atlas fica de fora. Não há empate de meio centavo no checkout, então half-up e half-even dão o mesmo resultado aqui. No remessa não é assim (§3.5).

| CNPJ | Lojista | EC | n | VENDA | ANTECIP | ESTORNO | REVERSÃO | **Comissão** | Divergência R$ (n) | valor_taxa Orbe |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 00520815000100 | Casa do Estudante Viagens Ltda | 1018325654 | 119 | 0,00 | 0,00 | −5,50 | 0,00 | **−5,50** (sem nota) | 15.397,42 (118) | 15.391,27 |
| 03229837000103 | Fluente Idiomas Online Ltda | 1066100982 | 82 | 7.480,28 | 0,00 | −164,21 | 0,00 | **7.316,07** | 0 | 7.315,70 |
| 07752116000126 | Kiwi Experience | 1038867654 | 85 | 10.250,43 | 2.431,46 | −42,04 | −1.928,44 | **10.711,41** | 0 | 10.711,06 |
| 08780784000120 | Campus Global Ltda | 1070531381 | 79 | 9.643,89 | 0,00 | −307,83 | 0,00 | **9.336,06** | 0 | 9.335,56 |
| 16181276000153 | EduAbroad | 1020660828 | 100 | 10.624,32 | 1.757,87 | −312,02 | 0,00 | **12.070,17** | 0 | 12.069,64 |
| 17217888000111 | Mundo Aberto | 1037647039 | 168 | 18.254,14 | 2.193,91 | −917,07 | −1.008,89 | **18.522,09** | 0 | 18.521,38 |
| 20987545000140 | Vela | 1086291869 | 51 | 9.315,31 | 0,00 | 0,00 | 0,00 | **9.315,31** | 0 | 9.315,05 |
| 21394880000106 | Trilha Jovem Turismo Ltda | 1068443135 | 67 | 5.838,42 | 0,00 | −209,85 | 0,00 | **5.628,57** | 0 | 5.628,23 |
| 22224579000109 | Escola Bridge de Idiomas Ltda | 1075624862 | 107 | 12.063,04 | 0,00 | −147,02 | 0,00 | **11.916,02** | 29,95 (5) | 11.945,46 |
| 23109187000161 | Oxford Prep Cursos Ltda | 1000960410 | 98 | 9.987,22 | 7.388,36 | −457,23 | −840,45 | **16.077,90** | 0 | 16.077,42 |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | 1041180753 | 105 | 12.631,04 | 2.534,54 | −154,80 | 0,00 | **15.010,78** | 0 | 15.010,25 |
| 50900987000179 | Bagagem Livre Turismo Ltda | 1087276103 | 74 | 9.004,37 | 0,00 | −1.300,39 | 0,00 | **7.703,98** | 0 | 7.703,68 |
| 53857560000123 | Canguru | 1061760196 | 80 | 9.000,91 | 2.761,65 | −83,13 | 0,00 | **11.679,43** | 0 | 11.679,08 |
| 61720397000180 | Lisboa Cursos e Viagens Ltda | 1023622151 | 76 | 8.979,42 | 0,00 | −508,64 | 0,00 | **8.470,78** | 0 | 8.470,45 |
| 66564512000199 | Novo Horizonte Intercambio | 1043300981 | 73 | 8.158,61 | 0,00 | −390,83 | 0,00 | **7.767,78** | 0 | 7.767,49 |
| 67869675000142 | Bem-Vindo Exchange Ltda | 1098729012 | 76 | 9.259,74 | 0,00 | 0,00 | 0,00 | **9.259,74** | 0 | 9.259,37 |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | 1014537966 | 111 | 9.590,14 | 2.515,81 | −199,87 | 0,00 | **11.906,08** | 0 | 11.905,52 |
| 78576234000179 | Horizonte Viagens | 1043396662 | 75 | 9.255,18 | 0,00 | −240,76 | 0,00 | **9.014,42** | 0 | 9.014,07 |
| 85694108000184 | Andes Expedições Ltda | 1058961395 | 41 | 3.941,76 | 0,00 | −122,41 | 0,00 | **3.819,35** | 0 | 3.819,13 |
| 89779285000114 | Sol Nascente Viagens Ltda | 1064304917 | 60 | 6.015,58 | 0,00 | −117,56 | 0,00 | **5.898,02** | 0 | 5.897,67 |
| 95927868000148 | Rota Global Intercâmbio Ltda | 1074504011 | 159 | 15.797,71 | 1.125,65 | −1.302,09 | 0,00 | **15.621,27** | 1.546,28 (87) | 17.166,83 |
| **Total (21 lojistas)** | | | **1.886** | **195.091,51** | **22.709,25** | **−6.983,25** | **−3.777,78** | **207.039,73** | **16.973,65 (210)** | **224.004,31** |
| Atlas Idiomas (fora) | 39566044000119 (aba 2025) | 1076801732 | 57 | — | — | — | — | não faturar | — | 7.876,05 |

Conferências:
- Notas CHECKOUT: 20 lojistas com saldo > 0, somando **R$ 207.045,23**. Casa (−5,50) não emite nota e vira pendência (S04).
- A soma do `valor_taxa` Orbe nas 1.886 linhas faturáveis é 224.004,31. A diferença para a comissão (16.964,58) se explica assim: 16.973,65 de divergências, menos 7,99 de efeito do truncamento nas linhas sem divergência, menos 1,08 de efeito do truncamento dentro das próprias linhas divergentes. Fecha ao centavo.
- O estorno de agosto da Casa (TX88445133, venda de 21/08, débito 1,49%) abate −5,50 porque em agosto o contrato não era zero. É isso que deixa a Casa negativa. Ver dúvida D1.

---

## 10. Regras evidentes nos dados (com evidência e confirmação)

| ID | Regra | Evidência (FATO) | Confirmação |
|---|---|---|---|
| E01 | Chave Orbe→contrato = EC Orbe; nome não serve | 22 ECs com 31 grafias; nenhum EC muda de nome-base | S03 |
| E02 | Faixas: débito, vista, parcelado 2-6x e 7-12x por `qtd_parcelas`, Pix, antecipação | Taxas aplicadas batem com essa leitura em 100% dos lojistas sem divergência | S01 |
| E03 | Orbe trunca o valor_taxa; Tarvo usa half-up linha a linha | 1.943 de 1.943 consistentes com truncamento | S11 |
| E04 | Estorno é total e herda a taxa da venda original | 50 de 50 estornos com referência: valor, taxa, modalidade e parcelas iguais | S02 |
| E05 | Estorno de venda de agosto abate setembro, com a taxa de agosto | 9 estornos com data_venda_original em 08/2026 | S02, S17 |
| E06 | Reversão anula a taxa da antecipação revertida | 6 de 6 reversões com valor total da AN referenciada, taxa 2,10 | S04 |
| E07 | Vigência por data da venda (Bridge 15/09) | A Orbe passou a 2,19% em 23/09; entre 15 e 18/09 cobrou 2,59% | planilha L6/L7 + S02 (data da venda original) |
| E08 | Rota +0,5 p.p. desde 12/09 = divergência | 0 divergências até 11/09; 83 vendas divergentes de 12/09 em diante | S06 |
| E09 | Casa do Estudante: taxa 0 de set a dez | A Orbe cobrou a taxa cheia em 117 linhas | S07 |
| E10 | Atlas sem contrato: não fatura | EC fora da aba vigente; CNPJ só na aba 2025 | S03 |
| E11 | Chave Ponte→contrato = CNPJ (14 díg.) | 14 de 14 CNPJs batem com a planilha | S05 |
| E12 | Spread em branco ou "padrão" = 1,5% | Kiwi, Canguru e Ponte Aérea aparecem a 1,50% na Ponte | S05, nota A32 |
| E13 | Spread % é sobre PTAX × ME | 233 de 233 = (TC − PTAX)/PTAX | S05 |
| E14 | Nº de operação único; repetida conta uma vez | PC-0926-0162 paga uma vez só no banco (§6.3) | S05 |
| E15 | Spread negativo fica fora | 4 operações "Taxa travada no pedido (D-1)" | S05 |
| E16 | Competência da remessa = data de contratação | 6 operações de 30/09 liquidam em 01/10 | S05 |
| E17 | Status "C/ RESSALVA" é irrelevante | e-mail da Ponte | S05 |
| E18 | Remessa: 1 nota para a Ponte, 50% por operação com half-up | e-mail ("50%... mediante nota fiscal") | S04, S11 |
| E19 | Contrapartida bancária: baixa passivos de agosto e despesa direta no resto | descrições "08/2026" no Aurora | S08, S12 |
| E20 | O lojista adianta o valor da remessa (Valor R$ + IOF) toda semana; a Tarvo paga a Ponte em D0 | 70 de 70 semanas e 21 de 21 TEDs batem | INTERP. forte (só valor) |

---

## 11. Dúvidas de negócio ainda em aberto

O que já está respondido em S01 a S17 não é repetido. Cada dúvida traz a premissa sugerida e o impacto de cada resposta.

| # | Pergunta fechada | Premissa sugerida | Impacto em R$ |
|---|---|---|---|
| D1 | O estorno de venda de **agosto** da Casa do Estudante (TX88445133, −369,39, débito, venda de 21/08) abate setembro à taxa de agosto (1,49%, −5,50), mesmo que a Casa fique com comissão negativa e sem nota? Ou a taxa zero vale também para estornos de vendas anteriores a setembro? | Abater −5,50 (S02 diz "inclusive vendas de agosto"). A Casa fica em −5,50: sem nota e pendência para Helena (S04) | A: Casa −5,50, sem nota. B: Casa 0,00, sem nota. Total CHECKOUT 207.039,73 (A) ou 207.045,23 (B). As notas a emitir somam 207.045,23 nos dois casos |
| D2 | Estornos de vendas que foram cobradas acima do contrato (Rota: TX88446419, TX88446585, TX88446596, TX88446647; Casa: TX88446763) devem aparecer em `divergencias_taxa.csv` com sinal negativo? Ou a venda e o estorno se anulam e nenhum dos dois é listado? | Listar as duas linhas, com sinal, para o total por lojista fechar | Rota: 1.644,72 (só vendas) contra 1.546,28 (líquido). Casa: 15.406,51 contra 15.397,42. Total: 17.081,18 contra 16.973,65 |
| D3 | A divergência da Casa do Estudante (Orbe cobrou e o contrato é 0%) vai para `divergencias_taxa.csv` com taxa_contratada = 0,00? Ou é tratada só como "devolução ao lojista" em pendências? | Divergência com contratada = 0 e a mesma pendência para Helena | Pode mudar o total do arquivo de divergências em 15.397,42 |
| D4 | Se a Orbe cobrar **menos** que o contrato, isso é divergência (a Tarvo cobra a diferença do lojista ou da Orbe) ou só uma nota informativa? | Divergência com valor negativo e pendência para Helena. A comissão continua pela taxa contratada (S01) | Hoje: **0 casos** em setembro. Regra para outubro |
| D5 | Vigência na planilha: vale `data_movimento` (venda) ou a data de captura? E um texto de vigência fora do padrão ("até", "a partir de", vazio) deve travar o processo ou cair na linha mais recente? | Data da venda; vigência não reconhecida trava e vira pendência | Hoje só afeta a Bridge: 29,95 |
| D6 | O PIX de **R$ 18.240,00 "PONTE AEREA ESTUDANTIL L"** (MRD2026090425, 17/09, grafia sem acento, valor redondo) não corresponde a nenhuma operação Ponte. É adiantamento de remessa futura (2.1.02.001), depósito errado (1.1.09.002) ou pagamento de outra coisa? | 2.1.02.001 + pendência (veio do lojista para a conta de remessas). Se não for identificado: 1.1.09.002 | Só classificação, sem efeito em comissão: 18.240,00 |
| D7 | Tolerância de spread na remessa (S10 deixou para nós): podemos usar \|Δ\| < 0,01 p.p. (ou R$ 1,00 por operação) como arredondamento? | Sim. Fora de Mundo Aberto, o maior desvio é 0,0016 p.p. / R$ 0,74; em Mundo Aberto o menor é 0,299 p.p. | Com a tolerância: 23 divergências e 1.418,85. Sem tolerância (Δ ≠ 0): +205 alarmes de centavo, somando 1,52 |
| D8 | Divergência de remessa: usar Spread % do relatório (6 casas) × PTAX × ME, ou Spread R$ − contratado × PTAX × ME? | Fórmula do gestor (Spread %) | 1.418,85 contra 1.418,88 (R$ 0,03) |
| D9 | Duplicata PC-0926-0162: no `pendencias.csv`, o valor é o spread (821,88), os 50% (410,94) ou o valor da operação (55.600,19)? | Spread R$ 821,88 (é o que inflaria a base da nota) | Sem efeito na comissão |
| D10 | Spread negativo: a pendência leva o valor negativo realizado (−1.834,05) ou o spread que deveria ter sido cobrado (estimado D-1 = 1.622,90; ou contratado 1,5% sobre PTAX × ME)? | Valor realizado −1.834,05 por operação, com o estimado D-1 informado | Não muda a comissão (estão fora). Muda só o valor exibido |
| D11 | Atlas Idiomas: as 4 antecipações de 15/09 (179.592,82) superam as vendas acumuladas da Atlas até essa data (55.357,50), e 2 foram revertidas. Isso é sinal de risco/compliance a reportar, além do "sem contrato"? | Pendência para o comercial e o risco, sem faturar | Bruto Atlas 262.138,61; valor_taxa Orbe 7.876,05 |
| D12 | A comissão de antecipação deve ir separada na nota (3.1.02) ou tudo como "intermediação/MDR"? S04 diz mesma nota; a dúvida é a discriminação | Mesma nota, com o valor de MDR e o de antecipação descritos no texto | MDR 188.108,26 (VENDA + ESTORNO) e antecipação líquida 18.931,47 (ANTECIP + REVERSÃO), sem Casa e Atlas |
| D13 | Devolução PIX Mundo Aberto (L65, 12.400,00): a proposta é 2.1.01.001. A Tarvo tem que repagar o lojista em outubro? | 2.1.01.001 + pendência | 12.400,00 (classificação) |
| D14 | Baixas de agosto no Aurora (folha 184.732,18; ISS 21.877,40; INSS 51.320,66; FGTS 14.778,57; IRRF 22.104,35; PIS 9.811,20; COFINS 45.282,46) contra os passivos 2.1.04.x / 2.1.03.x: confirmar que nenhum tem juros ou multa a separar em 4.3.02 | Sem juros (os valores estão em centavos "cheios", sem indício de acréscimo) | — |

Top 10 para levar ao Slack: D6, D2, D3, D1, D7, D4, D11, D5, D12, D10.

---

## 12. Riscos para o dev (checklist de leitura)
1. Planilha: CNPJ numérico sem zero (zfill), taxas texto "1,49%", spread "padrão", Bridge com 2 linhas, linha 30 riscada (ignorar pelo atributo strike, não pela posição), mesclado D4:I4 (usar o cabeçalho da linha 5).
2. Ponte: header na linha 5, rodapé "Total"/"Spread total" (filtrar `PC-`), CNPJ com e sem máscara, nome truncado, duplicata.
3. Aurora: UTF-8 com LF; `ref_origem` = número físico da linha (o 1º lançamento é L9); milhar `.`; linhas finais sem data.
4. OFX: SGML cp1252 sem tags de fechamento; sem saldo inicial.
5. Arredondamento: `Decimal` + `ROUND_HALF_UP`. `round()` do Python erra 0,60 no total da remessa.
6. Orbe: não usar bandeira para ligar estorno e venda; usar `id_referencia`.
