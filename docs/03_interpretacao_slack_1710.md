# Interpretação das respostas de 17/10 (S18–S39) para a nossa solução

Para cada resposta: o que ela **significa** para a Tarvo, o que **muda na solução** e **quem executa**. Fonte bruta: `docs/00_slack_respostas_financeiro.md`.

## A. O que a Tarvo realmente precisa (leitura de conjunto)
1. **O problema não é só calcular, é a informação não circular.** O Comercial fecha condições e ninguém avisa a Orbe nem a Ponte (S30). Por isso a Casa do Estudante e a Mundo Aberto foram cobradas errado o mês inteiro, e a Bridge por 4 dias. A planilha de taxas é a única fonte, desatualizada e mantida por quem não decide taxa (S33, S38).
2. **O tempo vai para casar nomes e refazer contas, e não para decidir.** Checkout leva 3 dias de match nome↔EC/CNPJ e retrabalho; extrato leva 2 dias linha a linha; remessa leva 2 dias de espera (S33). Isso a nossa solução já elimina. O que sobra para a Helena é decidir exceções e falar com terceiros, que é onde a IA ajuda.
3. **Todo conhecimento está em uma pessoa** (S32, S33): nas férias da Helena ninguém fecha. As regras escritas, com quem aprovou e quando, são parte do produto, não documentação acessória.
4. **Há dois tipos de "erro de taxa" com destinos diferentes:**
   - *Divergência de contrato*: o parceiro aplicou algo diferente do que foi informado a ele. A Tarvo **cobra o parceiro** e devolve ao lojista. São Rota e Bridge (Orbe) e Mundo Aberto (Ponte).
   - *Condição não comunicada*: o parceiro cobrou certo pelo que sabia; a falha é interna. **Não há o que cobrar** do parceiro; a Tarvo devolve ao lojista do próprio bolso. É a Casa do Estudante (S18, S37).

   Mundo Aberto é um caso de fronteira: a Helena chama de divergência e contesta com a Ponte (S05), embora também não tenha sido avisada (S30). Seguimos o que ela decidiu: contestar.
5. **O lojista já recebeu a menos** quando o parceiro cobra a mais, porque a taxa sai descontada na liquidação (S34). Toda divergência é, portanto, **dinheiro a devolver ao lojista**, e algumas também são dinheiro a recuperar do parceiro.
6. **O fechamento não termina no mês**: há coisas que atravessam meses. Atlas é faturada retroativamente quando a taxa sair (S27); o ajuste da Ponte volta no relatório seguinte (S36); a remessa da Ponte Aérea sai em outubro (S22); o TED da Ponte cai em 06/10 (S14). A solução precisa de **memória entre meses**.

