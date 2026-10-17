# 05 — Ajustes tardios da Orbe (arquivo 06) — análise para o fechamento de set/2026

Arquivo: `06_orbe_ajustes_tardios_set2026.csv` (14 linhas, mesmo layout do 01, todas com `data_movimento` 30/09/2026). Análise feita sem alterar `src/`, `app/`, `tests/`, `saida/` nem os dados. Recalculado em Decimal, half-up por linha (R01), contra o arquivo 01, a planilha 02 (aba vigente) e as saídas atuais. Regras citadas: R01, R10–R13, R15, R31, R51, R54, CC04, CC07, S01–S39.

## 1. Resumo

- **Nenhuma duplicata e nenhuma inconsistência de valor, lojista ou data.** Os 14 `id_transacao` são novos (nenhum existe no 01; os 14 são únicos entre si e estão acima do maior id do 01, TX88446959 e AN88446832, como se fossem a continuação do relatório).
- 10 estornos totais de vendas de setembro, 3 reversões totais de antecipação e 1 venda nova. Todas as originais existem no 01, com mesmo EC, valor bruto e data. Nenhuma original tinha estorno ou reversão no 01 (**sem estorno em duplicidade**). Nenhum estorno é parcial.
- **Nenhuma linha tem taxa aplicada diferente da contratada.** Logo, as divergências ficam como estão (R$ 16.973,65 em 210 transações). Nenhuma das 10 vendas estornadas estava em `divergencias_taxa.csv`, então R51 não é acionada.
- **Efeito: checkout cai R$ 3.304,39** (207.039,73 → **203.735,34**). Notas continuam 20 (nenhuma fica ≤ 0), soma 207.045,23 → **203.740,84**. Quase tudo vem da Oxford (−2.232,19) e da Maple (−845,01), por causa das reversões de antecipação.
- Pendências: nenhuma nova é obrigatória pelas regras. Há uma conferência sugerida (venda nova da Kiwi, item 4) e uma pergunta de processo (item 6).

## 2. Tabela linha a linha

Legenda das colunas de checagem: **Dup01** = id já existe no 01; **Orig** = id_referencia achado no 01 (ou no 06); **Valor/EC/Data** = bruto (em módulo), EC e `data_venda_original` batem com a original; **Já estornada?** = a original já tinha estorno/reversão no 01 ou no 06; **Tipo** = total ou parcial.

| # | id | Tipo | Lojista (EC) | Bruto | Dup01 | Orig (no 01) | Valor / EC / Data | Já estornada? | Tipo estorno |
|--:|---|---|---|--:|:-:|---|:-:|:-:|:-:|
| 1 | TX88446992 | ESTORNO | Dublin Hub (1014537966) | −1.147,05 | não | TX88431689 (18/09, à vista VISA) | sim / sim / sim | não | total |
| 2 | TX88447011 | ESTORNO | Maple Study (1041180753) | −420,77 | não | TX88413573 (03/09, débito) | sim / sim / sim | não | total |
| 3 | TX88447030 | ESTORNO | Mundo Aberto (1037647039) | −562,44 | não | TX88438558 (25/09, à vista) | sim / sim / sim | não | total |
| 4 | TX88447044 | ESTORNO | Bridge (1075624862) | −1.982,10 | não | TX88425142 (13/09, 2x) | sim / sim / sim | não | total |
| 5 | TX88447057 | ESTORNO | EduAbroad (1020660828) | −3.898,29 | não | TX88430977 (18/09, 2x) | sim / sim / sim | não | total |
| 6 | TX88447070 | ESTORNO | Bridge (1075624862) | −2.603,31 | não | TX88424537 (12/09, 6x) | sim / sim / sim | não | total |
| 7 | TX88447087 | ESTORNO | Oxford Prep (1000960410) | −8.647,36 | não | TX88422829 (11/09, 9x) | sim / sim / sim | não | total |
| 8 | TX88447093 | ESTORNO | Maple Study (1041180753) | −2.620,34 | não | TX88416714 (06/09, à vista) | sim / sim / sim | não | total |
| 9 | TX88447109 | ESTORNO | EduAbroad (1020660828) | −2.747,67 | não | TX88428997 (16/09, 3x) | sim / sim / sim | não | total |
| 10 | TX88447140 | ESTORNO | Oxford Prep (1000960410) | −2.366,18 | não | TX88432148 (19/09, à vista) | sim / sim / sim | não | total |
| 11 | AN88447152 | REVERSÃO ANT. | Oxford Prep (1000960410) | −46.080,41 | não | AN88446397 (22/09, antecipação) | sim / sim / sim | não | total |
| 12 | AN88447178 | REVERSÃO ANT. | Oxford Prep (1000960410) | −41.690,09 | não | AN88446748 (29/09, antecipação) | sim / sim / sim | não | total |
| 13 | AN88447194 | REVERSÃO ANT. | Maple Study (1041180753) | −36.583,37 | não | AN88446551 (24/09, antecipação) | sim / sim / sim | não | total |
| 14 | TX88447225 | VENDA | Kiwi Experience (1038867654) | 5.480,00 | não | — (venda, sem referência) | — | — | — |

