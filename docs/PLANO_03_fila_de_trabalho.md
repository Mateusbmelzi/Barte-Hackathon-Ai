# Plano 03 — Fila de trabalho, ações sugeridas pela IA, contatos e assistente de cadastro

Decisões do usuário (17/10, ~15h45): e-mail abre pronto no cliente de e-mail (mailto) e a analista envia lá; contatos em `cadastro/contatos.csv` com aba própria; IA roda automaticamente em todas as pendências e divergências após o fechamento; assistente de IA só altera condições de cliente no cadastro, sempre com confirmação.

## Contratos (os três devs programam contra isto)

### Itens da fila e chave estável
- Pendência: `chave = "PEN|" + tipo + "|" + ref_origem`.
- Divergência (por grupo do dossiê): `chave = "DIV|" + contraparte + "|" + cnpj + "|" + natureza`.
- Status: `ABERTA` → `EM_ACOMPANHAMENTO` → `BAIXADA`; divergência também pode ser `DECLINADA` (sai da fila).

### `meses/<AAAA-MM>/fila_log.csv` (memória do mês, só acrescenta)
`data_hora;usuario;chave;tipo_item;acao;status_novo;detalhe`
- tipo_item: PENDENCIA | DIVERGENCIA
- acao: SUGESTAO_IA | EMAIL_PREPARADO | EMAIL_ENVIADO | BAIXA | DECLINADA | REABERTA | COMENTARIO
- status atual de um item = `status_novo` da última linha com status preenchido; sem linhas = ABERTA.

### Colunas extras nos CSVs oficiais (no fim, depois das obrigatórias)
- `pendencias.csv`: `status;ultima_acao;data_ultima_acao;responsavel;comentario`
- `divergencias_taxa.csv`: `status` (o do grupo da linha)
- Sem fila (CLI/banca): todas `ABERTA` e o resto vazio → determinístico. O texto da IA NÃO entra nos CSVs oficiais.
- `fechamento.executar(..., fila=<pasta do mês ou None>)`; CLI `--fila <pasta>`.

### Ações permitidas por tipo (config `ACOES_POR_TIPO`)
`tipo → {"objetivo": "...", "destinos": [papéis permitidos]}`; papéis: LOJISTA, ORBE, PONTE, COMERCIAL, BANCO_AURORA, BANCO_MERIDIANO, CONTABILIDADE, FINANCEIRO_INTERNO. Ex.: DEVOLUCAO_LOJISTA_ISENCAO → [COMERCIAL, LOJISTA]; DIVERGENCIA_TAXA_CHECKOUT → [ORBE, LOJISTA]; SPREAD_NEGATIVO → [PONTE]; CREDITO_NAO_IDENTIFICADO → [BANCO_AURORA]; FONTE_AUSENTE → [FINANCEIRO_INTERNO]. Tipo sem entrada → [FINANCEIRO_INTERNO].

### `cadastro/contatos.csv`
`id_contato;papel;cnpj;nome;email;observacao` — e-mails fictícios (`@exemplo.com.br`), editáveis na aba Contatos. Lojista: um por CNPJ; ORBE, PONTE, COMERCIAL, BANCO_AURORA, BANCO_MERIDIANO, CONTABILIDADE: um cada.

### IA de ação — `src/ia_acoes.py`
`sugerir(item, contexto, destinos_permitidos) -> {"chave","acao_resumo","destinos":[papel],"emails":[{"papel","assunto","corpo"}],"prazo_sugerido","valores_citados":[...]}`
- Guarda-corpos: destino fora dos permitidos → removido; e-mail sem destino permitido → removido; todo valor em R$ citado no texto tem de existir no item (senão o e-mail é descartado e marca erro); nunca promete pagamento/devolução sem dizer "conforme aprovação da Helena"; tom profissional, PT-BR, curto.
- `sugerir_todos(itens, ...)` em paralelo limitado; cache em `<pasta da execução>/sugestoes_ia.json`. Sem chave: `disponivel()` falso e a tela mostra só o objetivo do playbook.
- Divergências: continuam com `ia.investigar` (causa) — rodar automaticamente após o fechamento — e TAMBÉM recebem `sugerir` (ação + e-mail).

### Assistente de cadastro — `src/ia_cadastro.py`
`propor(texto, lojistas, condicoes_vigentes) -> {"condicoes":[dict no schema do cadastro], "resumo":"...", "antes_depois":[{"faixa","antes","depois","origem"}], "duvidas":"..."}`
- Nunca grava. Valida com `cadastro.validar(condicao, pasta)` (dry-run, a ser exposto pelo Dev 1) e devolve os erros legíveis. Só tipos ISENCAO, TAXA_ESPECIAL, BLOQUEIO_FATURAMENTO, DE_PARA_EC, NOTA_PENDENCIA. Exige `aprovado_por` explícito no texto para taxa/isenção; se faltar, devolve `duvidas` e nenhuma condição.
- Gravar só via botão "Confirmar" → `cadastro.adicionar_varias`.

## Tela
Abas: Fechamento | **Fila de trabalho** (Pendências · Divergências · Em acompanhamento · Encerradas) | Clientes (+ caixa do assistente) | **Contatos**.
Item: título, valor, status, sugestão da IA, contatos; botões **Preparar e-mail** (popup editável; **Abrir no e-mail** = `mailto:`; depois pergunta "Você enviou?" → EMAIL_ENVIADO + EM_ACOMPANHAMENTO), **Dar baixa** (comentário), **Declinar** (só divergência, comentário), **Histórico**.

## Garantias
6 CSVs oficiais: no fechamento sem fila, iguais aos atuais + colunas extras com ABERTA (saida/ será regenerada uma vez e passa a ser o novo gabarito byte a byte). Nada é enviado automaticamente. Nenhum valor vem da IA.