## B. Mudanças na solução (por resposta)
| Resposta | Significa | Muda na solução | Dono |
|---|---|---|---|
| S18, S37 Casa | Isenção não informada ≠ divergência de contrato | `divergencias_taxa.csv`: colunas extras `natureza` (CONTRATO / ISENCAO_NAO_INFORMADA) e `cobrar_parceiro` (S/N). Pendência própria "devolver ao lojista", Helena + Comercial. Fora do total a cobrar da Orbe. | Dev |
| S19, S24, S25 | Divergência = lojista pagou diferente do contrato (a mais ou a menos) | Regra confirmada. Spread negativo segue só em pendência (já é assim). | Doc |
| S20 | Venda e estorno se anulam; cobra o líquido | Já é assim (estorno com sinal). H02 vira regra. | Doc |
| S21 | Taxa da venda original, mesmo na isenção | Já é assim (Casa −5,50). H01 vira regra. | Doc |
| S22 | PIX 18.240 = adiantamento de remessa de outubro da Ponte Aérea | Lançamento continua 2.1.02.001; passa a método HUMANO confirmado (conf. 1,0). Pendência muda de "sem origem" para "acompanhar: remessa prevista para o mês seguinte". Regra geral: PIX de lojista sem operação = recurso para remessa futura + acompanhamento. | Dev |
| S23 | Antecipação > vendas = alerta | Já existe. Tipo da pendência passa a ALERTA; decide Helena + Comercial. | Dev |
| S26 | CNPJ Ponte fora da planilha: calcula e abre cadastro | Já existe; quem decide = Comercial. | Dev |
| S27 | Taxa confirmada vale retroativa; mês seguinte puxa pendentes | **Novo:** memória entre meses (seção C). | Dev |
| S28 | Escolher conta para devolução de PIX | Manter 2.1.01.001 com motivo escrito. | Doc |
| S29 | Provisão de folha/impostos é regra permanente | Já é genérico. H14 vira regra. | Doc |
| S30 | Ninguém avisa os parceiros | Causa raiz no pitch. Proposta de melhoria: "aviso de condição nova" gerado pela solução. | Doc/Pitch |
| S31 | Rascunho de contestação por contraparte | **Segunda funcionalidade de IA** (seção D). | Dev (fase IA) |
| S32 | Comercial aprova taxa; Helena aprova regra de fechamento | REGRAS ganha colunas "aprovado por" e "data". Pendência de cadastro/contrato → Comercial. | Doc + Dev |
| S33 | Processo e tempos | CONTEXTO_EMPRESA.md e pitch ("de 8 dias para 1"). | Doc |
| S34 | Divergência = devolução ao lojista | Pendências de divergência dizem "devolver ao lojista R$ X; recuperar do parceiro R$ Y". | Dev |
| S35 | Repasse antecipado pela conta garantida sem regra | Fora do escopo do fechamento; vai como risco observado no pitch. | Pitch |
| S36 | Ajuste da Ponte vem no relatório seguinte | Outubro: linhas de ajuste no relatório da Ponte não podem quebrar o leitor; viram pendência "ajuste de contestação" ligada à pendência original (seção C). | Dev |
| S38 | Pendência por contraparte e por lojista; Comercial decide cadastro; >12x pendência | Agrupar spreads negativos por lojista (hoje 1 por operação). Conferir pendência para >12x. Quem decide cadastro = Comercial. | Dev |
| S39 | Atlas: repasse continua, só taxa suspensa | Já é assim. Vira regra. | Doc |

## C. Memória entre meses (lançamentos futuros)
Simples, em arquivos, sem banco de dados:
- Cada fechamento grava `historico/<AAAA-MM>/` com: `nao_faturado.csv` (transações fora da nota por falta de taxa, com arquivo e id de origem), `pendencias.csv` e `acompanhamentos.csv` (o que deve aparecer no mês seguinte: remessa da Ponte Aérea, TED da Ponte, transferência de 300 mil em trânsito, contestações abertas).
- O mês seguinte lê o histórico. Se a planilha já tem a taxa do EC, fatura as linhas antigas na nota do mês, com rastro até o arquivo e a linha originais e marcação "competência de origem 09/2026". Se não tem, continuam pendentes. Os acompanhamentos são conferidos contra o novo extrato ou relatório: o que apareceu é baixado, o que não apareceu vira pendência.
- Sem histórico (primeira execução, ou banca), o fechamento roda igual ao de hoje: **os 6 CSVs de setembro não mudam**.

## D. Onde a IA entra (fase seguinte, na ordem)
1. **Investigação de divergências** (aprovada): dossiê determinístico por grupo, e a IA levanta hipóteses de causa. Com S30 ela ganha um fato forte: "condição fechada pelo Comercial em X, parceiro não avisado".
2. **Rascunho de contestação por contraparte** (S31): um e-mail para a Orbe (Rota, Bridge) e um para a Ponte (Mundo Aberto, spreads negativos, duplicata), com a planilha de operações anexa. A Helena revisa e envia. Casa do Estudante **não** entra (S18); ela gera um rascunho separado para o Comercial/lojista.
3. Candidata: **aviso de condição nova** para parceiros quando a planilha muda, que ataca a causa raiz S30. Fica para depois.

A IA nunca altera valor, nunca fecha pendência, nunca envia nada.
