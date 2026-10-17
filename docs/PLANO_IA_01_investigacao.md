# Plano — IA use case 1: Investigação de divergências

> **Como ficou (17/10/2026).** O plano abaixo foi mantido como escrito. Diferenças em relação ao que foi implementado:
> - **Campo `dado_faltante`** (no lugar de `alerta_dado_faltante`): o dado que mais mudaria a conclusão e que não está no grupo ("nenhum" se nada faltar).
> - **Provedor:** além da API da Anthropic (`claude-sonnet-5-5`, SDK opcional), o OpenRouter (`anthropic/claude-sonnet-5.5`, chave `sk-or-`, só biblioteca padrão). É o mesmo modelo, sem fallback. A execução real de exemplo usou o OpenRouter. Sem `temperature` (o modelo rejeita); profundidade por effort/reasoning médio.
> - **Prompt `investigacao-v3` com `fatos_contrarios`:** cada hipótese cita os fatos a favor e os contrários. O prompt tem teste de contradição e exemplo fictício. O código remove IDs inexistentes, rebaixa `alta` com fato contrário para `media` e ordena por confiança. Motivo: na primeira execução, a IA pôs como principal na Rota uma hipótese ("tabela 2025") que um fato citado por ela mesma contradizia (`docs/04_validacao_ia.md`, M1/M2). O dossiê também passou a dizer o que a coincidência **não** explica.
> - **Exemplo do "Depois" abaixo:** a Rota **não** diverge no débito, só nas 3 faixas de crédito (fato calculado do dado; ver `PROMPTS/MOMENTOS.md`, momento 3).
> - **Execução real versionada** em `docs/exemplo_investigacao_ia.md` (execução 3). **Testes:** 98 no total, inclusive os da IA, com resposta simulada e sem rede.

## Objetivo
Para cada divergência que o fechamento encontra, a analista recebe **pronto**: os fatos (o que aconteceu), as hipóteses de causa (por que provavelmente aconteceu), o que conferir e com quem falar. Ela **aceita, recusa ou comenta**. A IA não decide nada.

Hoje: a Helena recebe "Rota: 87 transações, R$ 1.546,28" e precisa investigar sozinha.
Depois: "Rota — a partir de 12/09 a Orbe passou a cobrar +0,50 p.p. em débito, crédito à vista e 2–6x; o contrato não mudou (S06). Hipótese provável: reajuste cadastrado na Orbe sem contrato. Conferir: e-mail do Comercial para a Orbe em set/26. Falar com: Orbe." → [Aceitar] [Recusar] [Comentar].

## Princípios (não negociáveis)
1. **Fatos por código, texto pela IA.** Todo fato é calculado de forma determinística a partir dos arquivos. A IA só interpreta fatos que recebeu.
2. **Hipótese sem fato citado é descartada.** Cada hipótese precisa citar os IDs dos fatos que a sustentam; o código valida e descarta o resto.
3. **Os 6 CSVs oficiais não mudam com IA.** A IA escreve em arquivo separado. Com ou sem chave, `saida/` é idêntico (a banca compara byte a byte).
4. **Funciona sem chave.** Sem `ANTHROPIC_API_KEY`, a analista recebe só o dossiê de fatos, que já poupa tempo.
5. **A IA não envia, não altera valor, não fecha pendência.** A decisão da analista é registrada com nome, data e comentário.

## Fluxo de ponta a ponta
```
arquivos do mês
   │
   ▼
[1] fechamento determinístico (já existe) ──► 6 CSVs oficiais (inalterados pela IA)
   │
   ▼
[2] dossiê determinístico por grupo de divergência ──► saida/investigacao/dossie.json (+ .md legível)
   │                                                    (determinístico, entra no repositório)
   ▼ (só se houver chave e a analista pedir)
[3] IA: 1 chamada por grupo ──► execucoes/<run>/investigacao_ia.json (hipóteses validadas)
   │
   ▼
[4] tela: cartão por grupo = fatos | hipóteses | [Aceitar] [Recusar] [Comentar]
   │
   ▼
[5] decisões ──► execucoes/<run>/decisoes_investigacao.csv (quem, quando, decisão, comentário)
```

## Fases

### Fase 0 — Pré-requisito determinístico (S18, S37, S38)
- `divergencias_taxa.csv`: colunas extras `natureza` (CONTRATO | ISENCAO_NAO_INFORMADA) e `cobrar_parceiro` (S|N). Casa do Estudante = ISENCAO_NAO_INFORMADA, N.
- Pendências: Casa vira "devolver ao lojista" (Helena + Comercial), fora da cobrança da Orbe; divergências de contrato dizem "devolver ao lojista R$ X; recuperar do parceiro R$ X"; spreads negativos agrupados por lojista; cadastro/contrato decide o Comercial; PIX 18.240 vira acompanhamento (S22).
- Comissões e notas **não mudam**. Regenera `saida/` e atualiza os testes de gabarito.

### Fase 1 — Dossiê determinístico (`src/investigacao.py`)
**Grupo** = contraparte (ORBE/PONTE) × lojista × natureza. Setembro: Casa, Rota, Bridge (Orbe); Mundo Aberto (Ponte). Spreads negativos ficam para a v2.

