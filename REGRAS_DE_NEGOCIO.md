# Regras de negócio comprovadas

Só entra aqui o que foi **confirmado pelo financeiro da Tarvo** (fonte S## = `docs/00_slack_respostas_financeiro.md`) ou é **fato verificável no arquivo** (fonte D = dado). O que é premissa nossa está em `HIPOTESES.md`. O contexto da empresa (camada 1) está em `CONTEXTO_EMPRESA.md`.

> **Como este arquivo está organizado, e por quê.** O conhecimento do fechamento tem três naturezas diferentes, que mudam em ritmos diferentes e têm donos diferentes:
> 1. **Regras** (seções A a E): *como* a Tarvo fecha o mês. Valem todo mês, para qualquer lojista. Mudam raramente, e só com aprovação da Helena (regra de fechamento) ou do Comercial (taxa e condição), conforme S32.
> 2. **Condições contratuais vigentes (cadastro):** *o que* foi combinado com cada lojista (isenções, spreads negociados, de-para de EC). Mudam quando o Comercial fecha um contrato. São dado de cadastro, não regra.
> 3. **Ocorrências de setembro/2026:** *o que aconteceu* neste mês (Rota cobrada a mais, duplicata, PIX sem origem). São fatos de um mês; não se repetem por definição e nunca viram regra.
>
> Isso importa porque a IA de investigação recebe **regras + condições**, mas **não ocorrências**. Se ela recebesse "Rota +0,5 p.p. desde 12/09" como regra, passaria a esperar isso em outubro ou a explicar casos novos pelo caso velho. As ocorrências chegam a ela só como fatos do dossiê do mês, calculados pelo código.
>
> IDs R## não são renumerados. Regras novas começam em R50. Quando uma regra antiga era, na verdade, condição ou ocorrência, ela saiu da lista e aparece nas seções finais com a marca "ex-R##" (coluna "Antes"). Por isso o código e os CSVs que citam R14, R16, R17, R21, R41 ou R44 continuam rastreáveis: R14 → CC04; R16 → CC06/OC01; R17 → CC01/OC03 (tratamento em R52); R21 → CC02/CC03; R41 e R44 viraram regras gerais, com o caso de setembro em OC12 e OC08.
>
> **Aprovado por:** Helena = regra de fechamento; Comercial = taxa ou condição comercial (Helena registra) — S32. **Data:** data da resposta no Slack (16/10/2026 para S01–S17; 17/10/2026 para S18–S39).

## A. Regras de comissionamento

### Geral
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R01 | Arredondamento comum ao centavo, meio centavo para cima e simétrico no negativo (0,005 → 0,01; −0,005 → −0,01). Aplicado **linha a linha, depois soma**. | S11 | Helena | 16/10/2026 |
| R02 | A Orbe trunca centavos; a Tarvo não. Diferença de centavo causada por truncamento **não é divergência**. | S11 | Helena | 16/10/2026 |
| R03 | Competência = mês do evento: venda/estorno pelo `data_movimento`; remessa pela **data de contratação**. Mês fechado não reabre. | S02, S05 | Helena | 16/10/2026 |

### Checkout (Orbe)
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R10 | Comissão por transação = valor_bruto × taxa **contratada** (planilha), não o `valor_taxa` da Orbe. É a taxa inteira (sem custo Orbe). | S01, S17 | Helena | 16/10/2026 |
| R11 | Estorno abate a comissão do mês do estorno, inclusive de vendas de meses anteriores, usando a taxa contratada vigente **na data da venda original** — mesmo que, na data do estorno, valha uma isenção que não valia na venda. | S02, S17, S21 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R12 | Antecipação: bruto × taxa de antecipação contratada; entra na comissão e na mesma nota. Reversão de antecipação anula exatamente a taxa da antecipação que reverte. | S04, S17 | Helena | 16/10/2026 |
| R15 | Lojista sem contrato vigente na planilha (taxa desconhecida) → **não faturar** até o Comercial confirmar a taxa; pendência, quem decide: Comercial. (Caso de setembro: Atlas, ver condições.) | S03, S38 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R55 | Taxa confirmada depois **vale retroativa** desde a primeira transação do lojista. O fechamento do mês seguinte puxa as linhas que ficaram pendentes nos meses anteriores e as fatura na nota do mês, com rastro até a origem. | S27 | Helena | 17/10/2026 |

### Remessa (Ponte Câmbio)
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R20 | Comissão Tarvo = 50% do "Spread R$" **realizado** por operação, arredondado por operação (R01). Excesso contestável entra na nota do mês; ajuste só no mês em que a Ponte devolver (R56). | S05, S11, S13 | Helena | 16/10/2026 |
| R58 | CNPJ de remessa sem linha na planilha: calcular a metade do spread mesmo assim e abrir pendência de cadastro para o Comercial. | S26 | Helena | 17/10/2026 |

## B. Regras de tratamento de exceções e divergências
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R13 | Divergência checkout = transação com taxa aplicada ≠ contratada. Valor = valor_bruto × (taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso, com transação e valor. | S01, S11 | Helena | 16/10/2026 |
| R50 | **Divergência = o lojista pagou diferente do contrato, para mais ou para menos**, no checkout e na remessa. Cobrança abaixo do contrato também é divergência (valor negativo); Helena decide caso a caso. | S19, S24, S25 | Helena | 17/10/2026 |
| R51 | Venda cobrada fora do contrato e depois estornada: venda e estorno **se anulam**; cobra-se do parceiro só a diferença líquida. | S20 | Helena | 17/10/2026 |
| R60 | Toda divergência de taxa é dinheiro a **devolver ao lojista** (a taxa sai descontada na liquidação, então ele já recebeu a menos). A pendência informa "devolver ao lojista R$ X" e, quando a divergência é de contrato, "recuperar do parceiro R$ X". | S34 | Helena | 17/10/2026 |
| R52 | **Condição não informada ao parceiro ≠ divergência de contrato.** Se o parceiro cobrou certo pelo que sabia (ex.: isenção que ninguém comunicou), natureza = ISENCAO_NAO_INFORMADA: **não se cobra o parceiro**, a Tarvo devolve ao lojista. Fica separada das divergências de contrato e fora da cobrança da Orbe: uma pendência para Helena + Comercial, com o total e o detalhe por transação marcado. | S18, S37 | Helena | 17/10/2026 |
| R22 | Divergência de remessa = valor **cheio** que o lojista pagou a mais: (spread % aplicado − contratado) × PTAX × valor em moeda estrangeira. | S10 | Helena | 16/10/2026 |
| R23 | Spread negativo (trava vencida) não é aceito: fora da comissão e da nota; vira pendência de contestação. | S05 | Helena | 16/10/2026 |
| R53 | Spread negativo é **contestação, de outra natureza**: o lojista não pagou a mais, o prejuízo é da Tarvo com a Ponte. Não é divergência; pode ser listado junto das divergências só se ficar claro que é outra natureza. | S25 | Helena | 17/10/2026 |
| R24 | Nº de operação é único: repetida conta uma vez; também vai para a lista de correção da Ponte. | S05, S15 | Helena | 16/10/2026 |
| R25 | Status "APROVADO C/ RESSALVA" não altera nada para a Tarvo. | S05 | Helena | 16/10/2026 |
| R26 | Não assumir desconto da Ponte no repasse (contestação não aberta); conferir o TED quando cair (pendência da Helena). | S14 | Helena | 16/10/2026 |
| R56 | Retorno de contestação da Ponte: a Ponte responde por e-mail e lança o ajuste (crédito ou débito) no **relatório do mês seguinte**. Helena confere e registra no fechamento do mês em que o ajuste aparece. | S36 | Helena | 17/10/2026 |
| R54 | Antecipação acima das vendas acumuladas do lojista → **alerta** para Helena e Comercial (não há trava na Orbe; antecipação só deveria existir sobre o que já foi vendido). Mais grave se o lojista não tem contrato. | S23 | Helena | 17/10/2026 |
| R57 | A Tarvo não vende acima de 12x; transação com mais de 12 parcelas → pendência. | S38 | Helena | 17/10/2026 |
| R59 | Lojista sem contrato: **o repasse não para** (o dinheiro é do lojista); fica suspenso só o faturamento da taxa. | S39 | Helena | 17/10/2026 |

## C. Regras contábeis e de extratos
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R40 | `conta_codigo` = contrapartida do movimento bancário. Valor já registrado → baixa a conta onde estava (não vira receita/despesa de novo). | S12 | Helena | 16/10/2026 |
| R61 | **Provisão sempre:** todo mês, a folha e os impostos do mês ficam provisionados no fechamento; o pagamento no mês seguinte baixa a provisão. | S29 | Helena | 17/10/2026 |
| R41 | Consequência de R40/R61: folha, ISS, INSS, FGTS, IRRF, PIS e COFINS pagos no mês são do mês anterior e baixam o passivo provisionado. O repasse da Ponte do spread do mês anterior baixa 1.1.03.002 (em setembro: MRD2026090132, R$ 61.884,12, de 04/09). | S08, S12, S29 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R42 | Tarifas, aluguel, cloud, assinaturas e serviços não são provisionados → despesa direta do mês. | S12 | Helena | 16/10/2026 |
| R43 | Orbe deposita tudo no Aurora; créditos Orbe são classificados, sem conciliação parcela a parcela neste fechamento (o resto aguarda agenda de recebíveis). | S16 | Helena | 16/10/2026 |
| R44 | Crédito sem origem identificada **não é receita** até ser identificado. (Caso de setembro: PIX R$ 7.350, ver ocorrências.) | S09 | Helena | 16/10/2026 |

## D. Notas fiscais
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R30 | Checkout: 1 nota por lojista/mês, valor = comissão do mês (vendas + antecipações − estornos − reversões, pela taxa contratada). | S04 | Helena | 16/10/2026 |
| R31 | Saldo zero ou negativo → não emite nota; negativo não transporta → pendência para a Helena. | S04 | Helena | 16/10/2026 |
| R32 | Remessa: 1 nota só, tomadora Ponte Câmbio (CNPJ 75.374.179/0001-46), pelo total da participação. | S04, D | Helena | 16/10/2026 |
| R33 | Discriminação: texto simples com serviço e competência. | S04 | Helena | 16/10/2026 |

## E. Governança (quem aprova o quê)
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R62 | Taxa e condição comercial: **aprova o Comercial**, Helena registra. Regra de como fechar: **aprova a Helena**. Toda regra registra quem aprovou e quando. | S32 | Helena | 17/10/2026 |
| R63 | Cadastro e contrato (lojista novo, taxa, CNPJ fora da planilha) **decide o Comercial**. A Bia mantém a planilha, mas não decide taxa. Pendências de cadastro/contrato têm o Comercial como responsável. | S38 | Helena | 17/10/2026 |
| R64 | Pendência: **uma por contraparte e por lojista**, com o detalhe das transações anexado (vira o rascunho de contestação). | S38 | Helena | 17/10/2026 |
| R65 | Contestação: um rascunho por contraparte (Orbe, Ponte) com as operações anexadas; **Helena revisa e envia**. Nada é enviado automaticamente. | S31 | Helena | 17/10/2026 |
| R66 | A Helena não valida a classificação conta a conta: vale o critério escrito de R40/R42 (S12), com as premissas em `HIPOTESES.md`. | S38 | Helena | 17/10/2026 |

---

## Condições contratuais vigentes (cadastro)
Dado de cadastro, não regra: muda quando o Comercial fecha ou altera um contrato (R62, R63). A IA recebe esta seção junto com as regras.

| ID | Condição | Fonte | Aprovado por | Data | Antes |
|---|---|---|---|---|---|
| CC01 | Casa do Estudante (EC 1018325654): tarifa **zero** no checkout (MDR e antecipação) de set a dez/2026, acordo comercial. Remessa normal. A Orbe não foi avisada (S30), então a cobrança segue R52. | S07, S18 | Comercial (Helena registra) | 16/10/2026 (rev. 17/10/2026) | ex-R17 |
| CC02 | Mundo Aberto: spread de remessa **1,20%**, negociado em julho/2026. A Ponte não foi avisada (S30); mesmo assim, Helena trata como divergência e contesta (S05). | S05, S30 | Comercial (Helena registra) | 16/10/2026 | ex-R21 |
| CC03 | Spread contratado em branco ou "padrão" na planilha = **1,5%** sobre a PTAX de referência. | S05 | Comercial (Helena registra) | 16/10/2026 | ex-R21 |
| CC04 | De-para de ECs sem código na planilha: 1043300981 = Novo Horizonte Intercâmbio; 1043396662 = Horizonte Viagens e Turismo (empresas diferentes); 1038867654 = Kiwi Experience. CNPJ e taxas nas linhas delas na aba vigente. | S03 | Comercial (Helena registra) | 16/10/2026 | ex-R14 |
| CC05 | Atlas Idiomas (EC 1076801732): só na aba 2025, **sem contrato vigente**, taxa desconhecida; transaciona desde 10/09. Aplica R15, R54, R55 e R59. | S03, S23, S27, S39 | Comercial (Helena registra) | 16/10/2026 (rev. 17/10/2026) | ex-R15 (parte) |
| CC06 | Rota Global (EC 1074504011): contrato **inalterado** em 2026. | S06 | Comercial (Helena registra) | 16/10/2026 | ex-R16 |
| CC07 | Bridge Idiomas (EC 1075624862): crédito à vista 2,59% até 14/09 e **2,19% a partir de 15/09** (duas linhas na planilha). A Orbe foi avisada alguns dias depois (S30). | D, S30 | Comercial (Helena registra) | 17/10/2026 | — |

## Ocorrências de setembro/2026
Fatos deste mês. Não são regra e **não vão para a IA como contexto**; ela só os vê como fatos do dossiê. Valores de `saida/*.csv` e `PITCH.md`.

| ID | Ocorrência | Valor | Fonte | Tratada por | Antes |
|---|---|---|---|---|---|
| OC01 | Rota Global cobrada **+0,50 p.p.** desde 12/09 (contrato inalterado, CC06). | R$ 1.546,28 em 87 transações | S06, D | R13, R50, R60 | ex-R16 |
| OC02 | Bridge cobrada pela vigência anterior (2,59% × 2,19%) em 5 vendas à vista de **15 a 18/09**; a Orbe ajustou depois de avisada. | R$ 29,95 em 5 transações | D, S30 | R13, R50, R60 | — |
| OC03 | Casa do Estudante cobrada pela taxa cheia durante a isenção (CC01). Estorno TX88445133 de venda de 21/08 abate à taxa de agosto: Casa fecha em −R$ 5,50, sem nota. | R$ 15.397,42 em 118 transações | S07, S18, S21, D | R52, R11, R31 | ex-R17 |
| OC04 | Mundo Aberto cobrada a ~1,50% com contrato de 1,20% (CC02). | R$ 1.418,85 em 23 operações | S05, D | R22, R50, R20 | — |
| OC05 | Atlas Idiomas transacionou sem contrato; antecipou R$ 179.592,82 em 15/09 com R$ 55.357,50 de vendas acumuladas. | R$ 7.876,05 cobrados pela Orbe (referência) em 57 transações | S03, S23, D | R15, R54, R59 | ex-R15 (parte) |
| OC06 | Operação duplicada **PC-0926-0162** no relatório da Ponte. | R$ 821,88 | S05, S15, D | R24 | — |
| OC07 | 4 spreads negativos: PC-0926-0210, -0326, -0491, -0545 (trava D-1 vencida). | −R$ 1.834,05 realizado | S05, S25, D | R23, R53 | — |
| OC08 | PIX **R$ 7.350,00** (CNPJ 38.686.002/0001-80, Aurora) sem origem identificada. | R$ 7.350,00 | S09 | R44 (conta: H12) | ex-R44 (parte) |
| OC09 | PIX **R$ 18.240,00** de "PONTE AEREA ESTUDANTIL L" (Meridiano, MRD2026090425, 17/09): adiantamento do lojista Ponte Aérea Estudantil (sem relação com a Ponte Câmbio) para uma remessa que sai em outubro. | R$ 18.240,00 | S22 | conta: H10 | — |
| OC10 | Devolução PIX **R$ 12.400,00** da Mundo Aberto (Aurora): repasse que voltou, motivo desconhecido. | R$ 12.400,00 | S09, S28 | conta: H11 | — |
| OC11 | Transferência **R$ 300.000,00** do Aurora em 30/09, que cai no Meridiano em 01/10 (em trânsito). | R$ 300.000,00 | S09 | conta: H13 | — |
| OC12 | Pagamentos de agosto quitados em setembro (folha e tributos) e repasse Ponte de 04/09 (MRD2026090132). | R$ 61.884,12 (repasse Ponte) | S08 | R41 | ex-R41 (parte) |