Soma do bruto do 06: −145.869,38 (estornos −26.995,51; reversões −124.353,87; venda +5.480,00). Soma do `valor_taxa` Orbe: −3.304,32.

### 2.1 Taxa, comissão, lojista

Taxa contratada vigente na data da venda original (aba vigente, planilha 02) × taxa aplicada pela Orbe. A comissão é bruto × contratada, half-up por linha (R10/R12); a reversão usa 2,10%, a taxa da antecipação revertida (R12).

| # | id | Faixa na data da original | Contratada % | Aplicada % | Diverge? | Comissão da linha (R$) | `valor_taxa` Orbe (trunca) | Lojista mapeado / bloqueado? |
|--:|---|---|--:|--:|:-:|--:|--:|---|
| 1 | TX88446992 | à vista | 2,59 | 2,59 | não | −29,71 | −29,70 | Dublin Hub Intercâmbio, CNPJ 68567965000102 / não |
| 2 | TX88447011 | débito | 1,49 | 1,49 | não | −6,27 | −6,26 | Maple Study, 34671260000100 / não |
| 3 | TX88447030 | à vista | 2,49 | 2,49 | não | −14,00 | −14,00 | Mundo Aberto, 17217888000111 / não |
| 4 | TX88447044 | 2–6x | 3,19 | 3,19 | não | −63,23 | −63,22 | Escola Bridge, 22224579000109 / não |
| 5 | TX88447057 | 2–6x | 3,19 | 3,19 | não | −124,36 | −124,35 | EduAbroad, 16181276000153 / não |
| 6 | TX88447070 | 2–6x | 3,19 | 3,19 | não | −83,05 | −83,04 | Escola Bridge / não |
| 7 | TX88447087 | 7–12x | 3,79 | 3,79 | não | −327,73 | −327,73 | Oxford Prep, 23109187000161 / não |
| 8 | TX88447093 | à vista | 2,69 | 2,69 | não | −70,49 | −70,48 | Maple Study / não |
| 9 | TX88447109 | 2–6x | 3,19 | 3,19 | não | −87,65 | −87,65 | EduAbroad / não |
| 10 | TX88447140 | à vista | 2,59 | 2,59 | não | −61,28 | −61,28 | Oxford Prep / não |
| 11 | AN88447152 | antecipação | 2,10 | 2,10 | não | −967,69 | −967,68 | Oxford Prep / não |
| 12 | AN88447178 | antecipação | 2,10 | 2,10 | não | −875,49 | −875,49 | Oxford Prep / não |
| 13 | AN88447194 | antecipação | 2,10 | 2,10 | não | −768,25 | −768,25 | Maple Study / não |
| 14 | TX88447225 | 2–6x (3x) | 3,19 | 3,19 | não | +174,81 | +174,81 | Kiwi Experience, 07752116000126 (via de-para CC04/S03) / não |
| | | | | | | **−3.304,39** | −3.304,32 | |

