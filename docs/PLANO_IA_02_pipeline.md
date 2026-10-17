# Plano — IA v2: pipeline de investigação e cartão de decisão

## Pipeline
```
1. Detecta     → fechamento acha a divergência (existe)
2. Monta o caso (determinístico, src/investigacao.py), por grupo:
   a. rota_valores: linha do tempo por faixa — taxa cobrada × contratada por período
   b. condicoes_cliente: linhas da planilha (vigências) + condições do cadastro (C###)
   c. regras_aplicaveis: só as R## que valem para a natureza do caso
3. Ação pela regra (determinístico): devolver / cobrar parceiro / contestar, com valores e R##
4. IA explica (src/ia.py, prompt v4): escolhe a causa numa LISTA FECHADA, explica em linguagem simples,
   evidências em frases com referência, o que conferir, com quem falar. Não decide ação nem valor.
5. Guarda-corpo: IDs citados existem; categoria válida; contradição rebaixa confiança (existe)
6. Analista: Concordo / Discordo / Preciso verificar + comentário
```

## Contrato de dados (os três devs programam contra isto)
Campos NOVOS em cada grupo de `saida/investigacao/dossie.json` (os existentes continuam):
```json
"resumo_fatos": "Desde 12/09 a Orbe cobra +0,50 p.p. no crédito (à vista, 2–6x, 7–12x); débito, Pix e antecipação corretos.",
"acao_regra": {"texto": "Devolver ao lojista R$ 1.545,86 e contestar o mesmo valor com a Orbe.", "regras": ["R13", "R68", "R74"]},
"rota_valores": [
  {"id": "V1", "faixa": "CREDITO A VISTA", "de": "2026-09-01", "ate": "2026-09-11", "taxa_aplicada": "2.49", "taxa_contratada": "2.49", "qtd": 20, "diverge": false},
  {"id": "V2", "faixa": "CREDITO A VISTA", "de": "2026-09-12", "ate": "2026-09-30", "taxa_aplicada": "2.99", "taxa_contratada": "2.49", "qtd": 38, "diverge": true}
],
"condicoes_cliente": [
  {"id": "P10", "origem": "planilha linha 10", "texto": "desde 01/01/2026: débito 1,49%; crédito à vista 2,49%; …"},
  {"id": "C001", "origem": "cadastro", "texto": "isenção no checkout de 01/09 a 31/12/2026, aprovada por Comercial (S07)"}
],
"regras_aplicaveis": [{"id": "R13", "texto": "…"}]
```
Saída da IA por hipótese (prompt v4), além do que já existe:
```json
"causa_categoria": "REAJUSTE_SEM_CONTRATO",
"explicacao": "1–2 frases para quem não é técnico",
"evidencias": [{"texto": "A diferença é de +0,50 p.p. igual nas três faixas de crédito", "ref": "V2"}]
```
Categorias (enum): CONDICAO_NAO_INFORMADA_AO_PARCEIRO, VIGENCIA_APLICADA_COM_ATRASO, REAJUSTE_SEM_CONTRATO,
TABELA_DESATUALIZADA_NO_PARCEIRO, ERRO_DE_CADASTRO_NO_PARCEIRO, CONCESSAO_COMERCIAL_FORA_DO_CONTRATO, OUTRA.
IDs citáveis pela IA: F# (fatos), V# (rota), P#/C### (condições), R## (regras), S## (respostas do financeiro).

## Regras de construção
- Os 6 CSVs oficiais não mudam. O dossiê é determinístico (mesma entrada → mesmos bytes).
- A IA nunca gera ação, valor ou decisão; a ação vem de `acao_regra`.
- Decisões da analista: CONCORDO | DISCORDO | VERIFICAR (VERIFICAR fica marcado como pendente de checagem).
