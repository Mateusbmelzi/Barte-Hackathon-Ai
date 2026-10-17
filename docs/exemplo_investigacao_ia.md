# Exemplo de investigação com IA (execução real)

> **Exemplo de uma execução; a IA varia a cada execução; nenhum número oficial vem daqui.** Os números oficiais estão nos 6 CSVs de `saida/`. O caso (fatos, linha do tempo, ação pela regra) vem do dossiê determinístico (`saida/investigacao/dossie.json`). A causa é sugestão da IA, não verificada: quem decide é a analista.

> **Evolução da Rota (G02), v1 → v4.** Nas versões v1 e v2 do prompt a hipótese principal era "tabela antiga 2025". Desde a v3 é reajuste ou alteração de cadastro do EC na Orbe; na v4, com lista fechada de causas, vira **Reajuste sem contrato**. A aba antiga de 2025 só explica 2 das 3 faixas afetadas e aparece como possibilidade de confiança baixa. Ver `PROMPTS/MOMENTOS.md`.

- **Data da execução:** 2026-10-17 15:01:54
- **Provedor / modelo:** openrouter / anthropic/claude-sonnet-5.5 (modelo que respondeu: anthropic/claude-sonnet-5.5)
- **Prompt:** investigacao-v4
- **Competência:** 09/2026
- **Comando:** `python -m src.ia saida\investigacao\dossie.json execucoes\ia_real_5\investigacao_ia.json` (arquivo bruto em `execucoes/ia_real_5/`, fora do git)
- **Aviso fixo exibido na tela:** Sugestão da IA, não verificada. A decisão é da analista.
- **Decisão da analista (na tela):** Concordo / Discordo / Preciso verificar, com comentário obrigatório para Discordo e Preciso verificar.

## G01 — Casa do Estudante Viagens Ltda (Orbe)

**O que aconteceu**

Desde 01/09 a Orbe cobra a taxa cheia em todas as faixas; o lojista tem isenção comercial (C001).

**Linha do tempo**

| Faixa | Período | Cobrado | Contratado | Transações | Diverge |
|---|---|---|---|---|---|
| Débito | 21/08 a 21/08 | 1,49% | 1,49% | 1 | não |
| Débito | 08/09 a 30/09 | 1,49% | 0,00% | 12 | sim |
| Crédito à vista | 01/09 a 29/09 | 2,69% | 0,00% | 35 | sim |
| Crédito 2–6x | 01/09 a 30/09 | 3,19% | 0,00% | 41 | sim |
| Crédito 7–12x | 01/09 a 26/09 | 3,79% | 0,00% | 17 | sim |
| Pix | 06/09 a 29/09 | 0,89% | 0,00% | 9 | sim |
| Antecipação | 09/09 a 16/09 | 2,10% | 0,00% | 4 | sim |

**Ação pela regra** (definido pela regra, não pela IA)

Devolver ao lojista R$ 15.396,77 (sai do caixa da Tarvo — concessão comercial fora do contrato); não cobrar a Orbe. Regras: R52, R68, R74.

**Causa provável**

- **Condição não informada ao parceiro** — confiança alta
- Não existe uma pessoa responsável por avisar a Orbe das condições novas. Por isso ela cobrou certo pelo que sabia, e a isenção não chegou ao sistema dela.

*Por quê*

- Ninguém tem a função de avisar a Orbe; a Casa do Estudante não foi avisada. (S30)
- A Orbe cobrou certo pela planilha porque ninguém avisou a isenção. (S18)
- A taxa aplicada é igual à da linha 13 da planilha em 118 de 118 transações. (F6)
- A planilha não registra a isenção, que vem do acordo comercial. (F8)
- A isenção vale de 01/09/2026 a 31/12/2026, e a divergência começa no mesmo dia. (C001)

*Contra*

- Nenhum fato contrário citado.

**Outras possibilidades**