Observações:
- Os centavos de diferença contra a Orbe são truncamento (R02/S11), não divergência. Todas as 14 linhas conferem com truncamento, e `valor_liquido` = bruto − taxa em todas.
- Bridge: as duas vendas originais são de 12 e 13/09, crédito **parcelado**. A troca de 15/09 (CC07) só mexe no crédito à vista, então não interfere. Nenhuma linha do 06 cai na faixa "à vista de 15 a 18/09" da OC02.
- Casa do Estudante (isenção CC01) e Atlas (bloqueada, CC05) **não aparecem** no 06. Nenhum EC do arquivo é bloqueado. O de-para de EC só é necessário para a Kiwi (1038867654).
- As reversões anulam exatamente a comissão das antecipações que revertem (R12): AN88446397 → 967,69; AN88446748 → 875,49; AN88446551 → 768,25, iguais ao que está hoje em `rastro.csv`.

### 2.2 Anomalias (item 6 do pedido)

| Verificação | Resultado |
|---|---|
| Duplicata de id entre 06 e 01 | nenhuma |
| Estorno em duplicidade (original já estornada, no 01 ou no 06) | nenhum |
| Reversão cuja antecipação não existe | nenhuma; as 3 antecipações existem no 01 e eram válidas |
| Data fora de setembro | nenhuma (todas 30/09; datas das originais entre 03 e 29/09) |
| `data_venda_original` diferente da data da original | nenhuma |
| Estorno parcial | nenhum |
| Taxa aplicada sem correspondência na planilha | nenhuma |
| Venda nova com valor redondo (5.480,00) é duplicata de venda do 01? | **Não.** Não existe nenhum 5.480,00 no 01. Valores inteiros são comuns no 01 (26 vendas), e a Kiwi tem outros (3.651,00; 28.000,00; 616,00). Não há venda da Kiwi 3x com valor igual. |
| Antecipação acima das vendas (R54) depois do 06 | **não dispara.** Antecipado líquido × vendas líquidas: Oxford 224,0 mil × 289,1 mil; Maple 84,1 mil × 372,5 mil; Kiwi 24,0 mil × 310,0 mil |
| `bandeira` do estorno diferente da original | ocorre em 7 de 10 estornos do 06 (ex.: TX88447011 VISA × original AMEX). **É padrão do relatório:** no próprio 01, 39 de 56 estornos têm bandeira diferente da original. Não afeta taxa nem comissão; não tratar como anomalia. |

Único ponto que o dado sozinho não resolve: **a venda TX88447225 chegou num arquivo de "ajustes"** (id TX88447225, EC da Kiwi, 3x, R$ 5.480,00, taxa correta). Não há como provar nos arquivos que é uma venda legítima que ficou fora do relatório e não um lançamento indevido. Ver pergunta P1.

## 3. Impacto por lojista

Só os 7 lojistas abaixo mudam; os outros 14 e a Atlas ficam iguais. Valores em R$.

| Lojista | Linhas no 06 | Comissão antes | MDR (venda − estorno) | Antecipação (− reversão) | Comissão depois | Δ | Linhas Orbe antes → depois |
|---|---|--:|--:|--:|--:|--:|--:|
| Dublin Hub Intercâmbio Ltda | 1 | 11.906,08 | −29,71 | 0,00 | 11.876,37 | −29,71 | 111 → 112 |
| Maple Study Assessoria Educacional Ltda | 3 | 15.010,78 | −76,76 | −768,25 | 14.165,77 | −845,01 | 105 → 108 |
| Mundo Aberto | 1 | 18.522,09 | −14,00 | 0,00 | 18.508,09 | −14,00 | 168 → 169 |
| Escola Bridge de Idiomas Ltda | 2 | 11.916,02 | −146,28 | 0,00 | 11.769,74 | −146,28 | 107 → 109 |
| EduAbroad | 2 | 12.070,17 | −212,01 | 0,00 | 11.858,16 | −212,01 | 100 → 102 |
| Oxford Prep Cursos Ltda | 4 | 16.077,90 | −389,01 | −1.843,18 | 13.845,71 | −2.232,19 | 98 → 102 |
| Kiwi Experience | 1 | 10.711,41 | +174,81 | 0,00 | 10.886,22 | +174,81 | 85 → 86 |
| **Total** | **14** | | | | | **−3.304,39** | |

