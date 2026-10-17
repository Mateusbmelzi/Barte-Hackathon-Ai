# 11 — Validação independente: fila de trabalho, ações da IA, contatos e assistente (Plano 03)

Auditoria feita em 17/10/2026 sobre o código do working tree. Nada em `src/`, `app/`, `tests/`, `saida/`, `cadastro/` foi alterado; as execuções reais usaram pastas temporárias (meses, cadastro e execuções em cópia).

## Resultado

| # | Verificação | Resultado |
|---|---|---|
| 1 | Banca (cópia sem `.env`): `python -m src.fechamento` gera os 6 CSVs + dossiê (md/json) idênticos byte a byte a `saida/`; `pendencias.csv` = colunas do edital + `status;ultima_acao;data_ultima_acao;responsavel;comentario` (todas ABERTA, resto vazio); `divergencias_taxa.csv` = colunas do edital (+ natureza e cobrar_parceiro, que já existiam) + `status` ABERTA | OK |
| 2 | Execução real ponta a ponta (servidor com `ia_auto=True`, 22 itens = 18 pendências + 4 divergências) | OK com ressalvas (M2 a M4) |
| 3 | Fluxo de status na tela | OK |
| 4 | Assistente de cadastro | OK com ressalva (B3) |
| 5 | Contatos dos destinos | FALHA parcial (M1: 2 de 33 destinos sem e-mail) |
| 6 | `pytest -q` | OK, 364 passed (62 s) |

## 2. IA de ações, execução real

Três rodadas completas sem cache (rodada 1 pelo servidor; 2 e 3 por `sugerir_todos`), modelo `anthropic/claude-sonnet-5.5`.

- Sugestões: 22/22 sem erro em todas as rodadas. E-mails gerados: 33 por rodada (99 no total).
- E-mails descartados: **0 de 99 (0%)**. Por data: 0. Por valor: 0. Por "já feito"/promessa: 0. Por destino fora de `ACOES_POR_TIPO`: 0. Por tamanho: 0.
- Único ajuste registrado: 1 `acao_resumo` substituído pelo objetivo do playbook (rodada 3, grupo DIV Ponte/Mundo Aberto; motivo "afirma que a devolução/cobrança já foi feita"; 1 de 66 resumos). O texto original não é guardado, então não dá para saber se foi falso positivo (B4).
- Descartes indevidos pelos guarda-corpos de DATAS e VALORES: **nenhum ocorreu** nos dados reais, porque o item enviado à IA repete datas e valores em texto BR (`motivo`, `resumo_fatos`). Em teste sintético o risco existe (M3): data só em ISO e valor só em campo numérico do dossiê são descartados mesmo sendo verdadeiros.
- Conferência independente dos 99 e-mails: todo `R$` existe no item; todo dd/mm existe no item; apenas `09/2026` (competência, vem do contexto) e percentuais (`1,4991%`, `1,5%`, escritos com vírgula; o item usa ponto) não têm lastro literal, todos verdadeiros. Destinos e e-mails sempre dentro de `ACOES_POR_TIPO` (tipo sem entrada -> FINANCEIRO_INTERNO). Nenhum e-mail diz que a Tarvo "já devolveu/pagou/creditou"; as promessas vêm sempre com "conforme aprovação do financeiro". Os "foi devolvido" nos e-mails de L65 referem-se ao PIX devolvido pelo banco (fato do item).

Qualidade de 5 e-mails:
1. ALERTA_ANTECIPACAO -> COMERCIAL: bom. Fatos e datas do item, pede contrato e limite, curto.
2. DIV Rota Global -> ORBE: bom. Contesta 87 linhas, R$ 1.545,86, oferece detalhamento; sem prometer nada.
3. SPREAD_NEGATIVO -> PONTE: bom. Cita a operação, a observação "Taxa travada no pedido (D-1)" e a diferença; pede correção do repasse.
4. DEVOLUCAO_LOJISTA_ISENCAO -> LOJISTA: aceitável, mas sai junto com o do Comercial embora o próprio resumo mande confirmar a isenção primeiro, e diz "diferentes da condição combinada" (M4).
5. SALDO_CHECKOUT_NAO_POSITIVO -> LOJISTA: fraco. Comunica ao lojista saldo de R$ -5,50, a hipótese de estorno e "não haverá repasse nem nota" enquanto o e-mail interno pede decidir antes de avisar o lojista (M4).

## 3. Fluxo de status (servidor em porta livre, pasta temporária)
- Preparar e-mail: `mailto:` bem formado; decodificado de volta, assunto e corpo preservam acentos, travessão, `&`, `?` e quebras de linha. O status permanece ABERTA (só registra EMAIL_PREPARADO).
- "Enviei": EM_ACOMPANHAMENTO; `pendencias.csv` da execução com `status=EM_ACOMPANHAMENTO; ultima_acao=EMAIL_ENVIADO; data_ultima_acao; responsavel`.
- Baixa sem comentário (nem só espaços): 400. Declinar pendência: 400 (mensagem clara). Declinar divergência sem comentário: 400; com comentário: DECLINADA e as 87 linhas do grupo no `divergencias_taxa.csv` com `status=DECLINADA`.
- Também: sem "Seu nome" 400; e-mail inválido 400; chave inexistente 400; e-mail em item encerrado 400; reabrir -> ABERTA; reabrir item já aberto 400 (transição inválida); declinar de novo OK.
- Novo `/api/rodar`: status preservados (EM_ACOMPANHAMENTO, BAIXADA, DECLINADA); contadores e CSVs da nova execução refletem.

