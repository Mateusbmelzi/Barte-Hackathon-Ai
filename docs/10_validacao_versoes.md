# Validação independente: reenvio de arquivos (versões)

Auditoria feita em cópias da pasta de entrada (nada do projeto foi alterado, sem IA, tela em porta livre ≠ 8765). Comando: `python -m src.fechamento --entrada <pasta> --saida <pasta>`.

## Resultado por cenário

| # | Cenário | Resultado |
|---|---|---|
| 1 | Base (7 arquivos) | OK. Os 6 CSVs e o dossiê saem idênticos byte a byte a `saida/`. |
| 2 | Aurora v2 = original + 1 lançamento (saldo ajustado) | OK. 85 lançamentos Aurora, nada duplicado. Comissões, notas e divergências idênticas. As 85 referências Lnn do rastro apontam para a linha certa do v2 (conferidas por script; L93 = lançamento novo; L50, L65, L92 das pendências também). |
| 3 | Aurora v2 com 1 linha removida (BOLETO CONDOMINIO) | OK. 84 lançamentos (linha mantida), pendência `LANCAMENTO_SUMIU_NA_NOVA_VERSAO` (L16). Referências conferidas. |
| 4 | OFX v2 (DTSERVER posterior) com FITID novo e TRNAMT alterado | OK. 101 lançamentos (+1). `VERSAO_CONFLITANTE` mostra -129,90 → -139,90 e o fechamento usa -139,90. |
| 4b | Mesmo, mas com DTSERVER do "_v2" ANTERIOR ao do original | OK. A ordem segue o DTSERVER, não o nome: vale -129,90 e o FITID só existente no arquivo mais velho vira `LANCAMENTO_SUMIU` (mantido). |
| 5 | E-mail da Ponte reenviado idêntico com outro nome | OK. Remessa 39.543,45 inalterada, 228 operações, PC-0926-0162 contada uma vez (1 `OPERACAO_DUPLICADA`), pendências iguais. |
| 6 | Taxas v2 com Fluente crédito à vista 2,69% → 2,89% | OK. Comissão total sobe de 203.735,34 para 203.850,72 (+115,38). Esperado: bruto de vendas Fluente crédito à vista (30 vendas, R$ 57.690,93) × 0,2% = 115,38. Pendência `VERSAO_SUBSTITUIDA` presente. |
| 7 | Rastro fecha / formato oficial | OK em todos os cenários (c1 a c7): soma do rastro por id_saida = valor de comissões, notas e lançamentos, 240 a 241 linhas por cenário, zero divergências (o próprio fechamento também aborta com AssertionError se não fechar). |
| 8 | Tela (servidor em porta livre, mês 2026-09) | OK. 1º envio Aurora vira versão 1; o 2º (+1 linha) vira `_v2` com aviso; o 3º (idêntico ao v2) volta `duplicado: true` com aviso "arquivo idêntico ao já enviado em ..." e não é salvo. A pasta ficou com 8 arquivos + `_envios.csv` (sem `_v3`). Rodar: 85 lançamentos Aurora, bloco Versões com "usada ..._v2.csv (+1 lançamento novo)". Servidor encerrado. |
| 9 | `pytest -q` | OK. 266 passaram. |

Extra (c8): Aurora v2 com um lançamento CORRIGIDO (valor -28.450,00 → -28.540,00). O fechamento mantém os dois (85 lançamentos), gera `VERSAO_SOBREPOSTA` e `LANCAMENTO_SUMIU`. Comportamento coerente com "nada some em silêncio", mas ver BAIXO 3.

## Achados

Nenhum CRÍTICO. Nenhum MÉDIO.

### BAIXO
1. **Ids Lnn/LAN mudam entre versões.** Com +1 lançamento Aurora, todos os `LAN-00nn` do Meridiano deslocam em 1 (LAN-0085 vira LAN-0086). Quem anotou um id de uma execução anterior pode se confundir. Correção: citar sempre a chave natural (`ref_origem`) ao comunicar; ou numerar Meridiano antes do Aurora. Documentar no COMO_USAR.
2. **Reenvio idêntico da Ponte: o rastro passa a apontar o arquivo de nome posterior** (`03_email_ponte_reenviado.eml`), e não o original. Só muda o texto de `arquivo_origem`; valores iguais. Aceitável (empate de data resolve por nome). Se o aviso "mesmo conteúdo" fosse tratado como uma só versão, o nome original permaneceria.
3. **Lançamento corrigido na nova versão da Aurora fica em dobro até alguém agir** (valor antigo + novo, ambos contabilizados, com 2 pendências). Exemplo: BOLETO -28.450,00 e -28.540,00 no mesmo dia. É o desenho (nunca apagar em silêncio) e está sinalizado, mas o texto da pendência poderia sugerir "se for correção, remova a versão antiga na tela" para evitar fechar com o valor dobrado.
4. **Divergência negativa mostrada como "a devolver" (fora do escopo de versões).** No cenário 6 (taxa contratada maior que a cobrada) o PEN `DIVERGENCIA_TAXA_CHECKOUT` sai com valor -115,56 e texto "a devolver R$ -115,56". Cenário artificial, mas o texto deveria tratar valor negativo (Orbe cobrou a menos). Diferença de 0,18 entre -115,56 e o esperado 115,38 é truncamento da Orbe (S51).
5. **Aurora: empate de período usa ordem de nome.** Se o analista reenviar um extrato mais novo com nome que ordena antes do antigo e o mesmo "Período", a versão antiga é tratada como mais recente. Mitigado: o texto "usada/ignorada" e a união aparecem no bloco Versões. Correção opcional: desempatar pelo maior número de lançamentos ou pelo saldo final coerente.