Detalhe do MDR/antecipação depois (para o auditor): Dublin MDR 9.360,56 / antec. 2.515,81; Maple 12.399,48 / 1.766,29; Mundo Aberto 17.323,07 / 1.185,02; Bridge 11.769,74 / 0,00; EduAbroad 10.100,29 / 1.757,87; Oxford 9.140,98 / 4.704,73; Kiwi 10.383,20 / 503,02.

## 4. Totais: antes → depois (gabarito)

| Item | Antes | Depois | Δ |
|---|--:|--:|--:|
| Comissão checkout (21 lojistas) | 207.039,73 | **203.735,34** | −3.304,39 |
| &nbsp;&nbsp;MDR (vendas − estornos) | 188.108,26 | 187.415,30 | −692,96 |
| &nbsp;&nbsp;Antecipação (− reversões) | 18.931,47 | 16.320,04 | −2.611,43 |
| Por tipo: VENDA | 195.091,51 | 195.266,32 | +174,81 |
| Por tipo: ESTORNO | −6.983,25 | −7.851,02 | −867,77 |
| Por tipo: ANTECIPAÇÃO | 22.709,25 | 22.709,25 | 0,00 |
| Por tipo: REVERSÃO | −3.777,78 | −6.389,21 | −2.611,43 |
| Notas de checkout (nº) | 20 | 20 | 0 |
| Notas de checkout (soma) | 207.045,23 | **203.740,84** | −3.304,39 |
| Casa do Estudante (sem nota, PEN-0004) | −5,50 | −5,50 | 0 |
| Divergência de taxa checkout | 16.973,65 (210) | **16.973,65 (210)** | 0,00 |
| Linhas Orbe faturáveis (21 lojistas) | 1.886 | 1.900 | +14 |
| Atlas (fora, 57 linhas, valor_taxa Orbe 7.876,05) | igual | igual | 0 |

Conferência cruzada: 203.740,84 (notas) − 5,50 (Casa) = 203.735,34 (comissão). A soma das comissões das 14 linhas (−3.304,39) difere em 0,07 do `valor_taxa` Orbe (−3.304,32) por truncamento da Orbe.

Quebra por lojista das notas (R30), valores novos: Fluente 7.316,07; Kiwi 10.886,22; Campus 9.336,06; EduAbroad 11.858,16; Mundo Aberto 18.508,09; Vela 9.315,31; Trilha 5.628,57; Bridge 11.769,74; Oxford 13.845,71; Maple 14.165,77; Bagagem 7.703,98; Canguru 11.679,43; Lisboa 8.470,78; Novo Horizonte 7.767,78; Bem-Vindo 9.259,74; Dublin 11.876,37; Horizonte Viagens 9.014,42; Andes 3.819,35; Sol Nascente 5.898,02; Rota Global 15.621,27.

### 4.1 Efeito nas demais saídas

- **Notas (R31):** nenhuma fica ≤ 0. Continuam 20 notas; muda o valor e a discriminação de 7 (MDR, antecipação e nº de transações). `qtd_linhas_origem` sobe nas mesmas 7 notas (+14 no total).
- **Divergências:** sem mudança. Nenhuma linha nova com taxa aplicada ≠ contratada e nenhuma venda divergente estornada.
- **Pendências:** PEN-0002 (Bridge R$ 29,95), PEN-0003 (Rota R$ 1.546,28), PEN-0004 (Casa −5,50), PEN-0005/0006 (Atlas) ficam com o mesmo valor. As pendências com texto de contagem não mudam. Pendência nova **não é exigida pelas regras**. Opcional: uma de conferência para a Kiwi (TX88447225), ver P1.
- **`rastro.csv`:** +14 linhas (arquivo de origem = 06) por saída/nota afetada; as reversões continuam apontando para a antecipação do 01 que anulam.
- **Extratos/ERP:** nenhuma mudança na classificação (R43: créditos Orbe só classificados). Efeito de caixa a observar pela Helena, fora do fechamento: o líquido do 06 é −142.565,06 (estornos −26.995,51 bruto; reversões −124.353,87 bruto; venda +5.480,00 bruto).
- **Testes e documentos que citam totais** (para o dev): valores como 207.039,73, 207.045,23, contagem de 1.886 linhas, 1.943 linhas do 01 e comissão por lojista de Dublin, Maple, Mundo Aberto, Bridge, EduAbroad, Oxford e Kiwi, em `tests/test_gabarito.py`, `PITCH.md`, `docs/01_entendimento_dados.md` §9.