## 4. Assistente
- "A Rota Global passa a pagar 2,79% no crédito à vista a partir de 01/10/2026, aprovado pelo Comercial." -> 1 condição TAXA_ESPECIAL, CNPJ 95927868000148, EC 1074504011, CREDITO A VISTA, 2.79, início 2026-10-01, aprovado_por Comercial, antes/depois 2,49% -> 2,79%, `erros` vazio. Cadastro idêntico (hash) após propor; `confirmar` sem nome 400 (nada gravado); com nome gravou C007 (só no cadastro temporário); segundo `confirmar` com o mesmo token 400.
- Mesmo texto sem aprovador -> `condicoes: []` e `duvidas` perguntando quem aprovou. Nada gravado.
- Texto misto (Atlas isenção aprovada + "5% de desconto" Kiwi) -> `condicoes: []` e dúvidas coerentes (inclusive aviso do bloqueio C005 da Atlas).

## Achados

### CRÍTICO
Nenhum.

### MÉDIO
- **M1 — Dois itens com destino LOJISTA sem contato.** `PEN|DEVOLUCAO_REPASSE|L65` (Mundo Aberto) e `PEN|ACOMPANHAR_REMESSA_FUTURA|MRD2026090425` (Ponte Aérea Estudantil): o `ref_origem` não traz CNPJ/EC, então `Fila.itens_base` deixa `cnpj=""` e o contato de LOJISTA vem vazio; a tela abre o popup sem "Para" e o envio falha com "Informe o destinatário". Os outros 31 destinos resolvem (Atlas incluído: COMERCIAL nos dois itens; o contato K024 existe). Correção: preencher o CNPJ dessas pendências na origem (a descrição do lançamento traz `DEVOLUCAO PIX - MUNDO ABERTO` / `PIX RECEB PONTE AEREA ESTUDANTIL`) ou resolver por nome do lojista em `contatos.para`; no mínimo, a tela deve avisar "lojista não identificado" em vez de campo vazio.
- **M2 — Guarda-corpo "já foi feito" tem lacunas.** `_problema_texto` deixa passar: "O valor foi devolvido ao lojista.", "Valor devolvido ao lojista em setembro.", "A diferença foi paga.", "Pagamento realizado.", "O valor já está na conta do lojista.", "Devolução concluída.", "Já regularizamos a cobrança.", "O valor de R$ 100,00 foi estornado." (pega "creditado", "estorno processado", "já devolvemos", "já foi pago"). Nenhuma dessas frases apareceu nas 99 saídas reais, mas hoje o prompt é o único freio. Correção: ampliar `_FEITO` com particípios (`devolvid|estornad|pag[oa]|creditad|ressarcid|quitad|regularizad|concluid`) após `foi|foram|esta|estao|ja`, mais teste de regressão com essas frases (cuidando do caso legítimo "o PIX foi devolvido pelo banco").
- **M3 — Guarda-corpo de datas/valores só enxerga texto BR do item (descartes indevidos em potencial).** Teste sintético: item com `grupo.primeira_data="2026-09-14"` e e-mail "em 14/09" é descartado; `grupo.total_bruto="262138.61"` e e-mail "R$ 262.138,61" é descartado; "08/2026" idem. Hoje não ocorre porque `motivo` e `resumo_fatos` duplicam os números em BR. Correção: em `valores_permitidos` e `datas_ok`, varrer também decimais (`\d+\.\d{2}`) e datas ISO do JSON do item, convertendo para BR. Percentuais (`2,79%`) e contagens não têm guarda-corpo (um `%` inventado passa); sugestão: mesma verificação para `\d+[.,]\d+\s*%`.
- **M4 — E-mails duplicados e fora de sequência.** Quatro casos geram DOIS itens para o mesmo fato (pendência + grupo de divergência: Casa do Estudante, Rota Global, Mundo Aberto, Escola Bridge), cada um com e-mails próprios para os mesmos destinatários: 8 dos 33 e-mails são redundantes (ex.: a Orbe recebe duas contestações de R$ 1.545,86 da Rota Global). O e-mail ao LOJISTA de isenção sai junto com o do COMERCIAL embora a ação mande confirmar com o Comercial primeiro, e o saldo de R$ -5,50 gera e-mail ao lojista. Correção: indicar na tela os itens gêmeos ("mesmo caso de PEN-000X") e sugerir um e-mail por destinatário/caso; no prompt, "e-mail ao lojista só depois da confirmação do Comercial" e piso de valor para escrever ao lojista.

### BAIXO
- **B1** — E-mails FINANCEIRO_INTERNO são "da Helena para Helena" (assinatura = destinatária); trocar a assinatura ou gerar só a nota.
- **B2** — `mailto` codifica quebra de linha como `%0A`; a RFC 6068 pede `%0D%0A` (Outlook desktop às vezes junta linhas). Trocar `\n` por `\r\n` antes de `quote`.
- **B3** — Assistente: no texto misto o `resumo` diz "Será cadastrada isenção ... para a Atlas" mas `condicoes` vem vazio (por causa da dúvida), resumo contraditório na tela; no caso sem aprovador o resumo mostra data ISO (`2026-10-01`). Correção: havendo `duvidas`, forçar "Nada será cadastrado ainda" e formatar datas em dd/mm/aaaa.
- **B4** — Ao substituir `acao_resumo`, só o ajuste é gravado; guardar o texto original no cache para auditar falsos positivos.
- **B5** — `EMAIL_PREPARADO` não muda o status (conforme o plano); a tela deve deixar claro que só "Enviei" move o item.

## Arquivos de apoio (scratchpad, fora do projeto)
`auditoria_fila/`: `run_real.py`, `rep.py`, `chk.py`, `fluxo.py`, `assist.py`, `emails.txt`, `real/fila_final.json`, `real/runs_extra.json`.