- **Concessão comercial fora do contrato** — confiança média. A isenção foi aprovada pelo Comercial, mas ficou fora do contrato registrado. Por isso a Orbe só enxergou a taxa antiga.
  - A isenção foi aprovada pelo Comercial e consta só no cadastro. (C001)
  - A Casa do Estudante é concessão do comercial fora do contrato. (S41)
  - Concessão fora do contrato não é divergência de contrato e não se cobra o parceiro. (R52)
  - A planilha tem linha única, sem mudança de vigência. (F7)

**Para confirmar**

- Conferir com o Comercial o e-mail ou documento que formalizou a isenção de setembro a dezembro.
- Verificar na tela de cadastro da Orbe, para o EC 1018325654, se há alguma isenção ou taxa zero registrada.
- Ver na planilha de taxas, linha 13, se a observação 'cliente estratégico - ver c/ comercial' tem detalhe da isenção.

**Falar com:** Comercial  
**Dado faltante:** Registro de quando o Comercial fechou a isenção e se houve qualquer pedido de cadastro à Orbe.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G02 — Rota Global Intercâmbio Ltda (Orbe)

**O que aconteceu**

Desde 12/09 a Orbe cobra +0,50 p.p. no crédito à vista, 2–6x e 7–12x; débito, Pix e antecipação estão corretos.

**Linha do tempo**

| Faixa | Período | Cobrado | Contratado | Transações | Diverge |
|---|---|---|---|---|---|
| Débito | 01/09 a 18/09 | 1,49% | 1,49% | 10 | não |
| Crédito à vista | 02/09 a 11/09 | 2,49% | 2,49% | 20 | não |
| Crédito à vista | 12/09 a 29/09 | 2,99% | 2,49% | 38 | sim |
| Crédito 2–6x | 30/08 a 11/09 | 2,99% | 2,99% | 13 | não |
| Crédito 2–6x | 12/09 a 29/09 | 3,49% | 2,99% | 31 | sim |
| Crédito 7–12x | 03/09 a 08/09 | 3,59% | 3,59% | 11 | não |
| Crédito 7–12x | 12/09 a 30/09 | 4,09% | 3,59% | 18 | sim |
| Pix | 03/09 a 30/09 | 0,89% | 0,89% | 15 | não |
| Antecipação | 09/09 a 22/09 | 2,10% | 2,10% | 3 | não |

**Ação pela regra** (definido pela regra, não pela IA)

Devolver ao lojista R$ 1.545,86 e contestar R$ 1.545,86 com a Orbe. Regras: R13, R68, R74.

**Causa provável**

- **Reajuste sem contrato** — confiança média
- A cobrança subiu de forma igual em todas as faixas de crédito a partir de 12/09, sem mudança no contrato da lojista. Isso lembra um reajuste aplicado pela Orbe por conta própria.

*Por quê*

- O contrato é linha única, vigente desde 01/01/2026, sem mudança de vigência. (F9)
- Em todas as faixas afetadas a taxa aplicada é a contratada mais 0,50 p.p. (F6)
- A diferença é constante em todas as 87 transações. (F5)
- A Rota Global confirma que o contrato não mudou este ano. (S06)
- Crédito à vista passou de 2,49% para 2,99% a partir de 12/09/2026. (V3)
- A taxa de 7–12x de 4,09% não existe em nenhuma tabela da planilha. (F8)

*Contra*

- F7: A aba 'ANTIGO 2025 - nao usar' da planilha (mesmo CNPJ) coincide com a taxa aplicada em 2 de 5 faixas com transações no período (crédito à vista 2,99%, 2–6x 3,49%); não explica 7–12x (aplicada 4,09%; aba 3,49%), nem débito (aplicada 1,49%; aba 1,69%) e Pix (aplicada 0,89%; aba 0,99%), que seguiram a taxa contratada vigente (linha 10, desde 01/01/2026).

**Outras possibilidades**

