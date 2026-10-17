# Regras de negócio (gerais)

Só entra aqui o que foi **confirmado pelo financeiro da Tarvo** (fonte S## = `docs/00_slack_respostas_financeiro.md`) ou é **fato verificável no arquivo** (fonte D = dado). O que é premissa nossa está em `HIPOTESES.md`. O contexto da empresa está em `CONTEXTO_EMPRESA.md`.

> **O que é regra, o que é condição de cliente e o que é ocorrência do mês.**
> - **Regra (este arquivo):** *como* a Tarvo fecha o mês. Vale todo mês, para qualquer lojista. Muda raramente, e só com aprovação da Helena (regra de fechamento) ou do Comercial (taxa e condição), conforme R62. Casos de um cliente ou de um mês aparecem aqui, no máximo, como exemplo entre parênteses.
> - **Condição de cliente (cadastro):** *o que* foi combinado com cada lojista (isenção, spread negociado, de-para de EC, lojista bloqueado). Fica em `cadastro/condicoes_comerciais.csv`, editável pela aba **Clientes** da tela, com quem aprovou e a vigência. Os IDs são C### (C001, C002...). A planilha de taxas do cliente nunca é alterada.
> - **Ocorrência do mês:** *o que aconteceu* naquele fechamento (cobrança fora do contrato, duplicata, PIX sem origem). Fica no registro do fechamento, `docs/fechamento_2026-09.md` para setembro/2026. Ocorrência nunca vira regra.
>
> A IA de investigação recebe regras e condições, mas **não ocorrências**: as ocorrências chegam a ela só como fatos do dossiê do mês, calculados pelo código.
>
> **IDs R## não são renumerados.** Regras novas começam em R50. Regras que eram, na verdade, condição ou ocorrência saíram daqui e continuam rastreáveis: R14 → C002 a C004 (de-para de EC); R15 (parte da Atlas) → C005; R16 → ocorrência da Rota Global; R17 → C001 (isenção da Casa do Estudante; tratamento geral em R52); R21 voltou para cá como regra geral (spread padrão); o spread de 1,20% da Mundo Aberto está na planilha de taxas do cliente, e a observação de fronteira dela é a C006 (nota da pendência). Os antigos CC## e OC## passaram para o cadastro (C###) e para o registro do fechamento.
>
> **Aprovado por:** Helena = regra de fechamento; Comercial = taxa ou condição comercial (Helena registra), S32. **Data:** data da resposta no Slack (16/10/2026 para S01–S17; 17/10/2026 para S18–S54).

## 1. Comissionamento

| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R01 | Arredondamento comum ao centavo: meio centavo sobe, e o negativo é simétrico (0,005 vira 0,01; −0,005 vira −0,01). Arredonda **linha a linha, depois soma**. | S11 | Helena | 16/10/2026 |
| R02 | A Orbe trunca centavos; a Tarvo não. Diferença de centavo causada por truncamento **não é divergência**. | S11 | Helena | 16/10/2026 |
| R03 | Competência é o mês do evento: venda e estorno pelo `data_movimento`; remessa pela **data de contratação**. Mês fechado não reabre. | S02, S05 | Helena | 16/10/2026 |
| R10 | Checkout: comissão da transação = valor bruto × taxa **contratada** (planilha de taxas), não o `valor_taxa` da Orbe. É a taxa inteira, sem custo da Orbe. | S01, S17 | Helena | 16/10/2026 |
| R11 | Estorno abate a comissão do mês do estorno, inclusive de vendas de meses anteriores, pela taxa contratada vigente **na data da venda original**, mesmo que na data do estorno valha uma isenção que não valia na venda. | S02, S17, S21 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R12 | Antecipação: valor bruto × taxa de antecipação contratada; entra na comissão e na mesma nota. Reversão de antecipação anula exatamente a taxa da antecipação que reverte. | S04, S17 | Helena | 16/10/2026 |
| R15 | Lojista sem contrato vigente na planilha (taxa desconhecida): **não faturar** até o Comercial confirmar a taxa. Abre pendência e quem decide é o Comercial. O CNPJ de uma aba antiga só **identifica** o lojista; a taxa daquela aba não vale. Aparecer com zero ou ficar fora de `comissoes_por_lojista.csv` é escolha nossa (H29). (Exemplo: Atlas Idiomas, condição C005.) | S03, S38, S45 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R55 | Taxa confirmada depois **vale retroativa** desde a primeira transação do lojista. O fechamento do mês seguinte puxa as linhas que ficaram pendentes nos meses anteriores e as fatura na nota do mês, com rastro até a origem. | S27 | Helena | 17/10/2026 |
| R20 | Remessa: comissão da Tarvo = 50% do "Spread R$" **realizado** por operação, arredondado por operação (R01). O excesso contestável entra na nota do mês; o ajuste só entra no mês em que a Ponte devolver (R56), na linha de ajuste de R67. | S05, S11, S13, S40 | Helena | 16/10/2026 |
| R21 | Spread de remessa contratado em branco ou "padrão" na planilha = **1,5%** sobre a PTAX de referência. | S05 | Comercial (Helena registra) | 16/10/2026 |
| R58 | CNPJ de remessa sem linha na planilha: calcular a metade do spread mesmo assim e abrir pendência de cadastro para o Comercial. | S26 | Helena | 17/10/2026 |

## 2. Divergências e exceções

### O que é divergência e quem paga
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R13 | Divergência de checkout = transação com taxa aplicada diferente da contratada. Valor = valor bruto × (taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso, com transação e valor. | S01, S11 | Helena | 16/10/2026 |
| R50 | **Divergência = o lojista pagou diferente do contrato, para mais ou para menos**, no checkout e na remessa. Cobrança abaixo do contrato também é divergência (valor negativo); Helena decide caso a caso. | S19, S24, S25 | Helena | 17/10/2026 |
| R22 | Divergência de remessa = valor **cheio** que o lojista pagou a mais: (spread % aplicado − contratado) × PTAX × valor em moeda estrangeira. | S10 | Helena | 16/10/2026 |
| R68 | **Quem decide quem deve é o contrato, não o aviso.** Aditivo assinado ou condição negociada e registrada = divergência de contrato: Helena contesta a Orbe ou a Ponte e o lojista é ressarcido. Aviso atrasado é problema de processo e não muda quem deve. Concessão do Comercial **fora do contrato**: o parceiro cobrou o contratado, não há o que recuperar e a devolução sai do bolso da Tarvo (R52). | S41, S30 | Helena | 17/10/2026 |
| R52 | **Concessão comercial fora do contrato não é divergência de contrato.** Se o parceiro cobrou o contratado (por exemplo, isenção que o Comercial deu e ninguém comunicou), a natureza é ISENCAO_NAO_INFORMADA, descrita como "concessão comercial fora do contrato": **não se cobra o parceiro** e a devolução ao lojista sai do bolso da Tarvo (R68). Fica separada das divergências de contrato e fora da cobrança da Orbe: uma pendência para Helena + Comercial, com o total e o detalhe por transação marcado. Linhas dela em `divergencias_taxa.csv` são opcionais (S48); o que importa é ficar separada. | S18, S37, S41, S48 | Helena | 17/10/2026 |
| R60 | Toda divergência de taxa é dinheiro a **devolver ao lojista** (a taxa sai descontada na liquidação, então ele já recebeu a menos). A pendência informa "devolver ao lojista R$ X" e, quando a divergência é de contrato, "recuperar do parceiro R$ X". O valor segue R74. | S34, S51 | Helena | 17/10/2026 |
| R74 | **Valor a devolver ao lojista** = o que a Orbe (ou a Ponte) **descontou de fato** (`valor_taxa`; na remessa, o Spread R$) menos a comissão contratada, porque é o que saiu do bolso dele. A lista `divergencias_taxa.csv` segue a **fórmula** (bruto × diferença de taxa); a diferença entre as duas é truncamento da Orbe (R02). | S51, S11 | Helena | 17/10/2026 |

### Como tratar cada caso
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R51 | Venda cobrada fora do contrato e depois estornada: venda e estorno **se anulam**; cobra-se do parceiro só a diferença líquida. | S20 | Helena | 17/10/2026 |
| R70 | **Taxa do estorno:** a da data da **venda original**; a faixa (modalidade e parcelas) vem da própria linha do estorno (R11). | S44, S02 | Helena | 17/10/2026 |
| R71 | **Lista de divergências:** transação por transação; o estorno de uma venda que veio com taxa errada também entra, com valor negativo (R51). | S46, S20 | Helena | 17/10/2026 |
| R72 | **Isenção ou taxa zero com vigência:** vale para venda a partir da data de início; estorno de venda anterior segue a taxa da venda (R11). Para **antecipação** vale a **data da antecipação** (o serviço é prestado no dia); não é preciso buscar as vendas de origem. | S47, S21 | Helena | 17/10/2026 |
| R23 | Spread negativo (trava vencida) não é aceito: fica fora da comissão e da nota e vira pendência de contestação. | S05 | Helena | 16/10/2026 |
| R53 | Spread negativo é **contestação, de outra natureza**: o lojista não pagou a mais, o prejuízo é da Tarvo com a Ponte. Não é divergência; pode ser listado junto só se ficar claro que é outra natureza. A pendência traz dois valores rotulados (R69). | S25, S43 | Helena | 17/10/2026 |
| R69 | **Pendência de spread negativo com dois valores rotulados:** (1) o **spread realizado** do relatório (o que aconteceu) e (2) a **diferença até o spread contratado** (`valor_brl`: o que a Helena pede à Ponte, porque a trava deveria ter sido honrada). | S43 | Helena | 17/10/2026 |
| R24 | Nº de operação é único: operação repetida conta uma vez e também vai para a lista de correção da Ponte. | S05, S15 | Helena | 16/10/2026 |
| R25 | Status "APROVADO C/ RESSALVA" não altera nada para a Tarvo. | S05 | Helena | 16/10/2026 |
| R26 | Não assumir desconto da Ponte no repasse (contestação não aberta); conferir o TED quando cair (pendência da Helena). | S14 | Helena | 16/10/2026 |
| R56 | Retorno de contestação da Ponte: a Ponte responde por e-mail e lança o ajuste (crédito ou débito) no **relatório do mês seguinte**. Helena confere e registra no fechamento do mês em que o ajuste aparece. | S36 | Helena | 17/10/2026 |
| R67 | **Ajuste de contestação da Ponte** (linha nova no relatório, Nº de Operação próprio, observação "AJUSTE REF PC-…"): entra no mês em que **aparece**, abatendo a participação daquele mês dentro da nota única da Ponte; o rastro aponta a operação original. Sem nota complementar. Mês zerado ou negativo: não emite nota e vira pendência. O valor da participação (50% do Spread R$ do ajuste) é premissa nossa (H30). | S40, S36 | Helena | 17/10/2026 |

### Alertas e bloqueios
| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R54 | Antecipação acima das vendas acumuladas do lojista gera **alerta** para Helena e Comercial (não há trava na Orbe; antecipação só deveria existir sobre o que já foi vendido). É mais grave se o lojista não tem contrato. **Critério do alerta (nosso, H28):** só lojista novo, e pela antecipação acumulada líquida de reversões contra as vendas acumuladas. | S23, S42, S50 | Helena | 17/10/2026 |
| R57 | A Tarvo não vende acima de 12x; transação com mais de 12 parcelas vira pendência. | S38 | Helena | 17/10/2026 |
| R59 | Lojista sem contrato: **o repasse não para** (o dinheiro é do lojista); fica suspenso só o faturamento da taxa. | S39 | Helena | 17/10/2026 |

## 3. Notas fiscais

| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R30 | Checkout: 1 nota por lojista por mês, no valor da comissão do mês (vendas + antecipações − estornos − reversões, pela taxa contratada). | S04 | Helena | 16/10/2026 |
| R31 | Saldo zero ou negativo: não emite nota. Saldo negativo não transporta para o mês seguinte e vira pendência para a Helena. | S04 | Helena | 16/10/2026 |
| R32 | Remessa: 1 nota só, tomadora Ponte Câmbio (CNPJ 75.374.179/0001-46), pelo total da participação. | S04, D | Helena | 16/10/2026 |
| R33 | Discriminação: texto simples com o serviço e a competência. | S04 | Helena | 16/10/2026 |

## 4. Extratos e contabilidade

| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R40 | `conta_codigo` = contrapartida do movimento bancário. Valor já registrado baixa a conta onde estava; não vira receita nem despesa de novo. | S12 | Helena | 16/10/2026 |
| R61 | **Provisão sempre:** todo mês, a folha e os impostos do mês ficam provisionados no fechamento; o pagamento no mês seguinte baixa a provisão. | S29, S49 | Helena | 17/10/2026 |
| R41 | Consequência de R40 e R61: folha, ISS, INSS, FGTS, IRRF, PIS e COFINS pagos no mês são do mês anterior e baixam o passivo provisionado. O repasse da Ponte do spread do mês anterior baixa a conta 1.1.03.002. | S08, S12, S29 | Helena | 16/10/2026 (rev. 17/10/2026) |
| R42 | Tarifas, aluguel, cloud, assinaturas e serviços não são provisionados: viram despesa direta do mês. | S12 | Helena | 16/10/2026 |
| R43 | A Orbe deposita tudo no Aurora. Créditos da Orbe são classificados, sem conciliação parcela a parcela neste fechamento (o resto aguarda a agenda de recebíveis). | S16 | Helena | 16/10/2026 |
| R44 | Crédito sem origem identificada **não é receita** até ser identificado (exemplo: PIX sem pagador). | S09 | Helena | 16/10/2026 |
| R73 | **Provisão do mês fora do nosso fechamento:** a contabilidade faz com a Helena. O fechamento classifica o que passou nos extratos (R40) e não gera lançamento de provisão. | S49, S29 | Helena | 17/10/2026 |

## 5. Fechamento e governança

| ID | Regra | Fonte | Aprovado por | Data |
|---|---|---|---|---|
| R62 | Taxa e condição comercial: **aprova o Comercial**, Helena registra. Regra de como fechar: **aprova a Helena**. Toda regra e toda condição registram quem aprovou e quando. | S32 | Helena | 17/10/2026 |
| R63 | Cadastro e contrato (lojista novo, taxa, CNPJ fora da planilha) **decide o Comercial**. A Bia mantém a planilha, mas não decide taxa. Pendências de cadastro e contrato têm o Comercial como responsável. | S38 | Helena | 17/10/2026 |
| R64 | Pendência: **uma por contraparte e por lojista**, com o detalhe das transações anexado (vira o rascunho de contestação). | S38 | Helena | 17/10/2026 |
| R65 | Contestação: um rascunho por contraparte (Orbe, Ponte) com as operações anexadas; **Helena revisa e envia**. Nada é enviado automaticamente. | S31 | Helena | 17/10/2026 |
| R66 | A Helena não valida a classificação conta a conta: vale o critério escrito de R40 e R42 (S12), com as premissas em `HIPOTESES.md`. | S38 | Helena | 17/10/2026 |
| R75 | **Ajuste tardio da Orbe:** vem quando há ajuste, não todo mês. **Antes** da aprovação do fechamento entra no **mês do movimento**; **depois** da aprovação entra no mês seguinte. Mesmo `id_transacao` em dois arquivos com valores diferentes: critério nosso (H31), com pendência `ORBE_LINHA_DUPLICADA` para a Helena. | S52, S02 | Helena | 17/10/2026 |
| R76 | **Fechamento parcial:** a estrutura é a mesma todo mês, mas na prática chega arquivo atrasado ou com layout mudado. Fonte ausente ou layout inesperado: **não segurar o mês inteiro**. Fecha o que não depende dela, marca o que é provisório e diz o que está bloqueado e por quê (pendência `FONTE_AUSENTE` ou `LAYOUT_INESPERADO` para a Helena). Quem libera é a Helena; taxa e cadastro o Comercial decide antes. A solução prefere avisar a quebrar sem ninguém perceber. Detalhe do que fica provisório: H32. | S53 | Helena | 17/10/2026 |
