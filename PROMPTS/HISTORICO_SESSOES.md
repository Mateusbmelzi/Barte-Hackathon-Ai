# Histórico das sessões de IA (Claude Code, modo gestor)

Registro enviado pelo time. Resumo, na ordem em que as sessões aconteceram. Chaves de API foram removidas.

## Sessão 1 — Planejamento, perguntas ao financeiro e revisão das perguntas
- Pedido inicial: o Claude atua como gestor e planejador (não executa), coordena agentes, entrega MVP testado, regras comprovadas, hipóteses, instruções de uso e pré-esboço de pitch.
- O Claude leu o edital e os dados, criou o PLANO.md (7 fases) e lançou o analista de dados.
- O usuário trouxe as 15 threads do Slack; o Claude registrou as respostas (S01–S17) e criou REGRAS_DE_NEGOCIO.md v1.
- Correção do usuário: as perguntas ao financeiro não podem embutir a premissa nem terminar em "ok?/está certo?"; devem perguntar a regra. O Claude reescreveu PERGUNTAS_SLACK.md e guardou o critério.

## Sessão 2 — Construção, auditorias e entrega
- Dev, auditor e documentador em paralelo; auditoria independente com recálculo; correção da hipótese H08 (spreads negativos tratados como divergência — erro da IA pego pelo auditor).
- Evolução: cadastro de condições comerciais, aba Clientes, pipeline de IA (dossiê determinístico, causa em lista fechada), fila de trabalho, reenvio de arquivos, cliente novo com contrato lido pela IA.
- Commit final às 18h23; chave removida do export antes de qualquer commit.

## Sessão 3 — Prompt para gerar dados fictícios de teste
- Pedido: escrever um prompt para o ChatGPT gerar um mês fictício (outubro/2026) no formato dos arquivos do case, com 20+ inconsistências plantadas e gabarito com a interpretação (usando as regras R##).

## Sessão 4 — Auditoria geral com 4 agentes Sonnet
- Escopo vs. enunciado; checkout; remessa e notas; extratos, rastro e testes. Resultado: números batem ao centavo (checkout R$ 207.039,73 na época; remessa R$ 39.543,45); achados: falta de histórico em PROMPTS/ (este arquivo), PIX da Atlas classificados com confiança 0,95, diferença de R$ 5,50 entre notas e comissão (Casa do Estudante).
- Pergunta do usuário sobre os dois bancos: sem justificativa escrita; inferência: Aurora = operação e checkout, Meridiano = câmbio e remessa.

Observação: os textos integrais das sessões foram copiados e enviados pelo time conforme o edital; este arquivo é o índice no repositório.
