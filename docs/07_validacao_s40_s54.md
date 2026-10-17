# Validação independente — regras S40 a S54 (fechamento set/2026)

Auditoria feita em 17/10/2026 por auditor que **não importou `src/`**: os números foram recalculados a partir dos brutos (`01` + `06` Orbe, planilha `02`, anexo do `.eml` da Ponte) com scripts próprios (`Decimal`, `ROUND_HALF_UP` por linha). O código do projeto só foi executado pela linha de comando (`python -m src.fechamento --entrada ... --saida ...`) e pelo `pytest`. Nada em `src/`, `app/`, `tests/`, `saida/`, nos documentos existentes ou nos dados foi alterado; o `.env` não foi lido. Cenários parciais e a simulação de outubro rodaram em cópias fora do repositório.

## Resultado

| # | Verificação | Resultado | Evidência |
|---|---|---|---|
| 1a | Comissão checkout 203.735,34 em 1.900 transações | OK | recalculado 203.735,34 / 1.900; os 21 lojistas e as 1.900 linhas do rastro batem com o meu cálculo, transação a transação. Atlas (57 linhas) fora, por falta de contrato |
| 1b | Notas checkout 203.740,84 (20) | OK | 20 lojistas com saldo positivo; Casa fecha em −5,50 e não emite |
| 1c | Remessa 39.543,45, nota única | OK | 228 operações (233 linhas − 1 duplicada PC-0926-0162 − 4 negativas), 50% por operação, half-up |
| 1d | Divergências checkout 16.973,65 (210) | OK | 210 transações idênticas uma a uma, mesmo valor por linha (Casa 118 = 15.397,42; Rota 87 = 1.546,28; Bridge 5 = 29,95) |
| 1e | Divergências remessa 1.418,85 (23) | OK | 23 operações da Mundo Aberto, fórmula (spread % − contratado) × PTAX × ME. Nenhuma outra operação passa de R$ 0,74 de diferença, que é arredondamento |
| 2 | S51 devolver ao lojista | OK | Casa 15.396,77; Rota 1.545,86; Bridge 29,94 (Σ valor_taxa − comissão contratada nas linhas divergentes). Mundo Aberto 1.418,88 (Spread R$ − contratado × PTAX × ME, por operação; a fórmula % dá 1.418,85). Iguais em `pendencias.csv` e `investigacao/dossie.json` (G01 a G04) |
| 3 | S43 spread negativo, os dois valores | OK | PC-0926-0210 −687,52 / −1.351,87; 0326 −509,22 / −1.001,29; 0491 −292,28 / −574,91; 0545 −345,03 / −637,91. Totais −1.834,05 / −3.565,98. `valor_brl` de cada pendência = diferença até o contratado; o rastro soma o mesmo valor; o motivo traz o realizado |
| 4 | S42/S50 alerta de antecipação | OK | Aplicando o critério a todos os 22 ECs, só a Atlas acende (nova: primeira transação 10/09, sem referência anterior ao mês; saldo líquido de antecipação > vendas acumuladas). Bagagem Livre também é "nova", mas não antecipou acima das vendas. Regra antiga (antecipação acumulada > vendas acumuladas, qualquer lojista) acenderia 6: Oxford, Dublin Hub, Mundo Aberto, Kiwi, Canguru e Atlas, o mesmo que o PITCH diz |
| 5a | Rastro fecha para todo `id_saida` | OK | 491 ids; nenhum sem rastro, nenhum órfão, nenhuma soma diferente do valor reportado |
| 5b | Formato oficial dos 6 CSVs | OK | `;`, ponto decimal, datas AAAA-MM-DD, CNPJ de 14 dígitos, colunas obrigatórias na ordem do edital, UTF-8 sem BOM, ids únicos, `metodo` e `banco` válidos, `confianca` entre 0 e 1 |
| 6a | Parcial sem o `.eml` | OK | Sem stack trace. Checkout (comissões, notas, 210 divergências) idêntico ao completo. Remessa ausente com pendência `FONTE_AUSENTE`. As 85 linhas do Meridiano ligadas à Ponte ficam `HUMANO` / 0,60 / "conciliação bloqueada", com o mesmo valor e a mesma conta. Notas e comissões com `status=PROVISORIO` |
| 6b | Parcial sem o OFX do Meridiano | OK | Checkout, remessa, Aurora e divergências idênticos ao completo. Meridiano ausente, pendência `FONTE_AUSENTE` clara |
| 6c | Parcial sem a planilha de taxas | OK com ressalvas | Remessa (14 comissões, nota 39.543,45) e extratos idênticos ao completo; checkout bloqueado. Ressalvas nos achados 3 e 6 |
| 6d | Orbe 01 com coluna renomeada | FALHA (MÉDIO) | Pendência `LAYOUT_INESPERADO` clara e sem stack trace, mas o checkout sai calculado só com o arquivo de ajustes (achado 1) |
| 6e | Execução completa idêntica a `saida/` | OK | Os 6 CSVs, `dossie.json` e `dossie.md` idênticos byte a byte; ainda idênticos depois do `pytest` |
| 6f | Rastro fecha nos parciais | OK com ressalva | Fecha em todos os ids, exceto a própria pendência de bloqueio (achado 2) |
| 7 | S40 ajuste da Ponte em outubro simulado | OK | Relatório simulado de 10/2026 com a linha "AJUSTE REF PC-0926-0434", Spread R$ −235,74. Comissão de remessa caiu 117,87 (39.543,45 → 39.425,58), nota única da Ponte 39.425,58 com "ajustes de contestação da Ponte: R$ -117,87 (ref. PC-0926-0434)". O rastro (comissão, nota e 2 pendências) cita `ajuste de PC-0926-0434: 50% de Spread R$ -235.74`. A pendência `AJUSTE_PONTE_APLICADO` registra a premissa aberta (spread inteiro ou participação). A linha de ajuste não vira divergência nem spread negativo |
| 8a | `pytest -q` na pasta real | OK | 148 passed |
| 8b | Segurança: chave real fora do `.env` | OK | Nenhuma chave real. `.env` está no `.gitignore` e fora do índice; só `.env.example` é versionado, com `sk-or-...`. Um falso positivo, no achado 4 |