- **Tabela desatualizada no parceiro** — confiança baixa. Em duas faixas a taxa cobrada coincide com a aba antiga de 2025. Isso sugere uma tabela velha, mas ela não explica a faixa de 7–12x.
  - A aba antiga coincide com a taxa aplicada em crédito à vista e 2–6x. (F7)
  - A taxa de 7–12x aplicada não aparece em nenhuma tabela da planilha. (F8)
  - Débito, Pix e antecipação seguiram a taxa contratada no mesmo período. (F4)
  - Contra: F7 (A aba 'ANTIGO 2025 - nao usar' da planilha (mesmo CNPJ) coincide com a taxa aplicada em 2 de 5 faixas com transações no período (crédito à vista 2,99%, 2–6x…); F8 (Taxa aplicada sem correspondência na planilha (vigente, outras vigências, abas antigas ou outros lojistas) em: 7–12x 4,09%.); F4 (No mesmo período (12/09/2026 a 30/09/2026), sem divergência: débito (7), Pix (10), antecipação (2).)

**Para confirmar**

- Na tela de cadastro da Orbe, a taxa do EC 1074504011 por faixa de parcelamento e a data da última alteração.
- Se houve e-mail, aviso ou aditivo da Orbe sobre mudança de taxa por volta de 12/09/2026.
- Se o Comercial negociou ou registrou algo com a Rota Global perto dessa data, comparando com a linha 10 da planilha.
- As transações de exemplo TX88440860, TX88423647 e TX88444545 no extrato da Orbe.

**Falar com:** Orbe  
**Dado faltante:** Registro da Orbe sobre quando e por que a taxa do cadastro da lojista mudou em 12/09/2026.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G03 — Mundo Aberto (Ponte)

**O que aconteceu**

Em setembro a Ponte aplicou 1,50% (padrão) em todas as remessas; o contratado é 1,20%.

**Linha do tempo**

| Faixa | Período | Cobrado | Contratado | Transações | Diverge |
|---|---|---|---|---|---|
| SPREAD | 01/09 a 30/09 | 1,5000% | 1,2000% | 23 | sim |

**Ação pela regra** (definido pela regra, não pela IA)

Devolver ao lojista R$ 1.418,88 e contestar R$ 1.418,88 com a Ponte. Regras: R22, R68, R74.

**Causa provável**

- **Condição não informada ao parceiro** — confiança alta
- Ninguém na Tarvo tem a função de avisar a Ponte das condições novas. Por isso a corretora usou o spread padrão, como faz quando não há condição especial cadastrada.

*Por quê*

- O spread aplicado coincide com o padrão de 1,50% em 23 de 23 operações. (F5)
- A planilha registra 1,20% para o lojista, negociado em julho de 2026. (P15)
- A Mundo Aberto não foi avisada à Ponte, segundo a resposta do financeiro. (S30)
- O cadastro registra que a Ponte não foi avisada do spread de 1,20%. (C006)
- Em setembro, 100% das operações válidas do lojista divergem. (F7)
- Outros lojistas com spread diferente do padrão não tiveram nenhuma operação divergente. (F8)
- Pelo contrato, o caso é divergência e a Helena contesta com a Ponte. (S41)

*Contra*

- Nenhum fato contrário citado.

**Outras possibilidades**

- **Erro de cadastro no parceiro** — confiança baixa. Se a Ponte nunca recebeu o spread de 1,20%, o cadastro do lojista provavelmente ficou em branco ou padrão, e a corretora aplica 1,50% nesses casos.
  - Spread em branco na remessa equivale ao padrão de 1,50%. (F5)
  - Não há mudança de vigência na planilha; a divergência começa em 01/09/2026. (F6)
  - Todas as moedas das operações divergentes foram afetadas. (F3)

**Para confirmar**

- Cadastro da Mundo Aberto na Ponte: qual spread está registrado para o lojista.
- E-mails ou documentos enviados à Ponte sobre o spread de 1,20% negociado em julho.
- Operações de julho e agosto da Mundo Aberto, para ver qual spread foi aplicado antes de setembro.
- Linha 15 da planilha de taxas e a observação 'spread negociado em jul/26'.

**Falar com:** Comercial  
**Dado faltante:** Registro de quando e se o Comercial avisou a Ponte do spread de 1,20%, e o spread aplicado nas remessas antes de setembro.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum

## G04 — Escola Bridge de Idiomas Ltda (Orbe)

**O que aconteceu**

De 15/09 a 18/09 a Orbe cobrou 2,59% no crédito à vista; o contratado desde 15/09 é 2,19%; débito, 2–6x, 7–12x e Pix estão corretos.

**Linha do tempo**

| Faixa | Período | Cobrado | Contratado | Transações | Diverge |
|---|---|---|---|---|---|
| Débito | 01/09 a 29/09 | 1,49% | 1,49% | 15 | não |
| Crédito à vista | 01/09 a 13/09 | 2,59% | 2,59% | 8 | não |
| Crédito à vista | 15/09 a 18/09 | 2,59% | 2,19% | 5 | sim |
| Crédito à vista | 23/09 a 30/09 | 2,19% | 2,19% | 9 | não |
| Crédito 2–6x | 01/09 a 29/09 | 3,19% | 3,19% | 42 | não |
| Crédito 7–12x | 01/09 a 27/09 | 3,79% | 3,79% | 17 | não |
| Pix | 01/09 a 30/09 | 0,89% | 0,89% | 13 | não |

**Ação pela regra** (definido pela regra, não pela IA)

Devolver ao lojista R$ 29,94 e contestar R$ 29,94 com a Orbe. Regras: R13, R68, R74.

**Causa provável**

- **Vigência aplicada com atraso** — confiança média
- A nova taxa valia desde 15/09, mas o cadastro da Orbe só mudou depois de 18/09. Nesse intervalo, a taxa antiga seguiu sendo cobrada.

*Por quê*

- A taxa cobrada de 15/09 a 18/09 é igual à da linha anterior da planilha. (F6)
- A planilha mudou de vigência em 15/09 e a divergência começa no mesmo dia. (F7)
- Nesse período, todas as 5 transações de crédito à vista divergem. (F8)
- A Orbe cobrou 2,59% de 15/09 a 18/09, contra 2,19% contratado. (V3)
- A partir de 23/09, a Orbe já cobra 2,19%. (V4)
- A linha 7 da planilha fixa o crédito à vista em 2,19% desde 15/09. (P7)
- A Bridge foi avisada só alguns dias depois de 15/09. (S30)

*Contra*

- Nenhum fato contrário citado.

**Outras possibilidades**

- **Condição não informada ao parceiro** — confiança média. Como ninguém tem a função de avisar a Orbe, o aviso saiu com atraso. Até lá, a Orbe seguiu com a taxa antiga.
  - Ninguém tem a função de avisar a Orbe das condições novas. (S30)
  - O aditivo vale desde 15/09, e o aviso atrasado é problema de processo. (R68)
  - Só o crédito à vista mudou na planilha, e só ele divergiu. (F3)

**Para confirmar**

- E-mail ou comunicado do Comercial à Orbe com a nova taxa de crédito à vista e a data de envio.
- Tela de cadastro do EC 1075624862 na Orbe, com a data em que a taxa de 2,19% passou a constar.
- Aditivo assinado com a Bridge, com a data de vigência de 15/09/2026.
- Transações de crédito à vista entre 19/09 e 22/09, que não aparecem na rota, para ver quando a taxa mudou.

**Falar com:** Orbe  
**Dado faltante:** Data em que a Orbe atualizou a taxa de crédito à vista no cadastro do EC e data do aviso a ela.  
**Hipóteses descartadas pelo código:** 0  
**Ajustes do código:** nenhum
