# Exemplo de investigação com IA (execução real)

> **Exemplo de uma execução; a IA varia a cada execução; nenhum número oficial vem daqui.** Os números oficiais estão nos 6 CSVs de `saida/`. Os fatos vêm do dossiê determinístico (`saida/investigacao/dossie.json`). As hipóteses são sugestões da IA, não verificadas: quem decide é a analista.

> Versão do prompt v3; nas versões anteriores a hipótese principal da Rota foi diferente — ver `PROMPTS/MOMENTOS.md`.

- **Data da execução:** 2026-10-17 13:25:20
- **Provedor:** openrouter
- **Modelo pedido:** anthropic/claude-sonnet-5.5 · **modelo que respondeu:** anthropic/claude-sonnet-5.5
- **Versão do prompt:** investigacao-v3
- **Competência:** 09/2026
- **Comando:** `python -m src.ia saida\investigacao\dossie.json execucoes\ia_real_4\investigacao_ia.json` (arquivo bruto em `execucoes/ia_real_4/`, fora do git)
- **Aviso fixo exibido na tela:** Sugestão da IA, não verificada. A decisão é da analista.

## G01 — Casa do Estudante Viagens Ltda (Orbe, isenção não informada ao parceiro)

**Fatos-chave do dossiê**

- **F1** 118 transações divergentes, líquido R$ 15.397,42 (inclui 1 estorno(s) de vendas divergentes, com sinal negativo). A devolver ao lojista: R$ 15.397,42; a recuperar da Orbe: R$ 0,00.
- **F6** Taxa aplicada = taxa da linha 13 da planilha (desde 01/01/2026), a cobrada antes da isenção, em 118 de 118 transações: débito 1,49%, crédito à vista 2,69%, 2–6x 3,19%, 7–12x 3,79%, Pix 0,89%, antecipação 2,10%.
- **F8** A planilha de taxas não registra a isenção; ela vem do acordo comercial informado pelo financeiro (S07), válido de 01/09/2026 a 31/12/2026; a divergência começa no mesmo dia.
- **F9** Entre 01/09/2026 e 30/09/2026, 118 de 118 transações das faixas afetadas divergem (100%); somando todas as faixas, 118 de 118 (100%).

**Resumo da IA:** Em setembro de 2026, desde 01/09/2026, a Orbe cobrou da Casa do Estudante Viagens a taxa da planilha em 118 transações do checkout, apesar da isenção acordada, num líquido de R$ 15.397,42.

**Hipóteses**

1. A isenção de setembro a dezembro foi fechada pelo Comercial e não foi comunicada à Orbe, então o EC seguiu com as taxas da linha 13 da planilha. A Orbe cobrou certo pelo que sabia. — *fatos citados:* F6, F7, F8, F9, S07, S18, S30 · *confiança:* alta
2. O aviso pode ter sido enviado, mas a Orbe não atualizou o cadastro do EC. Isso não explica o que está nos fatos, pois a S30 diz que a Casa do Estudante não foi avisada. — *fatos citados:* F6, F8 · *contra:* S30, S18 · *confiança:* baixa

**Conferir**

- E-mail ou registro do Comercial com a data em que a isenção foi fechada e se algo foi enviado à Orbe.
- Taxas cadastradas para o EC 1018325654 na Orbe, para ver se estão iguais à linha 13 da planilha.
- Termo do acordo comercial C001 para confirmar vigência de 01/09/2026 a 31/12/2026 e as faixas isentas (MDR e antecipação).
- Transações de exemplo AN88445802, AN88445486 e TX88419350 para validar o detalhe por transação, incluindo o estorno.

**Falar com:** Comercial  
**Dado faltante:** Registro de quando o Comercial fechou a isenção e se houve qualquer comunicação à Orbe sobre ela.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G02 — Rota Global Intercâmbio Ltda (Orbe, divergência de contrato)

**Fatos-chave do dossiê**

- **F2** Primeira transação divergente em 12/09/2026 e última em 30/09/2026 (19 dia(s) corrido(s)), pela data da venda (no estorno, a da venda original).
- **F3** Faixas afetadas: crédito à vista (38), 2–6x (31), 7–12x (18).
- **F6** Em todas as faixas afetadas, a taxa aplicada = contratada +0,50 p.p.: crédito à vista 2,49% → 2,99%; 2–6x 2,99% → 3,49%; 7–12x 3,59% → 4,09%.
- **F7** A aba 'ANTIGO 2025 - nao usar' da planilha (mesmo CNPJ) coincide com a taxa aplicada em 2 de 5 faixas com transações no período (crédito à vista 2,99%, 2–6x 3,49%); não explica 7–12x (aplicada 4,09%; aba 3,49%), nem débito (aplicada 1,49%; aba 1,69%) e Pix (aplicada 0,89%; aba 0,99%), que seguiram a taxa contratada vigente (linha 10, desde 01/01/2026).

**Resumo da IA:** Desde 12/09/2026 até 30/09/2026, a Orbe aplicou taxa 0,50 p.p. acima da contratada em 87 transações de crédito da Rota Global Intercâmbio, líquido de R$ 1.546,28.

**Hipóteses**

1. A Orbe passou a aplicar, a partir de 12/09, um acréscimo uniforme nas faixas de crédito do EC, por mudança de cadastro ou de tabela no lado dela. Débito, Pix e antecipação seguiram a taxa contratada. — *fatos citados:* F3, F4, F5, F6, F9, F10, F11, S06 · *confiança:* média
2. Tabela antiga de 2025 reaplicada ao EC no cadastro da Orbe. Só explicaria crédito à vista e 2–6x. — *fatos citados:* F7, F6 · *contra:* F7, F8 · *confiança:* baixa

