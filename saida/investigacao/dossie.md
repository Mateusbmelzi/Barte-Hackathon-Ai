# Dossiê de investigação das divergências — competência 09/2026

Gerado pelo fechamento, de forma determinística: só **fatos** calculados dos arquivos do mês, com a transação ou operação de origem. Não há hipótese de causa aqui; quem decide é a analista.

| Grupo | Parceiro | Lojista | Natureza | Qtd | Divergência | Devolver ao lojista | Recuperar do parceiro |
|---|---|---|---|---:|---:|---:|---:|
| G01 | Orbe | Casa do Estudante Viagens Ltda | concessão comercial fora do contrato (devolução do bolso da Tarvo) | 118 | R$ 15.397,42 | R$ 15.396,77 | R$ 0,00 |
| G02 | Orbe | Rota Global Intercâmbio Ltda | divergência de contrato | 87 | R$ 1.546,28 | R$ 1.545,86 | R$ 1.545,86 |
| G03 | Ponte | Mundo Aberto | divergência de contrato | 23 | R$ 1.418,85 | R$ 1.418,88 | R$ 1.418,88 |
| G04 | Orbe | Escola Bridge de Idiomas Ltda | divergência de contrato | 5 | R$ 29,95 | R$ 29,94 | R$ 29,94 |

## G01 — Casa do Estudante Viagens Ltda (Orbe, checkout, concessão comercial fora do contrato (devolução do bolso da Tarvo))

- CNPJ 00520815000100 · EC 1018325654
- Divergência: R$ 15.397,42 em 118 transações
- Devolver ao lojista: R$ 15.396,77 · Recuperar do parceiro: R$ 0,00

### O que aconteceu

Desde 01/09 a Orbe cobra a taxa cheia em todas as faixas; o lojista tem isenção comercial (C001).

### Ação pela regra

Devolver ao lojista R$ 15.396,77 (sai do caixa da Tarvo — concessão comercial fora do contrato); não cobrar a Orbe. _(regras: R52, R68, R74)_

### Linha do tempo

| ID | Faixa | De | Até | Taxa aplicada | Taxa contratada | Qtd | Diverge |
|---|---|---|---|---:|---:|---:|---|
| V1 | débito | 21/08/2026 | 21/08/2026 | 1,49% | 1,49% | 1 | não |
| V2 | débito | 08/09/2026 | 30/09/2026 | 1,49% | 0% | 12 | sim |
| V3 | crédito à vista | 01/09/2026 | 29/09/2026 | 2,69% | 0% | 35 | sim |
| V4 | 2–6x | 01/09/2026 | 30/09/2026 | 3,19% | 0% | 41 | sim |
| V5 | 7–12x | 01/09/2026 | 26/09/2026 | 3,79% | 0% | 17 | sim |
| V6 | Pix | 06/09/2026 | 29/09/2026 | 0,89% | 0% | 9 | sim |
| V7 | antecipação | 09/09/2026 | 16/09/2026 | 2,10% | 0% | 4 | sim |

### Condições do cliente

- **P13** (planilha linha 13) desde 01/01/2026: débito 1,49%; crédito à vista 2,69%; 2–6x 3,19%; 7–12x 3,79%; Pix 0,89%; antecipação 2,10% (obs: 'cliente estratégico - ver c/ comercial')
- **C001** (cadastro) isenção (todas as faixas) de 01/09/2026 a 31/12/2026, aprovada por Comercial, fonte S07/S47

### Regras aplicáveis

