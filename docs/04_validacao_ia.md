# 04 — Validação independente: dossiê de investigação e IA (Fase 4)

**Auditor:** agente independente · **Data:** 17/10/2026 · **Competência:** 09/2026
**Escopo:** `saida/investigacao/dossie.json` (4 grupos), `saida/divergencias_taxa.csv`, `saida/pendencias.csv`, Fase 0, execução real `execucoes/ia_real_1/investigacao_ia.json`, segurança da chave e os 6 CSVs oficiais.

**Método.** Os scripts do auditor não importam `src/`: leem direto os arquivos brutos da raiz (CSV da Orbe, as duas abas da planilha `02_tabela_taxas_contratadas.xlsx` e o anexo `PonteCambio_Relatorio_TARVO_092026.xlsx` extraído do `.eml`). Depois recalculam cada fato. Nenhuma chamada de IA foi feita e o `.env` não foi lido. Os scripts ficam no scratchpad da sessão (`auditoria_ia/audit_orbe.py`, `audit_ponte.py`).

Regras usadas no recálculo: a divergência de checkout é o bruto × (taxa aplicada − contratada), arredondado half-up por linha. No estorno vale a data da venda original. A Casa tem taxa zero de 01/09 a 31/12/2026 (CC01). A divergência de remessa é (spread aplicado − contratado) × PTAX × valor em moeda (R22), com tolerância de 0,01 p.p. (H06). Operações duplicadas contam uma vez e spreads negativos ficam fora.

## 1. Resultado

| # | Verificação | Resultado |
|---|---|---|
| 1.1 | G01 Casa: 118 transações, R$ 15.397,42 (1 estorno), de 01/09 a 30/09 (30 dias), faixas deb 12 / à vista 35 / 2–6x 41 / 7–12x 17 / Pix 9 / antecipação 4, nenhuma faixa sem divergência, diferença = taxa cheia por faixa, linha 13 em 118/118, 1 transação fora do período | OK |
| 1.2 | G02 Rota: 87 transações, R$ 1.546,28 (4 estornos), de 12/09 a 30/09 (19 dias), à vista 38 / 2–6x 31 / 7–12x 18; sem divergência no período: débito 7 / Pix 10 / antecipação 2; +0,50 p.p. constante; 87/106 = 82,1%; 53 antes | OK |
| 1.3 | G02 coincidências: aba 2025 = 2,99 à vista e 3,49 parcelado (bate em à vista e 2–6x); 7–12x aplicada 4,09 contra 3,49 da aba; 4,09 não existe em nenhuma linha nem aba da planilha | OK nos números, enganoso por omissão (achado M1) |
| 1.4 | G04 Bridge: 5 transações, R$ 29,95, de 15/09 a 18/09 (4 dias), só à vista, +0,40 p.p.; aplicada 2,59 = linha 6 (até 14/09), vigente 2,19 (linha 7, desde 15/09); no período sem divergência: deb 1 / 2–6x 1 / 7–12x 3 / Pix 2; 5/12 = 41,7%; fora do período 55 antes e 40 depois | OK |
| 1.5 | G03 Mundo Aberto: 23 operações válidas, R$ 1.418,85, de 01/09 a 30/09; AUD 8 / CAD 4 / EUR 1 / GBP 2 / NZD 3 / USD 5; spread aplicado de 1,4991% a 1,5009% (dif. +0,2991 a +0,3009 p.p.); 23/23 dentro de 0,01 p.p. de 1,50%; outros 4 lojistas com spread negociado (Nórdica 1,25 / EduAbroad 1,30 / Lisboa 1,60 / Novo Horizonte 1,40), 60 operações e nenhuma divergente | OK |
| 1.6 | IDs de exemplo e extremos (primeira e última transação de cada grupo) | OK |
| 2 | Dossiê × `divergencias_taxa.csv`: quantidade, total e datas por lojista iguais; natureza e cobrar_parceiro (Casa ISENCAO_NAO_INFORMADA/N; Rota, Bridge e Mundo Aberto CONTRATO/S); devolver/recuperar iguais aos de PEN-0001/02/03/07 | OK |
| 3.1 | Casa com natureza ISENCAO_NAO_INFORMADA, cobrar_parceiro N; PEN-0001 diz que "NÃO entra na cobrança da Orbe", quem decide: Helena / Comercial | OK |
| 3.2 | Pendências de contrato dizem "Devolver ao lojista R$ X; recuperar do parceiro R$ X" (PEN-0002/03/07) | OK |
| 3.3 | Spreads negativos: 1 pendência por lojista (PEN-0009 a 0012) | OK (cada lojista tem 1 operação, então o agrupamento não é exercitado com mais de uma) |
| 3.4 | Cadastro e contrato: quem decide é o Comercial (PEN-0005) | OK |
| 3.5 | PIX R$ 18.240,00 = ACOMPANHAR_REMESSA_FUTURA (PEN-0018) | OK |
| 3.6 | Comissão checkout 207.039,73 · notas checkout 207.045,23 (20) · comissão e nota remessa 39.543,45 | OK |
| 3.7 | Rastro fecha: a soma de `rastro.csv` por id_saida é igual ao valor de cada linha de comissões, notas, divergências e pendências; todo lançamento tem rastro | OK (0 diferenças) |
| 4.1 | IA: todos os `fatos_citados` existem no grupo (8 hipóteses) | OK |
| 4.2 | IA: nenhum número ou data fora do dossiê (varredura por regex nos textos) | OK |
| 4.3 | IA: nenhuma hipótese contradiz um fato | FALHA: G02 H1 (M2), G03 H2 (B2) |
| 4.4 | `investigacao_ia.json` não contém "sk-or-" nem "sk-ant-" | OK |
| 5.1 | `.env` está no `.gitignore` (linha 12), não é rastreado e aparece como ignorado | OK |
| 5.2 | `git grep "sk-or-\|sk-ant-"` nos arquivos versionados e no histórico: nada. Nos novos não rastreados, só textos de exemplo (`.env.example` "sk-or-...", `src/ia.py` prefixo, `tests/test_ia.py` "sk-or-v1-CHAVE-FALSA", "sk-ant-normal") | OK |
| 6.1 | `python -m src.fechamento` numa cópia sem `.env`, `.git` e `execucoes/`, com `saida/` apagada antes: os 6 CSVs ficaram idênticos byte a byte (`cmp`), e `dossie.json`/`dossie.md` também, até esta data | OK |
| 6.2 | `python -m pytest -q` na pasta real: 90 testes passaram, `saida/` não foi alterada | OK |