**Conferir**

- Taxas cadastradas hoje no EC 1074504011 na Orbe, por faixa, e a data da última alteração.
- E-mails ou tickets com a Orbe sobre mudança de taxa ou de cadastro do EC a partir de 12/09/2026.
- Se a taxa de 7–12x de 4,09% existe em alguma tabela ou campanha da Orbe, já que não consta na planilha.
- Transações TX88440860, TX88423647 e TX88444545 no relatório da Orbe, com a taxa aplicada em cada uma.

**Falar com:** Orbe  
**Dado faltante:** Histórico de alterações das taxas cadastradas no EC 1074504011 na Orbe, com datas, para ver se algo mudou em 12/09/2026.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G03 — Mundo Aberto (Ponte, divergência de contrato)

**Fatos-chave do dossiê**

- **F1** 23 operações com spread acima do contratado; valor cheio pago a mais pelo lojista R$ 1.418,85. A devolver ao lojista: R$ 1.418,85; a recuperar da Ponte: R$ 1.418,85.
- **F4** Diferença variável de +0,2991 p.p. a +0,3009 p.p. sobre o spread contratado (1,20%).
- **F5** Spread aplicado de 1,4991% a 1,5009%: coincide com o spread padrão de 1,50% (R21) dentro da tolerância de 0,01 p.p. (H06) em 23 de 23 operações; contratado 1,20%.
- **F8** No mês, outros 4 lojista(s) com spread contratado diferente do padrão (Nórdica Educação Internacional Ltda 1,25%, EduAbroad 1,30%, Lisboa Cursos e Viagens Ltda 1,60%, Novo Horizonte Intercambio 1,40%) tiveram 60 operações válidas, nenhuma divergente.

**Resumo da IA:** Nas remessas da Mundo Aberto, de 01/09/2026 a 30/09/2026, a Ponte aplicou spread de 1,4991% a 1,5009% em vez dos 1,20% contratados em 23 operações, com R$ 1.418,85 pagos a mais pelo lojista.

**Hipóteses**

1. A Ponte não foi avisada do spread de 1,20% negociado em julho e aplicou o spread padrão de 1,50% em todas as remessas do lojista. — *fatos citados:* F5, F7, F6, F8, S30, S05 · *confiança:* alta
2. O cadastro da Ponte pode ter sido feito ou atualizado com o spread em branco ou como padrão, em vez de 1,20%, e o spread negociado em julho nunca entrou nele. — *fatos citados:* F5, F6, F7, F4 · *contra:* F8 · *confiança:* baixa

**Conferir**

- E-mails ou comunicados do Comercial à Ponte sobre o spread de 1,20% da Mundo Aberto, com data de envio.
- Cadastro do lojista na Ponte: qual spread consta como vigente em setembro.
- Comprovantes de fechamento de câmbio de algumas operações de exemplo (PC-0926-0434, PC-0926-0373, PC-0926-0566) para ver o spread aplicado.
- Data e registro do fechamento do spread negociado em julho junto ao Comercial.

**Falar com:** Comercial  
**Dado faltante:** Registro de que o Comercial informou (ou não) o spread de 1,20% à Ponte, e qual spread consta no cadastro da Ponte para a Mundo Aberto.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G04 — Escola Bridge de Idiomas Ltda (Orbe, divergência de contrato)

**Fatos-chave do dossiê**

- **F2** Primeira transação divergente em 15/09/2026 e última em 18/09/2026 (4 dia(s) corrido(s)), pela data da venda (no estorno, a da venda original).
- **F5** Diferença constante de +0,40 p.p. sobre a taxa contratada em todas as 5 transações.
- **F6** Taxa aplicada = vigência anterior do mesmo lojista na planilha (linha 6, até 14/09/2026) em: crédito à vista 2,59%; a vigente no período (linha 7) é crédito à vista 2,19%.
- **F7** Planilha: linha 6 até 14/09/2026; linha 7 desde 15/09/2026. Mudança de vigência em 15/09/2026; a divergência começa no mesmo dia (15/09/2026) e termina em 18/09/2026.

**Resumo da IA:** Na Escola Bridge de Idiomas, de 15/09/2026 a 18/09/2026, a Orbe aplicou crédito à vista de 2,59% em 5 transações, acima do 2,19% contratado desde 15/09/2026, com líquido de R$ 29,95.

**Hipóteses**

1. A Orbe manteve no cadastro a taxa antiga de crédito à vista (2,59%) nos primeiros dias após a renegociação, porque a atualização só chegou depois de 15/09. Isso é consistente com o aviso tardio à Orbe e com a taxa aplicada igual à da linha 6. — *fatos citados:* F5, F6, F7, F8, S30 · *confiança:* média
2. A Orbe recebeu o aviso e atualizou o cadastro depois de 18/09/2026, e as vendas feitas até essa data usaram a tabela anterior. Isso explicaria por que não há divergência depois de 18/09/2026. — *fatos citados:* F2, F9, F7 · *contra:* S30 · *confiança:* baixa

**Conferir**

- E-mail ou protocolo em que o Comercial pediu à Orbe a mudança do crédito à vista da Bridge, com a data de envio.
- Taxa de crédito à vista cadastrada no EC 1075624862 na Orbe, com a data da última alteração.
- Planilha de taxas, linhas 6 e 7, para confirmar a vigência do crédito à vista de 2,19% desde 15/09/2026.
- Extrato das 5 transações divergentes (por exemplo TX88428053 e TX88431123) para ver a taxa aplicada em cada uma.

**Falar com:** Orbe  
**Dado faltante:** Data em que a Orbe foi avisada e passou a aplicar o crédito à vista de 2,19% no EC da Bridge.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum
