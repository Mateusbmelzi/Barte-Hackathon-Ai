# 09 - Validação independente do pipeline de investigação (PLANO_IA_02)

Auditoria feita com scripts próprios (sem importar `src/`), a partir dos brutos. Nada do projeto foi alterado. A IA real não foi chamada e o `.env` não foi lido. Scripts em `scratchpad/auditoria_pipeline/`.

Veredito geral: **OK**. Nenhum achado crítico nem médio. Há 6 achados baixos (5 na redação da IA e 1 de rótulo na tela).

## 1. rota_valores a partir dos brutos - OK
Recalculei os segmentos a partir de Orbe 01 + 06, da planilha 02, do anexo do .eml e de `cadastro/condicoes_comerciais.csv`.

- Chave do segmento: faixa, taxa aplicada e taxa contratada. A data usada é a data da venda original nos estornos e reversões, e a data do movimento nas demais.
- Contratada: Casa = 0,00 de 01/09 a 31/12; Bridge crédito à vista = 2,59 até 14/09 e 2,19 desde 15/09; Rota Global e Casa fora da isenção seguem a planilha.
- G01, G02 e G04: os conjuntos (faixa, taxa aplicada, taxa contratada, de, ate, qtd) são idênticos ao dossiê. O campo `diverge` é consistente em todos os segmentos.
- Totais por grupo, somando segmentos divergentes e não divergentes: Casa 119 (118 divergentes + 1 estorno de 21/08, correto), Rota Global 159, Bridge 109. Batem com as transações brutas por EC, sem faltar nem repetir nenhuma. Não há id repetido entre os arquivos 01 e 06.
- G03 (Ponte, Mundo Aberto): 23 operações distintas no anexo, todas com spread de 1,50% (contratado 1,20%), de 01/09 a 30/09. Igual ao dossiê.
- `qtd` dos segmentos divergentes é igual ao `qtd` do grupo (118, 87, 5).

## 2. resumo_fatos, acao_regra, condicoes_cliente - OK
- Os 4 `resumo_fatos` estão fiéis à rota. Exemplos: +0,50 p.p. nas três faixas de crédito desde 12/09 (G02); 2,59 contra 2,19 de 15/09 a 18/09 (G04); 1,50 contra 1,20 em todas as remessas (G03).
- Os valores de `acao_regra` são iguais aos de `pendencias.csv`: 15.396,77 (PEN-0001), 1.545,86 (PEN-0003), 29,94 (PEN-0002) e 1.418,88 (PEN-0007). Devolver e recuperar batem com o `cobrar_parceiro` (N na Casa, S nas demais).
- Todas as R## citadas em `acao_regra` e em `regras_aplicaveis` existem em REGRAS_DE_NEGOCIO.md. O sentido é compatível: R52 (concessão fora do contrato), R13 (checkout), R22 (remessa), R68 e R74.
- `condicoes_cliente`: P13, P10, P15, P6 e P7 coincidem com as linhas da planilha, contando o cabeçalho na linha 5. C001 e C006 coincidem com o CSV do cadastro.

## 3. Reprodutibilidade - OK
`python -m src.fechamento` numa cópia sem `.env` gerou os 6 CSVs oficiais, `dossie.json` e `dossie.md` idênticos byte a byte à pasta real (`cmp` nos 8 arquivos). O dossiê devolvido pela API do servidor também é igual ao arquivo.

## 4. IA (execucoes/ia_real_5/investigacao_ia.json) - OK, com ressalvas baixas
- Não há chave de API no JSON.
- Todas as refs (evidências, fatos_citados e fatos_contrarios) existem no grupo. Todas as categorias estão no enum. `erro` é null nos 4 grupos.
- Nenhum número ou data fora do dossiê, exceto 19/09 e 22/09 no G04 (ver B2).
- Coerência da hipótese principal (2 linhas por grupo):
  - G01, CONDICAO_NAO_INFORMADA (alta): coerente com S18/S30 e R52. A taxa aplicada é a da planilha em 118 de 118 e a isenção está só no cadastro. A segunda hipótese, CONCESSAO_FORA_DO_CONTRATO (média), é a que a regra R52 nomeia. As duas são compatíveis.
  - G02, REAJUSTE_SEM_CONTRATO (média): +0,50 p.p. constante, contrato inalterado (S06), 4,09% sem correspondência em nenhuma tabela (F8). A alternativa TABELA_DESATUALIZADA (baixa) está bem rebaixada, porque a aba de 2025 só coincide em 2 de 5 faixas.
  - G03, CONDICAO_NAO_INFORMADA (alta): spread padrão de 1,50% em 23 de 23 operações, C006 e S30. Coerente.
  - G04, VIGENCIA_APLICADA_COM_ATRASO (média): a taxa aplicada é a da linha 6 da planilha e a divergência começa em 15/09 (F6/F7). Coerente. A segunda hipótese, CONDICAO_NAO_INFORMADA (média), também.

## 5. Tela - OK
- Servidor da cópia numa porta livre (8791, fora da 8765), com cliente falso que repete o conteúdo de `ia_real_5`. Não usei `python -m app`, porque ele tenta a 8765 primeiro. O servidor foi encerrado no fim.
- Rodei o fechamento pela API e o `/api/estado` traz o dossiê completo.
- Cartão no navegador embutido: título e lojista, selo da natureza e botão "Devolver e contestar R$ 1.545,86". Em seguida "O que aconteceu" (resumo), "Linha do tempo" (tabela com as linhas divergentes em rosa) e "Ação pela regra" com o rótulo "definido pela regra, não pela IA" e as regras R13, R68 e R74. Depois "Causa provável" (sugestão da IA, com confiança, explicação e "Por quê" com refs), "Para confirmar" e "Sua decisão".
- POST de decisão: VERIFICAR sem comentário, com comentário só de espaços, e DISCORDO sem comentário retornam 400. Decisão FOO, nome da analista vazio e decisão antes de gerar hipóteses também retornam 400. CONCORDO e VERIFICAR com comentário retornam 200.
- `decisoes_investigacao.csv` grava a coluna `causa_categoria` (REAJUSTE_SEM_CONTRATO e CONDICAO_NAO_INFORMADA_AO_PARCEIRO), com modelo e versão do prompt.
- O guarda-corpo aceitou o conteúdo real da IA sem ajustes.
- Sem `.env`, a tela informa que a chave está ausente e orienta como configurar.

## 6. pytest - OK
`pytest -q` na pasta real: **236 passed** em 49 s. `saida/` e o `git status` ficaram idênticos antes e depois.

## Achados
Nenhum CRÍTICO. Nenhum MÉDIO.

BAIXO:
- **B1 - G03, evidência de S30 mal redigida.** O texto é "A Mundo Aberto não foi avisada à Ponte, segundo a resposta do financeiro." Quem não foi avisada foi a Ponte, e a frase atribui o aviso ao lojista. Correção: pedir no prompt que a evidência reproduza o sujeito da resposta, ou checar na revisão. Não afeta valores.
- **B2 - G04, datas derivadas.** O campo `conferir` cita "entre 19/09 e 22/09". As datas não estão no dossiê; foram deduzidas do intervalo entre V3 (até 18/09) e V4 (desde 23/09). A dedução é verdadeira (não há crédito à vista nesses dias), mas viola a regra "só números do dossiê". Correção: expor a lacuna na rota ou aceitar datas derivadas por regra.
- **B3 - G02, fatos_contrarios repete evidências.** Na hipótese 2, F7, F8 e F4 aparecem como evidência e como contrários. F7 é de apoio parcial (coincide em 2 faixas), não contrário. Correção: no guarda-corpo, exigir que fatos_contrarios não repitam as evidências.
- **B4 - G02, S06 atribuída à Rota Global.** O texto "A Rota Global confirma que o contrato não mudou" vem da resposta do financeiro (S06), não do lojista. Correção: pedir que a frase diga "o financeiro confirma".
- **B5 - G03, hipótese 2.** O texto diz que "Todas as moedas das operações divergentes foram afetadas" (F3). A frase é tautológica e a evidência não sustenta um erro de cadastro. A confiança é baixa, então o efeito é pequeno. Sem correção necessária.
- **B6 - Observação sobre a Casa.** Na linha do tempo da Casa, a primeira linha é "Débito 21/08/2026, 1,49 contra 1,49, 1 transação". É um estorno de venda anterior à isenção. Está correto, mas pode confundir. Sugestão: rotular como "estorno de venda anterior".