## 2. Achados

### CRÍTICO
Nenhum. Não há valor errado, chave exposta nem CSV oficial alterado.

### MÉDIO

**M1. G02 F6 omite a evidência que refuta a "tabela 2025".**
- *O que acontece:* F6 compara a aba 2025 só com as faixas afetadas. A aba 2025 tem débito 1,69 e Pix 0,99 para a Rota, mas a Orbe aplicou 1,49 e 0,89 no período (F4: sem divergência). Se a Orbe tivesse voltado à tabela 2025, débito e Pix também divergiriam, e o 7–12x seria 3,49, abaixo do contrato. Além disso, a aba 2025 é uma tabela genérica, igual para os 12 lojistas, e não uma condição própria da Rota, como "mesmo CNPJ" dá a entender. A coincidência em à vista e 2–6x é aritmética: o contrato de 2026 nessas faixas é exatamente o de 2025 menos 0,50 p.p.
- *Exemplo:* aba 2025, linha 3: `Rota … 0.0169, 0.0299, 0.0349, 0.0099`. No dossiê: "Taxa aplicada = aba 'ANTIGO 2025' … em: crédito à vista 2,99%, 2–6x 3,49%".
- *Correção sugerida:* acrescentar a F6 (ou criar um fato novo): "A aba 2025 explicaria 2 das 5 faixas com transação no período (à vista, 2–6x). Não explica 7–12x (aba 3,49; aplicada 4,09), débito (aba 1,69; aplicada 1,49) nem Pix (aba 0,99; aplicada 0,89). A aplicada é a contratada + 0,50 p.p. nas 3 faixas de crédito." Avaliar a mesma lógica para "coincide com" nos outros grupos.

**M2. G02 H1 da IA contradiz F6/F7 e ficou como a mais provável.**
- *O que acontece:* H1 ("a Orbe passou a usar uma tabela antiga de 2025 nas faixas de crédito; isso explica o acréscimo constante de +0,50 p.p.") cita F6, e F6 diz que o 7–12x **não** coincide. A tabela 2025 não explica +0,50 p.p. no 7–12x. H1 recebeu confiança `media` e H2 (cadastro errado ou alteração nas taxas de crédito, sustentada por F7) recebeu `baixa`: a ordem está invertida. O guarda-corpo só confere se o ID existe, não se o fato sustenta a hipótese.
- *Correção sugerida:* (a) M1 deixa a contradição explícita no dossiê. (b) Acrescentar ao prompt uma regra: "se um fato do grupo contradiz a hipótese, não a proponha, ou cite o fato contrário e use confiança baixa". (c) Opcional: pedir na saída `fatos_contrarios[]` por hipótese e mostrá-los na tela.