## 5. Perguntas abertas ao financeiro (Helena)

Redigidas como perguntas sobre a regra, sem premissa embutida. Premissa sugerida e impacto ficam ao lado, para a nossa decisão.

### P1 — prioridade alta
**Pergunta:** Quando a Orbe manda, num arquivo de ajustes separado do relatório mensal, uma linha de VENDA (e não só estorno ou reversão), qual é a regra para ela entrar no fechamento do mês e o que a Tarvo confere antes de faturar a taxa? Exemplo: a TX88447225, de 30/09/2026, Kiwi Experience, crédito parcelado em 3x, R$ 5.480,00, que não aparece no relatório principal.

- **Premissa sugerida:** competência pela `data_movimento` (R03), então entra em setembro. Fatura como qualquer venda, pela taxa contratada, com marca no rastro de que veio do arquivo 06.
- **Impacto de cada alternativa:**
  - A. Entra em setembro (premissa): Kiwi 10.886,22 (+174,81); total checkout 203.735,34; notas 203.740,84.
  - B. Fica fora até a Orbe confirmar que a venda é legítima, com pendência: Kiwi 10.711,41; total checkout 203.560,53; notas 203.566,03. Os R$ 174,81 vão para a nota de outubro se confirmada (padrão R55).
  - C. Entra só em outubro, pela data de chegada do arquivo: mesmo número de B em setembro, sem pendência.
- Observação: o total dos estornos e reversões do 06 não depende desta resposta.

### P2 — prioridade média (não bloqueia hoje)
**Pergunta:** Quando a Orbe mandar estornos ou reversões de antecipação de um mês já fechado, depois de a nota do lojista ter sido emitida, em que mês e de que forma o ajuste entra? Exemplo: se as reversões AN88447152 e AN88447178 (Oxford, R$ 967,69 e R$ 875,49 de comissão) tivessem chegado depois da nota NF-0009 de setembro.

- **Premissa sugerida:** R03 e S02 ("mês fechado não reabre"): o ajuste entra no mês da chegada, abatendo a nota seguinte, com rastro até o `data_movimento` original. Hoje não se aplica, porque o 06 chegou antes das 18h30 e entra na nota de setembro.
- **Impacto:**
  - A. Abate em outubro (premissa): nota de setembro de Oxford sairia 16.077,90 e a de outubro nasce reduzida em 1.843,18.
  - B. Nota de setembro substituída/corrigida: Oxford 13.845,71 em setembro; o outubro não sofre abatimento.
- Impacto hoje em R$: zero.

## 6. Itens para conferir fora da Helena

- **Bia (Orbe):** confirmar se TX88447225 (Kiwi) é venda que ficou fora do relatório principal; é a resposta que transforma a alternativa B em A.
- **Qualquer volume futuro:** vale checar, antes de ler o 06, que o arquivo é de ajustes de setembro e não é uma cópia parcial do 01 (aqui verificado: nenhum id repetido).

## 7. Gabarito resumido para dev e auditor

- 14 linhas, 14 ids novos, 0 duplicatas, 0 divergências novas, 0 pendências obrigatórias novas.
- Comissão checkout: 207.039,73 → **203.735,34**; MDR 187.415,30; antecipação 16.320,04.
- Notas de checkout: 20, soma 203.740,84. Casa −5,50 sem nota.
- Divergência de taxa checkout: 16.973,65 (210), inalterada.
- Linhas por lojista que mudam: Dublin 11.876,37; Maple 14.165,77; Mundo Aberto 18.508,09; Bridge 11.769,74; EduAbroad 11.858,16; Oxford 13.845,71; Kiwi 10.886,22.
- Se a Helena decidir pela alternativa B de P1: tirar a linha TX88447225; checkout 203.560,53; notas 203.566,03; Kiwi 10.711,41.