- **R52** Concessão comercial fora do contrato (ex.: isenção que o Comercial deu e ninguém comunicou) não é divergência de contrato: não se cobra o parceiro e a devolução ao lojista sai do bolso da Tarvo; fica separada, em uma pendência para Helena e Comercial.
- **R68** Quem deve é decidido pelo contrato, não pelo aviso: aditivo ou condição negociada e registrada é divergência de contrato (a Helena contesta o parceiro e o lojista é ressarcido); aviso atrasado é problema de processo. Concessão do Comercial fora do contrato: o parceiro cobrou o contratado e a devolução sai do bolso da Tarvo.
- **R13** Divergência de checkout = transação com taxa aplicada diferente da contratada; valor = valor bruto × (taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso.
- **R60** Toda divergência de taxa é dinheiro a devolver ao lojista; quando é de contrato, também a recuperar do parceiro.
- **R74** Valor a devolver ao lojista = o que o parceiro descontou de fato (valor_taxa; na remessa, o Spread R$) menos a comissão contratada. A lista de divergências segue a fórmula; a diferença entre as duas é truncamento da Orbe.
- **R72** Isenção ou taxa zero com vigência vale para venda a partir da data de início; para antecipação vale a data da antecipação; estorno segue a taxa da venda.

### Fatos detalhados

- **F1** 118 transações divergentes, líquido R$ 15.397,42 (inclui 1 estorno(s) de vendas divergentes, com sinal negativo). A devolver ao lojista (o que saiu do bolso dele: valor_taxa da Orbe menos a comissão contratada, S51): R$ 15.396,77; a recuperar da Orbe: R$ 0,00. A diferença para o líquido pela fórmula (R$ 0,65) é truncamento da Orbe. _(ref.: AN88445802, AN88445486, TX88419350)_
- **F2** Primeira transação divergente em 01/09/2026 e última em 30/09/2026 (30 dia(s) corrido(s)), pela data da venda (no estorno, a da venda original). _(ref.: TX88410128, TX88444796)_
- **F3** Faixas afetadas: débito (12), crédito à vista (35), 2–6x (41), 7–12x (17), Pix (9), antecipação (4). _(ref.: TX88418675, TX88410932, TX88410171)_
- **F4** No mesmo período (01/09/2026 a 30/09/2026), não houve transação do lojista em faixa sem divergência.
- **F5** Diferença variável de +0,89 p.p. a +3,79 p.p., constante dentro de cada faixa: débito +1,49 p.p.; crédito à vista +2,69 p.p.; 2–6x +3,19 p.p.; 7–12x +3,79 p.p.; Pix +0,89 p.p.; antecipação +2,10 p.p.
- **F6** Taxa aplicada = taxa da linha 13 da planilha (desde 01/01/2026), a cobrada antes da isenção, em 118 de 118 transações: débito 1,49%, crédito à vista 2,69%, 2–6x 3,19%, 7–12x 3,79%, Pix 0,89%, antecipação 2,10%.
- **F7** Planilha: linha única do lojista (linha 13, desde 01/01/2026), sem mudança de vigência; a divergência começa em 01/09/2026. _(ref.: TX88410128)_
- **F8** A planilha de taxas não registra a isenção; ela vem do acordo comercial informado pelo financeiro (S07), válido de 01/09/2026 a 31/12/2026; a divergência começa no mesmo dia. _(ref.: TX88410128)_
- **F9** Entre 01/09/2026 e 30/09/2026, 118 de 118 transações das faixas afetadas divergem (100%); somando todas as faixas, 118 de 118 (100%).
- **F10** Fora desse período, o lojista teve 1 transação(ões) faturável(is) no relatório do mês (1 com data de referência antes de 01/09/2026), nenhuma divergente. _(ref.: TX88445133)_

### O que o financeiro já respondeu

- **S07** Casa do Estudante: tarifa zerada no checkout de setembro a dezembro (MDR e antecipação), acordo comercial; a Orbe cobrou e a Helena devolve ao lojista.
- **S18** Casa do Estudante: a Orbe cobrou certo pela planilha porque ninguém avisou a isenção; não há o que cobrar da Orbe, é devolução ao lojista (Helena com o Comercial).
- **S37** Casa do Estudante: uma pendência com o total e o detalhe por transação; não pode entrar na cobrança da Orbe.
- **S30** Ninguém tem a função de avisar Orbe/Ponte das condições novas; a Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas.
- **S41** O que decide cobrar a contraparte é o contrato, não o aviso: Bridge (aditivo assinado, 2,19% desde 15/09) e Mundo Aberto (1,20% negociado e registrado desde julho) são divergência, a Helena contesta com Orbe/Ponte e o lojista é ressarcido; Casa do Estudante é concessão do comercial fora do contrato: a Orbe cobrou o contratado e a devolução sai do bolso da Tarvo.
- **S51** Devolve-se ao lojista o que saiu do bolso dele: o valor_taxa que a Orbe descontou menos a comissão contratada. A lista de divergências segue a fórmula bruto x diferença de taxa; a diferença entre as duas é o truncamento da Orbe.

Exemplos: AN88445802, AN88445486, TX88419350

## G02 — Rota Global Intercâmbio Ltda (Orbe, checkout, divergência de contrato)

- CNPJ 95927868000148 · EC 1074504011
- Divergência: R$ 1.546,28 em 87 transações
- Devolver ao lojista: R$ 1.545,86 · Recuperar do parceiro: R$ 1.545,86

### O que aconteceu

Desde 12/09 a Orbe cobra +0,50 p.p. no crédito à vista, 2–6x e 7–12x; débito, Pix e antecipação estão corretos.

### Ação pela regra

Devolver ao lojista R$ 1.545,86 e contestar R$ 1.545,86 com a Orbe. _(regras: R13, R68, R74)_

### Linha do tempo

| ID | Faixa | De | Até | Taxa aplicada | Taxa contratada | Qtd | Diverge |
|---|---|---|---|---:|---:|---:|---|
| V1 | débito | 01/09/2026 | 18/09/2026 | 1,49% | 1,49% | 10 | não |
| V2 | crédito à vista | 02/09/2026 | 11/09/2026 | 2,49% | 2,49% | 20 | não |
| V3 | crédito à vista | 12/09/2026 | 29/09/2026 | 2,99% | 2,49% | 38 | sim |
| V4 | 2–6x | 30/08/2026 | 11/09/2026 | 2,99% | 2,99% | 13 | não |
| V5 | 2–6x | 12/09/2026 | 29/09/2026 | 3,49% | 2,99% | 31 | sim |
| V6 | 7–12x | 03/09/2026 | 08/09/2026 | 3,59% | 3,59% | 11 | não |
| V7 | 7–12x | 12/09/2026 | 30/09/2026 | 4,09% | 3,59% | 18 | sim |
| V8 | Pix | 03/09/2026 | 30/09/2026 | 0,89% | 0,89% | 15 | não |
| V9 | antecipação | 09/09/2026 | 22/09/2026 | 2,10% | 2,10% | 3 | não |

### Condições do cliente

- **P10** (planilha linha 10) desde 01/01/2026: débito 1,49%; crédito à vista 2,49%; 2–6x 2,99%; 7–12x 3,59%; Pix 0,89%; antecipação 2,10%

### Regras aplicáveis

- **R13** Divergência de checkout = transação com taxa aplicada diferente da contratada; valor = valor bruto × (taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso.
- **R50** Divergência é o lojista pagar diferente do contrato, para mais ou para menos (abaixo do contrato = valor negativo); a Helena decide caso a caso.
- **R68** Quem deve é decidido pelo contrato, não pelo aviso: aditivo ou condição negociada e registrada é divergência de contrato (a Helena contesta o parceiro e o lojista é ressarcido); aviso atrasado é problema de processo. Concessão do Comercial fora do contrato: o parceiro cobrou o contratado e a devolução sai do bolso da Tarvo.
- **R60** Toda divergência de taxa é dinheiro a devolver ao lojista; quando é de contrato, também a recuperar do parceiro.
- **R74** Valor a devolver ao lojista = o que o parceiro descontou de fato (valor_taxa; na remessa, o Spread R$) menos a comissão contratada. A lista de divergências segue a fórmula; a diferença entre as duas é truncamento da Orbe.
- **R51** Venda cobrada fora do contrato e depois estornada: venda e estorno se anulam; cobra-se só a diferença líquida.
- **R70** A taxa do estorno é a da data da venda original.
- **R71** Na lista de divergências, o estorno de uma venda com taxa errada também entra, com valor negativo.
- **R02** A Orbe trunca centavos; a diferença de centavo causada por truncamento não é divergência.

### Fatos detalhados

- **F1** 87 transações divergentes, líquido R$ 1.546,28 (inclui 4 estorno(s) de vendas divergentes, com sinal negativo). A devolver ao lojista (o que saiu do bolso dele: valor_taxa da Orbe menos a comissão contratada, S51): R$ 1.545,86; a recuperar da Orbe: R$ 1.545,86. A diferença para o líquido pela fórmula (R$ 0,42) é truncamento da Orbe. _(ref.: TX88440860, TX88423647, TX88444545)_
- **F2** Primeira transação divergente em 12/09/2026 e última em 30/09/2026 (19 dia(s) corrido(s)), pela data da venda (no estorno, a da venda original). _(ref.: TX88423647, TX88444545)_
- **F3** Faixas afetadas: crédito à vista (38), 2–6x (31), 7–12x (18). _(ref.: TX88424022, TX88424077, TX88423647)_
- **F4** No mesmo período (12/09/2026 a 30/09/2026), sem divergência: débito (7), Pix (10), antecipação (2). _(ref.: TX88424002, TX88424521, AN88445945)_
- **F5** Diferença constante de +0,50 p.p. sobre a taxa contratada em todas as 87 transações.
- **F6** Em todas as faixas afetadas, a taxa aplicada = contratada +0,50 p.p.: crédito à vista 2,49% → 2,99%; 2–6x 2,99% → 3,49%; 7–12x 3,59% → 4,09%.
- **F7** A aba 'ANTIGO 2025 - nao usar' da planilha (mesmo CNPJ) coincide com a taxa aplicada em 2 de 5 faixas com transações no período (crédito à vista 2,99%, 2–6x 3,49%); não explica 7–12x (aplicada 4,09%; aba 3,49%), nem débito (aplicada 1,49%; aba 1,69%) e Pix (aplicada 0,89%; aba 0,99%), que seguiram a taxa contratada vigente (linha 10, desde 01/01/2026).
- **F8** Taxa aplicada sem correspondência na planilha (vigente, outras vigências, abas antigas ou outros lojistas) em: 7–12x 4,09%.
- **F9** Planilha: linha única do lojista (linha 10, desde 01/01/2026), sem mudança de vigência; a divergência começa em 12/09/2026. _(ref.: TX88423647)_
- **F10** Entre 12/09/2026 e 30/09/2026, 87 de 87 transações das faixas afetadas divergem (100%); somando todas as faixas, 87 de 106 (82,1%).
- **F11** Fora desse período, o lojista teve 53 transação(ões) faturável(is) no relatório do mês (53 com data de referência antes de 12/09/2026), nenhuma divergente. _(ref.: TX88445463)_

### O que o financeiro já respondeu

- **S06** Rota Global: o contrato não mudou este ano; a cobrança de +0,50 p.p. desde 12/09 é divergência.
- **S51** Devolve-se ao lojista o que saiu do bolso dele: o valor_taxa que a Orbe descontou menos a comissão contratada. A lista de divergências segue a fórmula bruto x diferença de taxa; a diferença entre as duas é o truncamento da Orbe.

Exemplos: TX88440860, TX88423647, TX88444545

## G03 — Mundo Aberto (Ponte, remessa, divergência de contrato)

- CNPJ 17217888000111
- Divergência: R$ 1.418,85 em 23 operações
- Devolver ao lojista: R$ 1.418,88 · Recuperar do parceiro: R$ 1.418,88

### O que aconteceu

Em setembro a Ponte aplicou 1,50% (padrão) em todas as remessas; o contratado é 1,20%.

### Ação pela regra

Devolver ao lojista R$ 1.418,88 e contestar R$ 1.418,88 com a Ponte. _(regras: R22, R68, R74)_

### Linha do tempo

| ID | Faixa | De | Até | Taxa aplicada | Taxa contratada | Qtd | Diverge |
|---|---|---|---|---:|---:|---:|---|
| V1 | spread de remessa | 01/09/2026 | 30/09/2026 | 1,50% | 1,20% | 23 | sim |

### Condições do cliente

- **P15** (planilha linha 15) desde 01/01/2026: spread de remessa 1,20% (obs: 'spread negociado em jul/26')
- **C006** (cadastro) nota do cadastro: Caso de fronteira: a Ponte não foi avisada do spread de 1,20% (S30), mas a Helena decidiu tratar como divergência e contestar com a Ponte (S05).

### Regras aplicáveis

- **R22** Divergência de remessa = valor cheio que o lojista pagou a mais: (spread % aplicado − contratado) × PTAX × valor em moeda estrangeira.
- **R50** Divergência é o lojista pagar diferente do contrato, para mais ou para menos (abaixo do contrato = valor negativo); a Helena decide caso a caso.
- **R68** Quem deve é decidido pelo contrato, não pelo aviso: aditivo ou condição negociada e registrada é divergência de contrato (a Helena contesta o parceiro e o lojista é ressarcido); aviso atrasado é problema de processo. Concessão do Comercial fora do contrato: o parceiro cobrou o contratado e a devolução sai do bolso da Tarvo.
- **R60** Toda divergência de taxa é dinheiro a devolver ao lojista; quando é de contrato, também a recuperar do parceiro.
- **R74** Valor a devolver ao lojista = o que o parceiro descontou de fato (valor_taxa; na remessa, o Spread R$) menos a comissão contratada. A lista de divergências segue a fórmula; a diferença entre as duas é truncamento da Orbe.
- **R20** Remessa: comissão da Tarvo = 50% do Spread R$ realizado por operação; o excesso contestável entra na nota do mês e o ajuste só entra no mês em que a Ponte devolver.

### Fatos detalhados

- **F1** 23 operações com spread acima do contratado; Spread R$ efetivamente cobrado a mais (realizado menos contratado x PTAX x Valor ME, S51) R$ 1.418,88; pela fórmula da lista de divergências R$ 1.418,85. A devolver ao lojista: R$ 1.418,88; a recuperar da Ponte: R$ 1.418,88. _(ref.: PC-0926-0434, PC-0926-0373, PC-0926-0566)_
- **F2** Primeira operação divergente contratada em 01/09/2026 e última em 30/09/2026 (30 dia(s) corrido(s)). _(ref.: PC-0926-0016, PC-0926-0566)_
- **F3** Moedas das operações divergentes: AUD (8), CAD (4), EUR (1), GBP (2), NZD (3), USD (5).
- **F4** Diferença variável de +0,2991 p.p. a +0,3009 p.p. sobre o spread contratado (1,20%).
- **F5** Spread aplicado de 1,4991% a 1,5009%: coincide com o spread padrão de 1,50% (CC03) dentro da tolerância de 0,01 p.p. (H06) em 23 de 23 operações; contratado 1,20%. _(ref.: PC-0926-0016)_
- **F6** Planilha: linha única do lojista (linha 15, desde 01/01/2026), sem mudança de vigência; a divergência começa em 01/09/2026. _(ref.: PC-0926-0016)_
- **F7** Entre 01/09/2026 e 30/09/2026, 23 de 23 operações válidas do lojista divergem (100%); no mês, 23 operações válidas do lojista.
- **F8** No mês, outros 4 lojista(s) com spread contratado diferente do padrão (Nórdica Educação Internacional Ltda 1,25%, EduAbroad 1,30%, Lisboa Cursos e Viagens Ltda 1,60%, Novo Horizonte Intercambio 1,40%) tiveram 60 operações válidas, nenhuma divergente. _(ref.: PC-0926-0003, PC-0926-0040, PC-0926-0004)_

### O que o financeiro já respondeu

- **S05** Mundo Aberto negociou spread de 1,20% em julho; aplicar mais é divergência, Helena contesta com a Ponte.
- **S10** Divergência de remessa vale pelo valor cheio que o lojista pagou a mais, não só os 50% da Tarvo.
- **S13** O excesso da Mundo Aberto entra na nota de setembro pelo realizado; se a Ponte devolver, a metade da Tarvo sai no mês do ajuste.
- **S30** Ninguém tem a função de avisar Orbe/Ponte das condições novas; a Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas.
- **S41** O que decide cobrar a contraparte é o contrato, não o aviso: Bridge (aditivo assinado, 2,19% desde 15/09) e Mundo Aberto (1,20% negociado e registrado desde julho) são divergência, a Helena contesta com Orbe/Ponte e o lojista é ressarcido; Casa do Estudante é concessão do comercial fora do contrato: a Orbe cobrou o contratado e a devolução sai do bolso da Tarvo.

Exemplos: PC-0926-0434, PC-0926-0373, PC-0926-0566

## G04 — Escola Bridge de Idiomas Ltda (Orbe, checkout, divergência de contrato)

- CNPJ 22224579000109 · EC 1075624862
- Divergência: R$ 29,95 em 5 transações
- Devolver ao lojista: R$ 29,94 · Recuperar do parceiro: R$ 29,94

### O que aconteceu

De 15/09 a 18/09 a Orbe cobrou 2,59% no crédito à vista; o contratado desde 15/09 é 2,19%; débito, 2–6x, 7–12x e Pix estão corretos.

### Ação pela regra

Devolver ao lojista R$ 29,94 e contestar R$ 29,94 com a Orbe. _(regras: R13, R68, R74)_

### Linha do tempo

| ID | Faixa | De | Até | Taxa aplicada | Taxa contratada | Qtd | Diverge |
|---|---|---|---|---:|---:|---:|---|
| V1 | débito | 01/09/2026 | 29/09/2026 | 1,49% | 1,49% | 15 | não |
| V2 | crédito à vista | 01/09/2026 | 13/09/2026 | 2,59% | 2,59% | 8 | não |
| V3 | crédito à vista | 15/09/2026 | 18/09/2026 | 2,59% | 2,19% | 5 | sim |
| V4 | crédito à vista | 23/09/2026 | 30/09/2026 | 2,19% | 2,19% | 9 | não |
| V5 | 2–6x | 01/09/2026 | 29/09/2026 | 3,19% | 3,19% | 42 | não |
| V6 | 7–12x | 01/09/2026 | 27/09/2026 | 3,79% | 3,79% | 17 | não |
| V7 | Pix | 01/09/2026 | 30/09/2026 | 0,89% | 0,89% | 13 | não |

### Condições do cliente

- **P6** (planilha linha 6) até 14/09/2026: débito 1,49%; crédito à vista 2,59%; 2–6x 3,19%; 7–12x 3,79%; Pix 0,89%; antecipação 2,10% (obs: 'renegociado - ver linha de baixo')
- **P7** (planilha linha 7) desde 15/09/2026: débito 1,49%; crédito à vista 2,19%; 2–6x 3,19%; 7–12x 3,79%; Pix 0,89%; antecipação 2,10% (obs: 'só mudou o crédito à vista')

### Regras aplicáveis

- **R13** Divergência de checkout = transação com taxa aplicada diferente da contratada; valor = valor bruto × (taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso.
- **R50** Divergência é o lojista pagar diferente do contrato, para mais ou para menos (abaixo do contrato = valor negativo); a Helena decide caso a caso.
- **R68** Quem deve é decidido pelo contrato, não pelo aviso: aditivo ou condição negociada e registrada é divergência de contrato (a Helena contesta o parceiro e o lojista é ressarcido); aviso atrasado é problema de processo. Concessão do Comercial fora do contrato: o parceiro cobrou o contratado e a devolução sai do bolso da Tarvo.
- **R60** Toda divergência de taxa é dinheiro a devolver ao lojista; quando é de contrato, também a recuperar do parceiro.
- **R74** Valor a devolver ao lojista = o que o parceiro descontou de fato (valor_taxa; na remessa, o Spread R$) menos a comissão contratada. A lista de divergências segue a fórmula; a diferença entre as duas é truncamento da Orbe.
- **R51** Venda cobrada fora do contrato e depois estornada: venda e estorno se anulam; cobra-se só a diferença líquida.
- **R70** A taxa do estorno é a da data da venda original.
- **R71** Na lista de divergências, o estorno de uma venda com taxa errada também entra, com valor negativo.
- **R02** A Orbe trunca centavos; a diferença de centavo causada por truncamento não é divergência.

### Fatos detalhados

- **F1** 5 transações divergentes, líquido R$ 29,95. A devolver ao lojista (o que saiu do bolso dele: valor_taxa da Orbe menos a comissão contratada, S51): R$ 29,94; a recuperar da Orbe: R$ 29,94. A diferença para o líquido pela fórmula (R$ 0,01) é truncamento da Orbe. _(ref.: TX88431123, TX88429931, TX88428053)_
- **F2** Primeira transação divergente em 15/09/2026 e última em 18/09/2026 (4 dia(s) corrido(s)), pela data da venda (no estorno, a da venda original). _(ref.: TX88428053, TX88431123)_
- **F3** Faixas afetadas: crédito à vista (5). _(ref.: TX88428053)_
- **F4** No mesmo período (15/09/2026 a 18/09/2026), sem divergência: débito (1), 2–6x (1), 7–12x (3), Pix (2). _(ref.: TX88427720, TX88430138, TX88429641)_
- **F5** Diferença constante de +0,40 p.p. sobre a taxa contratada em todas as 5 transações.
- **F6** Taxa aplicada = vigência anterior do mesmo lojista na planilha (linha 6, até 14/09/2026) em: crédito à vista 2,59%; a vigente no período (linha 7) é crédito à vista 2,19%.
- **F7** Planilha: linha 6 até 14/09/2026; linha 7 desde 15/09/2026. Mudança de vigência em 15/09/2026; a divergência começa no mesmo dia (15/09/2026) e termina em 18/09/2026. _(ref.: TX88428053)_
- **F8** Entre 15/09/2026 e 18/09/2026, 5 de 5 transações das faixas afetadas divergem (100%); somando todas as faixas, 5 de 12 (41,7%).
- **F9** Fora desse período, o lojista teve 97 transação(ões) faturável(is) no relatório do mês (57 com data de referência antes de 15/09/2026; 40 depois de 18/09/2026), nenhuma divergente. _(ref.: TX88410286, TX88431908)_

### O que o financeiro já respondeu

- **S30** Ninguém tem a função de avisar Orbe/Ponte das condições novas; a Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas.
- **S41** O que decide cobrar a contraparte é o contrato, não o aviso: Bridge (aditivo assinado, 2,19% desde 15/09) e Mundo Aberto (1,20% negociado e registrado desde julho) são divergência, a Helena contesta com Orbe/Ponte e o lojista é ressarcido; Casa do Estudante é concessão do comercial fora do contrato: a Orbe cobrou o contratado e a devolução sai do bolso da Tarvo.
- **S51** Devolve-se ao lojista o que saiu do bolso dele: o valor_taxa que a Orbe descontou menos a comissão contratada. A lista de divergências segue a fórmula bruto x diferença de taxa; a diferença entre as duas é o truncamento da Orbe.

Exemplos: TX88431123, TX88429931, TX88428053