## Achados

### MÉDIO

**1. Relatório principal da Orbe ilegível deixa o arquivo de ajustes ser calculado sozinho.**
Cenário (d): `01_orbe...csv` com `valor_bruto` renomeado para `valor_total`, `06_orbe_ajustes...csv` intacto. O programa avisa (`LAYOUT_INESPERADO`, "Bloqueado: comissões, notas e divergências do checkout não calculadas"), mas continua e calcula o checkout só com as 14 linhas do `06`:
- o resumo imprime `Comissão CHECKOUT: R$ -3.304,39 (7 lojistas, 14 transações)` e `Notas CHECKOUT: R$ 174,81 (1 notas)`, contradizendo o próprio aviso;
- `comissoes_por_lojista.csv` traz 7 lojistas do checkout com valores parciais; `notas_a_emitir.csv` traz uma nota de Kiwi Experience de R$ 174,81 (o certo é R$ 10.886,22). Ambos com `status=PROVISORIO`, mas a nota é emitível por engano;
- 6 pendências `SALDO_CHECKOUT_NAO_POSITIVO` falsas, e um grupo de investigação gerado do arquivo parcial.

Correção: quando qualquer arquivo Orbe falha (layout ou leitura), bloquear o checkout inteiro, sem comissões, notas, divergências nem pendências derivadas. Usar o `06` só se o `01` foi lido. O teste novo é `tests/test_layout.py`: incluir a asserção de que `comissoes_por_lojista.csv` não tem linha CHECKOUT nesse cenário.

### BAIXO

**2. A pendência de bloqueio não tem linha no rastro.**
Em todos os cenários parciais, `PEN-0001` (`FONTE_AUSENTE` ou `LAYOUT_INESPERADO`, valor 0,00) não aparece em `rastro.csv`. É o único id sem rastro. Correção: gravar uma linha `PEN-0001;<arquivo esperado>;<nome ou padrão>;0.00;fonte ausente`.

**3. Resumo da tela/CLI e alerta de antecipação sem a planilha de taxas.**
Sem `02`, o resumo mostra `Divergências REMESSA: R$ 0,00 (0 linhas)` em vez de `BLOQUEADO`; um zero pode ser lido como "conferido e sem divergência". Além disso, o alerta de antecipação da Atlas (que só depende da Orbe) some junto com o checkout. Correção: marcar a divergência de remessa como BLOQUEADO nesse caso; calcular `ALERTA_ANTECIPACAO` mesmo sem taxas.

**4. Texto com formato de chave em `docs/06_validacao_ajustes.md`, linha 44.**
Um exemplo falso `sk-or-v1-C…` (mais de 20 caracteres) está no documento e no commit 97e3991. Não é chave real, mas um scanner acusa e a banca pode estranhar. Correção: trocar por `sk-or-<chave>`; o histórico git continua com o texto, inofensivo.

**5. Dois números de "pico" da Atlas convivem na documentação.**
`HIPOTESES.md` H15, `PERGUNTAS_SLACK.md` e `docs/01_entendimento_dados.md` falam em R$ 179.592,82 contra vendas de R$ 55.357,50 (15/09, dia de maior excesso: 124.235,32). A pendência `PEN-0006`, o `PITCH.md` e `REGRAS_DE_NEGOCIO.md` OC05 usam o pico líquido de R$ 183.581,24 em 24/09 contra R$ 109.719,61 (excesso 73.861,63), que é o critério S50. Os dois estão certos para o que descrevem. Correção: uma frase em H15 dizendo que ele é anterior a H28 e que o valor reportado é o do pico líquido.

### Sem achado crítico
Nenhuma divergência de valor em comissões, notas, divergências, devoluções, spreads negativos ou rastro do fechamento completo.

## Observações (não são defeito)
- Sem o `.eml`, 85 lançamentos do Meridiano (PIX de lojistas para remessa e TEDs à Ponte) passam a `HUMANO` com confiança 0,60 por não haver como conciliar; valor e conta não mudam. Comportamento coerente com S53.
- O Spread R$ do ajuste da Ponte foi tratado como spread inteiro (50% = −117,87), como pedido na S40; a pergunta de 12:04 do Desbravadores segue sem resposta e a premissa está escrita na pendência.
- Scripts da auditoria: `scratchpad/auditoria_s40/` (`aud_checkout.py`, `aud_remessa.py`, `aud_antecip.py`, `aud_comparar.py`, `aud_parcial.py`, `mk_cen.py`, `mk_outubro.py`), fora do repositório.
