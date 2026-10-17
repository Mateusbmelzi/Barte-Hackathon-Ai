# Plano de execução — Fechamento Tarvo set/2026

Gestor: Claude (coordena, não executa). Executores: agentes. Toda entrega passa por validação do gestor antes de avançar.

## Objetivo
Uma solução simples (Python + pandas, linha de comando) que lê os 6 arquivos **como vêm** e gera em `saida/` os 6 CSVs do formato oficial, com rastro de cada número até a linha de origem. Roda de novo em outubro só trocando a pasta de entrada.

Princípio: **mínimo certo antes do extra**. Ordem de prioridade:
1. Comissão CHECKOUT por lojista + rastro (nível mínimo)
2. Comissão REMESSA, divergências de taxa, notas a emitir, lançamentos classificados (nível alvo)
3. Pendências explicadas, rastro completo, robustez para outubro (nível extra)

## Estrutura do repositório (obrigatória no edital)
```
README.md            instalar e rodar do zero, limitações
COMO_USAR.md         passo a passo para a analista (não técnico)
REGRAS_DE_NEGOCIO.md regras comprovadas (dado ou resposta do financeiro)
HIPOTESES.md         premissas, perguntas ao financeiro e respostas
PERGUNTAS_SLACK.md   dúvidas abertas para o usuário levar ao Slack
PITCH.md             pré-esboço do pitch
PROMPTS/             histórico + MOMENTOS.md
docs/                entendimento dos dados (EDA)
src/                 código
tests/               testes automáticos (pytest)
saida/               CSVs gerados
<arquivos de dados>  ficam na raiz, intocados
```

## Fases

| # | Fase | Agente | Entrega | Critério de aceite (gestor valida) |
|---|---|---|---|---|
| 1 | Entendimento dos dados | Analista de dados | `docs/01_entendimento_dados.md` | Cada arquivo: layout, encoding, chaves, totais, anomalias com exemplos (ids reais). Lista de regras evidentes e de dúvidas. |
| 2 | Regras + hipóteses v1 | Gestor | `REGRAS_DE_NEGOCIO.md`, `HIPOTESES.md`, `PERGUNTAS_SLACK.md` | Cada regra cita evidência; cada hipótese tem ID (H01…), impacto e o que muda se a resposta for outra. |
| 3 | Leitores (parsers) | Dev | `src/leitores.py` + testes | Lê os 6 arquivos sem limpeza manual; contagens batem com a EDA. |
| 4 | Motor de cálculo | Dev | `src/checkout.py`, `src/remessa.py`, `src/extratos.py`, `src/saidas.py`, `src/fechamento.py` | Gera os 6 CSVs no formato oficial; regras parametrizadas em `src/config.py` com referência à hipótese/regra. |
| 5 | Validação independente | Auditor (agente diferente do dev) | `docs/02_validacao.md` + `tests/` | Recalcula amostras à mão a partir do arquivo bruto; soma do rastro = número reportado; formato do edital; sem alarmes falsos óbvios. |
| 6 | Documentação + pitch | Redator | `README.md`, `COMO_USAR.md`, `PITCH.md`, atualização de regras/hipóteses com números finais | Linguagem para financeiro; números do pitch saem dos CSVs gerados. |
| 7 | Revisão final | Gestor | checklist abaixo | Tudo verde. |

## Regras de trabalho para todos os agentes
- Não editar os arquivos de dados originais. Não fazer limpeza manual.
- Toda regra de negócio usada no código cita `R##` (comprovada) ou `H##` (hipótese) em comentário e em `config.py`.
- Nada de casamento aproximado de nomes "que parece bom": vínculo por chave (CNPJ, código de estabelecimento, id). Se não houver chave, vira pendência.
- Exceção de negócio ≠ erro de código: vai para `pendencias.csv` com motivo e quem decide.
- Simples > esperto. Sem LLM no caminho crítico de cálculo; IA só onde a regra não resolve (e marcada `metodo=IA`).

## Checklist final (gestor)
- [x] `python -m src.fechamento` roda do zero e gera os 6 CSVs (auditor e documentador, cópias limpas, byte a byte)
- [x] `pytest` verde (51, inclui gabarito independente e outubro simulado)
- [x] Formato: `;`, ponto decimal, datas AAAA-MM-DD, CNPJ 14 dígitos (docs/02_validacao.md)
- [x] Para todo `id_saida`: soma de `rastro.valor` = valor reportado (491/491, conferido pelo gestor)
- [x] Toda hipótese no código está no HIPOTESES.md e vice-versa (H01–H24)
- [x] COMO_USAR, REGRAS, HIPÓTESES, PERGUNTAS_SLACK, PITCH entregues

## Pendente (time humano)
- [ ] Levar PERGUNTAS_SLACK.md ao financeiro; aplicar respostas conforme HIPOTESES.md §3
- [ ] Exportar transcripts das sessões de IA para PROMPTS/
- [ ] Checkpoints 11h e 15h30; repositório público no GitHub até 18h30; pitch até 19h
