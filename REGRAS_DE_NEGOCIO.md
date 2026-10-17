# Regras de negócio comprovadas

Só entra aqui o que foi **confirmado pelo financeiro da Tarvo** (fonte S## = `docs/00_slack_respostas_financeiro.md`) ou é **fato verificável no arquivo** (fonte D = dado). O que é premissa nossa está em `HIPOTESES.md`.

## Geral
| ID | Regra | Fonte |
|---|---|---|
| R01 | Arredondamento comum ao centavo, meio centavo para cima e simétrico no negativo (0,005 → 0,01; −0,005 → −0,01). Aplicado **linha a linha, depois soma**. | S11 |
| R02 | A Orbe trunca centavos; a Tarvo não. Diferença de centavo causada por truncamento **não é divergência**. | S11 |
| R03 | Competência = mês do evento: venda/estorno pelo `data_movimento`; remessa pela **data de contratação**. Mês fechado não reabre. | S02, S05 |

## Checkout (Orbe)
| ID | Regra | Fonte |
|---|---|---|
| R10 | Comissão por transação = valor_bruto × taxa **contratada** (planilha), não o `valor_taxa` da Orbe. É a taxa inteira (sem custo Orbe). | S01, S17 |
| R11 | Estorno abate a comissão do mês do estorno, inclusive de vendas de agosto, usando a taxa contratada vigente **na data da venda original**. | S02, S17 |
| R12 | Antecipação: bruto × taxa de antecipação contratada; entra na comissão e na mesma nota. Reversão de antecipação anula exatamente a taxa da antecipação que reverte. | S04, S17 |
| R13 | Divergência = transação com taxa aplicada ≠ contratada. Valor = valor_bruto × (taxa aplicada − contratada). Devolução ao lojista é decisão da Helena, caso a caso. | S01, S11 |
| R14 | ECs sem código na planilha: 1043300981 = Novo Horizonte Intercâmbio; 1043396662 = Horizonte Viagens e Turismo (empresas diferentes); 1038867654 = Kiwi Experience. CNPJ e taxas nas linhas delas na aba vigente. | S03 |
| R15 | Atlas Idiomas (EC 1076801732): sem contrato vigente → **não faturar** até o comercial confirmar a taxa (pendência, quem decide: Comercial). | S03 |
| R16 | Rota Global (EC 1074504011): contrato não mudou; a cobrança +0,50 p.p. desde 12/09 é divergência. | S06 |
| R17 | Casa do Estudante (EC 1018325654): taxa contratada **zero** no checkout (MDR e antecipação) de set a dez/2026. Tudo que a Orbe cobrou é divergência a devolver. | S07 |

## Remessa (Ponte Câmbio)
| ID | Regra | Fonte |
|---|---|---|
| R20 | Comissão Tarvo = 50% do "Spread R$" **realizado** por operação, arredondado por operação (R01). Excesso contestável entra na nota do mês; ajuste só no mês em que a Ponte devolver. | S05, S11, S13 |
| R21 | Spread contratado em branco/"padrão" = 1,5% sobre PTAX de referência. Mundo Aberto = 1,20% (desde julho). | S05 |
| R22 | Divergência de remessa = valor **cheio** que o lojista pagou a mais: (spread % aplicado − contratado) × PTAX × valor em moeda estrangeira. | S10 |
| R23 | Spread negativo (trava vencida) não é aceito: fora da comissão e da nota; vira pendência de contestação. | S05 |
| R24 | Nº de operação é único: repetida conta uma vez; também vai para a lista de correção da Ponte. | S05, S15 |
| R25 | Status "APROVADO C/ RESSALVA" não altera nada para a Tarvo. | S05 |
| R26 | Não assumir desconto da Ponte no repasse; conferir o TED quando cair (pendência da Helena). | S14 |

## Notas fiscais
| ID | Regra | Fonte |
|---|---|---|
| R30 | Checkout: 1 nota por lojista/mês, valor = comissão do mês (vendas + antecipações − estornos − reversões, pela taxa contratada). | S04 |
| R31 | Saldo zero ou negativo → não emite nota; negativo não transporta → pendência para a Helena. | S04 |
| R32 | Remessa: 1 nota só, tomadora Ponte Câmbio (CNPJ 75.374.179/0001-46), pelo total da participação. | S04 |
| R33 | Discriminação: texto simples com serviço e competência. | S04 |

## Extratos e plano de contas
| ID | Regra | Fonte |
|---|---|---|
| R40 | `conta_codigo` = contrapartida do movimento bancário. Valor já registrado → baixa a conta onde estava (não vira receita/despesa de novo). | S12 |
| R41 | Folha, ISS, INSS, FGTS, IRRF, PIS, COFINS pagos em setembro são de agosto e estavam provisionados → baixa do passivo. Repasse Ponte 04/09 (MRD2026090132) baixa 1.1.03.002. | S08, S12 |
| R42 | Tarifas, aluguel, cloud, assinaturas e serviços não estavam provisionados → despesa direta do mês. | S12 |
| R43 | Orbe deposita tudo no Aurora; créditos Orbe são classificados, sem conciliação parcela a parcela neste fechamento. | S16 |
| R44 | PIX R$ 7.350 sem identificação não é receita. | S09 |
