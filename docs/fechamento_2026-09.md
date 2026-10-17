# Registro do fechamento de setembro/2026

Este arquivo guarda **o que aconteceu** no fechamento de setembro/2026: as ocorrências do mês. Elas não são regra (as regras gerais estão em `REGRAS_DE_NEGOCIO.md`) nem condição de cliente (estas estão em `cadastro/condicoes_comerciais.csv`, IDs C###). Serve de histórico para o fechamento de outubro: se um caso parecido aparecer, aqui está como foi tratado e quem decidiu.

Valores lidos de `saida/*.csv` do fechamento de 17/10/2026 (com os ajustes tardios do arquivo 06 já somados). Fontes S## em `docs/00_slack_respostas_financeiro.md`. Status: situação no momento do fechamento; a decisão das pendências é da Helena (e do Comercial quando indicado).

## Índice

| # | Ocorrência | Valor | Regra | Condição | Pendência | Status |
|---|---|---|---|---|---|---|
| 1 | Rota Global cobrada +0,50 p.p. | R$ 1.545,86 | R13, R50, R60, R74 | planilha de taxas (contrato inalterado) | PEN-0003 | Aberta: contestar a Orbe |
| 2 | Bridge Idiomas, vigência nova não aplicada | R$ 29,94 | R13, R50, R60, R68, R74 | planilha de taxas (duas linhas de vigência) | PEN-0002 | Aberta: contestar a Orbe |
| 3 | Casa do Estudante, isenção não comunicada | R$ 15.396,77 | R52, R68, R72, R11, R31, R74 | C001 | PEN-0001, PEN-0004 | Aberta: Tarvo devolve ao lojista |
| 4 | Mundo Aberto, spread de remessa 1,50% x 1,20% | R$ 1.418,88 | R22, R50, R60, R20, R74 | C006 (nota); spread de 1,20% na planilha | PEN-0007, PEN-0008 | Aberta: contestar a Ponte |
| 5 | Atlas Idiomas sem contrato | R$ 7.876,05 (referência) | R15, R54, R55, R59 | C005 | PEN-0005, PEN-0006 | Aberta: Comercial define a taxa |
| 6 | Operação duplicada PC-0926-0162 | R$ 821,88 | R24 | nenhuma | PEN-0013 | Aberta: pedir correção à Ponte |
| 7 | Quatro spreads negativos | −R$ 1.834,05 (realizado) | R23, R53, R69, R21 | planilha de taxas (spread padrão 1,5% pela R21 quando em branco) | PEN-0009 a PEN-0012 | Aberta: contestar a Ponte |
| 8 | PIX R$ 7.350,00 sem origem | R$ 7.350,00 | R44 | nenhuma | PEN-0015 | Aberta: identificar pagador |
| 9 | PIX R$ 18.240,00 da Ponte Aérea Estudantil | R$ 18.240,00 | R40 (conta: H10, H21) | nenhuma | PEN-0018 | Acompanhamento: conferir em outubro |
| 10 | Devolução PIX R$ 12.400,00 (Mundo Aberto) | R$ 12.400,00 | R40 (conta: H11) | nenhuma | PEN-0016 | Aberta: confirmar o motivo |
| 11 | Transferência R$ 300.000,00 em trânsito | R$ 300.000,00 | R40 (conta: H13) | nenhuma | PEN-0017 | Aberta: conferir no extrato de outubro |
| 12 | Pagamentos de agosto quitados em setembro | R$ 61.884,12 (repasse Ponte) | R41, R61, R73 | nenhuma | PEN-0014 | Aberta: conferir o TED |
| 13 | Ajustes tardios da Orbe (arquivo 06) | −R$ 3.304,39 na comissão | R75, R11, R12, R01 | nenhuma | nenhuma | Fechada: incorporada |
| 14 | ECs sem código na planilha | 3 ECs | R63 | C002, C003, C004 | nenhuma | Fechada: resolvida pelo de-para |

Valor a devolver ao lojista segue R74 (o que o parceiro descontou de fato menos a comissão contratada). A lista `divergencias_taxa.csv` usa a fórmula (bruto × diferença de taxa) e difere por centavos, por truncamento da Orbe (R02).

## 1. Rota Global cobrada +0,50 p.p.

- **O que aconteceu:** desde 12/09 a Orbe cobrou da Rota Global (EC 1074504011) 0,50 p.p. acima da taxa contratada. O contrato não mudou em 2026 (S06).
- **Valor:** R$ 1.545,86 a devolver ao lojista e recuperar da Orbe (R74); fórmula da lista R$ 1.546,28; 87 transações.
- **Regra aplicada:** R13, R50, R60, R74. É divergência de contrato (R68).
- **Condição usada:** a taxa vigente da planilha de taxas, sem exceção de cadastro.
- **Pendência:** PEN-0003 (Helena).
- **Status:** aberta. Helena contesta a Orbe e o lojista é ressarcido. Causa raiz da cobrança errada: não identificada pelos dados (a IA de investigação sugere hipóteses, a analista decide).

## 2. Bridge Idiomas, vigência nova não aplicada

- **O que aconteceu:** a Bridge (EC 1075624862) passou de 2,59% para 2,19% no crédito à vista a partir de 15/09 (duas linhas na planilha). A Orbe só foi avisada dias depois (S30) e cobrou a taxa antiga em 5 vendas à vista de 15 a 18/09; ajustou depois de avisada.
- **Valor:** R$ 29,94 a devolver ao lojista e recuperar da Orbe; fórmula da lista R$ 29,95; 5 transações.
- **Regra aplicada:** R13, R50, R60, R68 (o contrato decide, não o aviso), R74.
- **Condição usada:** as duas linhas de vigência da planilha de taxas (sem condição própria no cadastro).
- **Pendência:** PEN-0002 (Helena).
- **Status:** aberta. Aviso atrasado é problema de processo e não muda quem deve.

## 3. Casa do Estudante, isenção não comunicada

- **O que aconteceu:** o Comercial deu à Casa do Estudante (EC 1018325654) taxa zero no checkout (MDR e antecipação) de set a dez/2026, **fora do contrato**. A Orbe não foi avisada (S18, S30) e cobrou a taxa cheia. Um estorno (TX88445133) de venda de 21/08 abate à taxa de agosto (R11); com isso a Casa fecha o mês em −R$ 5,50 e não emite nota.
- **Valor:** R$ 15.396,77 a devolver ao lojista (R74); fórmula da lista R$ 15.397,42; 118 transações. Saldo do mês: −R$ 5,50.
- **Regra aplicada:** R52 e R68 (concessão fora do contrato: não se cobra a Orbe, o custo é da Tarvo), R72 (isenção vale para venda a partir de 01/09 e, na antecipação, pela data da antecipação), R11, R31, R74.
- **Condição usada:** C001 (isenção da Casa, set a dez/2026; S07, S18, S47).
- **Pendência:** PEN-0001 (devolução ao lojista, Helena + Comercial) e PEN-0004 (saldo de −R$ 5,50 sem nota, Helena).
- **Status:** aberta. Decisão da Helena sobre pagar o lojista; nada a recuperar da Orbe. Aviso à Orbe é o próximo passo de processo.

## 4. Mundo Aberto, spread de remessa 1,50% contra 1,20%

- **O que aconteceu:** a Ponte aplicou spread de cerca de 1,50% em 23 operações de Mundo Aberto (CNPJ 17.217.888/0001-11), com contrato de 1,20% negociado em julho/2026. A Ponte não foi avisada (S30), mas a Helena tratou como divergência e vai contestar (S05).
- **Valor:** R$ 1.418,88 a devolver ao lojista e recuperar da Ponte; fórmula da lista R$ 1.418,85; 23 operações. O excesso está dentro da nota de remessa: R$ 709,50 (metade da Tarvo).
- **Regra aplicada:** R22, R50, R60, R74; R20 e R56 para o excesso na nota (ajuste só no mês em que a Ponte devolver).
- **Condição usada:** o spread de 1,20% está na planilha de taxas do cliente (linha 15, desde jul/26), não no cadastro. O cadastro tem a C006 (NOTA_PENDENCIA), a observação de fronteira (S05/S30: a Ponte não foi avisada, mas a Helena trata como divergência), que entra no motivo da pendência.
- **Pendência:** PEN-0007 (divergência) e PEN-0008 (excesso na nota), Helena.
- **Status:** aberta. Contestar a Ponte por e-mail (R65, Helena revisa e envia).

## 5. Atlas Idiomas sem contrato

- **O que aconteceu:** a Atlas (EC 1076801732, CNPJ 39.566.044/0001-19 pela aba 2025, que só identifica o lojista) transacionou desde 10/09 sem contrato vigente e com taxa desconhecida. Lojista novo, pico de antecipação acumulada líquida de reversões de R$ 183.581,24 em 24/09, acima das vendas acumuladas até a data (R$ 109.719,61). Única a acender o alerta em setembro (H28).
- **Valor:** R$ 7.876,05 cobrados pela Orbe em 57 transações (bruto R$ 262.138,61), só referência. Fora de comissões e notas.
- **Regra aplicada:** R15 (não faturar), R59 (o repasse ao lojista continua), R54 (alerta de antecipação), R55 (quando a taxa for confirmada, vale retroativa e entra na nota do mês seguinte).
- **Condição usada:** C005 (Atlas bloqueada até o Comercial confirmar a taxa).
- **Pendência:** PEN-0005 (cadastro/contrato, Comercial) e PEN-0006 (alerta de antecipação, Helena + Comercial).
- **Status:** aberta. O Comercial confirma a taxa; em outubro as linhas pendentes de setembro entram na nota.

## 6. Operação duplicada PC-0926-0162

- **O que aconteceu:** a Ponte repetiu a operação PC-0926-0162 no relatório (linha 77, observação "reprocessada").
- **Valor:** R$ 821,88 (Spread R$ da linha repetida).
- **Regra aplicada:** R24 (conta uma vez e entra na lista de correção da Ponte).
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0013 (Helena).
- **Status:** aberta. Pedir à Ponte que corrija o relatório (S15).

## 7. Quatro spreads negativos

- **O que aconteceu:** quatro operações com trava D-1 vencida e spread negativo: PC-0926-0210 (Ponte Aérea Estudantil), PC-0926-0326 (Canguru), PC-0926-0491 (Dublin Hub) e PC-0926-0545 (Novo Horizonte Intercambio). O lojista não pagou a mais; o prejuízo é da Tarvo com a Ponte.
- **Valor:** −R$ 1.834,05 de spread realizado; −R$ 3.565,98 de diferença até o spread contratado (o que se pede à Ponte). Por operação, diferença até o contratado: −R$ 1.351,87, −R$ 1.001,29, −R$ 574,91 e −R$ 637,91.
- **Regra aplicada:** R23 (fora da comissão e da nota), R53 (contestação, outra natureza), R69 (dois valores rotulados).
- **Condição usada:** nenhuma do cadastro; o spread contratado de cada lojista vem da planilha de taxas (R21: 1,5% quando em branco).
- **Pendência:** PEN-0009, PEN-0010, PEN-0011 e PEN-0012 (Helena).
- **Status:** abertas. Helena contesta a Ponte; o retorno chega como ajuste no relatório do mês seguinte (R56, R67).

## 8. PIX de R$ 7.350,00 sem origem

- **O que aconteceu:** PIX de R$ 7.350,00 recebido no Aurora do CNPJ 38.686.002/0001-80, sem identificação do pagador (S09).
- **Valor:** R$ 7.350,00.
- **Regra aplicada:** R44 (não é receita até ser identificado). Conta provisória 1.1.09.002 (H12).
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0015 (Helena).
- **Status:** aberta. Identificar o pagador e reclassificar.

## 9. PIX de R$ 18.240,00 da Ponte Aérea Estudantil

- **O que aconteceu:** PIX de "PONTE AEREA ESTUDANTIL L" no Meridiano (MRD2026090425, 17/09), sem operação da Ponte no mês que o explique. A Helena confirmou: é o lojista Ponte Aérea Estudantil, sem relação com a Ponte Câmbio, adiantando dinheiro de uma remessa que sai em outubro (S22).
- **Valor:** R$ 18.240,00.
- **Regra aplicada:** R40, com a conta 2.1.02.001 (recurso de lojista para remessa a liquidar) em H10 e H21.
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0018 (acompanhamento, Helena).
- **Status:** acompanhamento. Em outubro a operação deve aparecer no relatório da Ponte; se não aparecer, confirmar com o lojista (devolver ou reclassificar).

## 10. Devolução de PIX de R$ 12.400,00 (Mundo Aberto)

- **O que aconteceu:** um PIX de repasse ao lojista Mundo Aberto voltou (devolução) por motivo desconhecido (S09, S28). Conta 2.1.01.001 (H11): o repasse continua a pagar.
- **Valor:** R$ 12.400,00.
- **Regra aplicada:** R40.
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0016 (Helena).
- **Status:** aberta. Confirmar o motivo e se deve repagar em outubro.

## 11. Transferência de R$ 300.000,00 em trânsito

- **O que aconteceu:** transferência de R$ 300.000,00 do Aurora em 30/09 que só cai no Meridiano em 01/10 (S09). Mantida em 1.1.09.001 (H13).
- **Valor:** R$ 300.000,00 (−R$ 300.000,00 no extrato de saída).
- **Regra aplicada:** R40.
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0017 (Helena).
- **Status:** aberta. Conferir a entrada no extrato do Meridiano de outubro.

## 12. Pagamentos de agosto quitados em setembro

- **O que aconteceu:** folha e tributos pagos em setembro são de agosto e baixam o passivo provisionado. O repasse da Ponte de 04/09 (MRD2026090132) baixa a conta 1.1.03.002. A provisão de setembro em si não é feita pelo nosso fechamento (feita pela contabilidade com a Helena).
- **Valor:** R$ 61.884,12 (repasse da Ponte). Em 06/10 a Ponte informa o repasse dos 50% de setembro; a nota é de R$ 39.543,45 e 50% do total do relatório é R$ 39.036,80, diferença de R$ 506,65.
- **Regra aplicada:** R41, R61, R73; R26 para a conferência do TED.
- **Condição usada:** nenhuma.
- **Pendência:** PEN-0014 (conferir o repasse da Ponte, Helena).
- **Status:** aberta. Conferir o TED quando cair, sem presumir desconto.

## 13. Ajustes tardios da Orbe (arquivo 06)

- **O que aconteceu:** em 17/10, depois de a primeira versão estar pronta, a Orbe mandou 14 ajustes com `data_movimento` 30/09: 10 estornos, 3 reversões de antecipação e 1 venda (Kiwi). Nenhuma duplicata, nenhuma taxa diferente da contratada.
- **Valor:** −R$ 3.304,39 na comissão de checkout (R$ 207.039,73 para R$ 203.735,34), quase tudo da Oxford (−R$ 2.232,19, por 2 reversões de antecipação) e da Maple (−R$ 845,01). Notas de checkout: R$ 207.045,23 para R$ 203.740,84. Divergências e pendências não mudaram.
- **Regra aplicada:** R75 (antes da aprovação do fechamento entra no mês do movimento), R11, R12, R01.
- **Condição usada:** nenhuma. A venda nova da Kiwi só usa o de-para C004 para identificar o EC.
- **Pendência:** nenhuma obrigatória.
- **Status:** fechada. Para outubro: a Orbe manda ajuste quando há; o programa lê todo arquivo `orbe` da pasta e o `rastro.csv` diz de qual arquivo veio cada linha. Análise completa em `docs/05_ajustes_tardios.md` e `docs/06_validacao_ajustes.md`.

## 14. ECs sem código na planilha

- **O que aconteceu:** três ECs da Orbe não tinham código na planilha de taxas e foram ligados ao lojista pelo de-para do Comercial (S03): 1043300981 = Novo Horizonte Intercâmbio, 1043396662 = Horizonte Viagens e Turismo (empresas diferentes) e 1038867654 = Kiwi Experience.
- **Valor:** não se aplica (afeta a identificação do lojista, não um valor).
- **Regra aplicada:** R63 (cadastro decide o Comercial).
- **Condição usada:** C002, C003 e C004.
- **Pendência:** nenhuma.
- **Status:** fechada. Em outubro, EC novo sem código na planilha vira condição nova no cadastro (aba Clientes).