### BAIXO

- **B1. A execução real não será versionada.** `execucoes/` está no `.gitignore` e `docs/exemplo_investigacao_ia.md`, previsto na Fase 4 do plano, ainda não existe. A banca, sem chave, não veria a IA funcionando. *Correção:* copiar a execução real, revisada, para `docs/exemplo_investigacao_ia.md`.
- **B2. G03 H2 contradiz S30.** "O aviso pode ter sido enviado e falhado no cadastro", mas S30, presente no grupo, diz que a Mundo Aberto "não foi avisada". A hipótese não cita S30 e tem confiança `baixa`. *Correção:* a mesma regra de fato contrário de M2.
- **B3. G04 H2 se apoia pouco nos fatos.** "Sem relação com a data de comunicação da Tarvo" vai contra S30 (avisada dias depois de 15/09), que é exatamente o que H1 usa. É especulação, com confiança `baixa`.
- **B4. G01 tem duas hipóteses que são a mesma causa** (isenção não comunicada × falta de dono do aviso). O prompt já diz "não complete a lista por completar". A redundância é inofensiva.
- **B5. Mundo Aberto é um caso de fronteira de negócio, não um erro.** A Ponte também não foi avisada (S30), como a Orbe no caso da Casa, mas o grupo está como CONTRATO/cobrar_parceiro S por decisão da Helena (S05). Está documentado em `src/prompts/contexto_tarvo.md`, mas não no dossiê nem na pendência PEN-0007. *Correção:* citar S30 e S05 no motivo da PEN-0007 para a analista não estranhar a diferença em relação à Casa.
- **B6. Provedor.** A execução real usou OpenRouter (`anthropic/claude-sonnet-5.5`), e não a API da Anthropic direto, como dizia o plano. O arquivo registra provedor e modelo, então basta citar isso no README e no HIPOTESES.

## 3. Avaliação qualitativa da IA (execução `ia_real_1`)

Sem alucinação numérica: todos os números, datas, IDs e linhas da planilha citados estão no dossiê. A natureza dos grupos foi respeitada: na Casa, a IA não sugere cobrar a Orbe. Nenhuma hipótese foi descartada pelo guarda-corpo.

- **G01 Casa: boa.** A causa (isenção acordada, registrada só no fechamento, sem aviso à Orbe) é a dos fatos e de S07/S18/S30. "Falar com: Comercial" está certo. O 4º item de "conferir" (TX88445133) acrescenta pouco. H2 repete H1.
- **G02 Rota: fraca na ordem das hipóteses.** A leitura dos fatos favorece outra explicação: +0,50 p.p. constante nas 3 faixas de crédito (inclusive 7–12x, 4,09 = 3,59 + 0,50), e débito, Pix e antecipação na taxa de 2026. Isso aponta para um reajuste ou cadastro de +0,50 p.p. no crédito do EC na Orbe a partir de 12/09, e não para a volta da tabela 2025. A coincidência com a aba 2025 é aritmética. H2 devia ser a principal. O "conferir" e o "dado faltante" (histórico de cadastro do EC por volta de 12/09) estão corretos e levariam a Helena à resposta.
- **G03 Mundo Aberto: boa.** H1 (a Ponte não recebeu o 1,20% e aplicou o padrão de 1,50%) é sustentada por F5, F7, F8 e S30, e a confiança `alta` se justifica. A sugestão de verificar remessas anteriores a setembro é um bom dado faltante. "Falar com: Comercial" é coerente com a pergunta sobre a causa (se a Ponte foi avisada), embora a contestação seja com a Ponte (S05). H2 contradiz S30 (B2).
- **G04 Bridge: boa.** H1 (a Orbe manteve a taxa da linha 6 até receber o aviso tardio, o que explica o fim em 18/09) é a leitura mais provável. Com S30 e F7/F9, poderia ser `alta`. H2 é especulativa (B3).

**Conclusão:** o dossiê está correto nos números e o pipeline determinístico não é afetado pela IA (CSVs idênticos, 90 testes passando, nenhuma chave versionada). A IA é útil em 3 dos 4 grupos. A falha relevante é de raciocínio no G02: ela não pesou um fato contrário que ela mesma citou. Com M1 e M2 corrigidos, isso deve se resolver.