**Fatos por grupo**, cada um com ID (F1, F2…), texto curto e refs de origem:
- quantidade, valor total, valor a devolver, valor a recuperar do parceiro;
- primeira e última data; dias corridos;
- modalidades/faixas de parcela afetadas e não afetadas no mesmo período;
- diferença em p.p.: constante ou variável (mín/máx);
- a taxa aplicada coincide com…: a vigência anterior do mesmo lojista na planilha; a aba 2025; a taxa de outro lojista; o spread padrão 1,5%; a taxa "cheia" de antes de uma isenção;
- datas de mudança na planilha × data de início da divergência (ex.: Bridge muda em 15/09, a divergência vai de 15 a 18/09);
- respostas do financeiro que tocam o caso (S##), lidas de uma tabela em `config.py`, nunca inventadas;
- 3 transações de exemplo (ids).

Saída: `saida/investigacao/dossie.json` e `dossie.md` (legível). São determinísticos e entram no repositório.

### Fase 2 — IA (`src/ia.py` + `src/prompts/investigacao.md`)
- **Modelo:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), 1 chamada por grupo (4 em setembro), saída estruturada (JSON schema) e temperatura baixa.
- **Entrada:** contexto da empresa (resumo de CONTEXTO_EMPRESA.md), regras relevantes (R##), condição contratual do lojista e o dossiê do grupo. Nada além disso.
- **Saída por grupo:** `resumo` (1 frase), `hipoteses[]` {causa, fatos_citados[F#], confianca alta|media|baixa}, `conferir[]`, `falar_com` (Orbe | Ponte | Comercial | Lojista), `alerta_dado_faltante` (o que a IA precisaria saber e não tem).
- **Guarda-corpos no código:** descarta hipótese que cite fato inexistente ou nenhum fato; limita a 3 hipóteses; marca tudo como "sugestão da IA, não verificada"; timeout e erro → mensagem "IA indisponível; dossiê disponível".
- **Chave:** variável `ANTHROPIC_API_KEY` ou arquivo `.env` na raiz (no .gitignore). Biblioteca `anthropic` como dependência **opcional**: sem ela, o fechamento roda igual.
- **Prompt versionado** em arquivo, para revisão humana.

### Fase 3 — Tela e decisão da analista
- Interface: cartão "Investigação de divergências", com um bloco por grupo: fatos à esquerda, hipóteses à direita, botão "Gerar hipóteses com IA" (desabilitado sem chave, com explicação).
- Por hipótese: [Aceitar] [Recusar] + comentário; nome da analista no topo da tela.
- Grava `decisoes_investigacao.csv`: grupo, hipótese, decisão, comentário, analista, data/hora, modelo usado.
- Linha de comando: `python -m src.fechamento --ia` gera o dossiê e as hipóteses em arquivo (sem decisão).

### Fase 4 — Validação
- **Testes do dossiê** contra fatos conhecidos: Rota começa em 12/09 com +0,50 p.p. constante em 3 modalidades; Bridge cobra a taxa da vigência anterior de 15 a 18/09; Casa cobra a taxa cheia em 100% das transações; Mundo Aberto = 1,5% padrão.
- **Testes da IA com resposta simulada** (sem rede): hipótese sem fato é descartada; sem chave o fluxo segue; os 6 CSVs são idênticos com e sem `--ia`.
- **Auditor independente:** confere cada fato do dossiê contra os arquivos brutos e julga se as hipóteses de uma execução real fazem sentido.
- **Uma execução real** com a chave do time, salva como exemplo em `docs/exemplo_investigacao_ia.md` (a banca pode não ter chave).

### Fase 5 — Documentação
- README: onde pôr a chave; como rodar com e sem IA.
- COMO_USAR: como ler o cartão e decidir.
- HIPOTESES: premissas da IA (modelo, limites, guarda-corpos).
- PITCH: slide "onde a IA atua e onde não atua", com o exemplo real.
- MOMENTOS: candidato a momento de IA (ex.: hipótese descartada pelo guarda-corpo).

## Execução (agentes)
| Ordem | Agente | Escopo | Paralelo? |
|---|---|---|---|
| 1 | Dev A | Fases 0 e 1 (determinístico) | sim, com o Dev B |
| 1 | Dev B | Fase 2 contra o schema do dossiê definido aqui, com dossiê de exemplo fixo | sim, com o Dev A |
| 2 | Dev A | Fase 3 (tela e CLI), integrando A e B | depois de 1 |
| 3 | Auditor | Fase 4 | depois de 2 |
| 3 | Documentador | Fase 5 | junto com o Auditor |

## Fora do escopo da v1 (evolução)
Spreads negativos e outras pendências no dossiê; rascunho de contestação (use case 2); aprendizado com as decisões passadas; histórico de vários meses como fato.

## Decisões necessárias do time
1. Chave da Anthropic para a execução real e o exemplo (sem chave: entregamos dossiê + simulação, e a parte IA fica não demonstrada).
2. Confirmar Sonnet 5.5 como modelo.
