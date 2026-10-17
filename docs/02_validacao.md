# Validação independente do fechamento set/2026

Auditor: agente independente, 17/10/2026. Objetivo: tentar provar que as saídas em `saida/` estão erradas.
Método: recálculo do zero a partir dos 6 arquivos brutos, com scripts próprios (sem importar `src/` e sem reaproveitar testes). A planilha de taxas foi lida célula a célula (openpyxl, incluindo o tachado), o anexo xlsx foi extraído do `.eml` e o OFX foi lido com regex. A conta usa `Decimal` com `ROUND_HALF_UP` linha a linha.
Scripts em `scratchpad/auditoria/` (`base.py`, `a_check.py`, `a_check2.py`, `a_div.py`, `a_rem.py`, `a_rastro.py`, `a_fmt.py`, `a_ext.py`, `a_pix.py`, `a_tot.py`, `a_amostra.py`).

**Conclusão:** não encontrei nenhum número errado frente às regras confirmadas (R01–R44). O recálculo independente bateu ao centavo com as 21 comissões de checkout, as 14 de remessa, as 21 notas e as 210 + 23 divergências "reais". Os achados ficam em interpretação (hipóteses abertas que podem gerar alarme falso), no conteúdo das pendências e em pontos cosméticos.

## 1. Tabela de verificações

| # | Verificação | Resultado | Evidência |
|---|---|---|---|
| 1a | Separador `;`, ponto decimal, datas AAAA-MM-DD, CNPJ com 14 dígitos | OK | `a_fmt.py`: 0 problemas nos 6 CSVs. Todo campo numérico casa com `-?\d+(\.\d+)?`, todo CNPJ com `\d{14}` (inclusive 00520815000100, 03229837000103 e 08780784000120, que perdiam o zero na xlsx) |
| 1b | Colunas obrigatórias presentes e na ordem do edital (PDF págs 4–5) | OK | As colunas obrigatórias são as primeiras de cada arquivo, na ordem do edital. As extras vêm depois |
| 1c | Domínios (CHECKOUT/REMESSA, AURORA/MERIDIANO, REGRA/IA/HUMANO, confiança entre 0 e 1) | OK | 0 valores fora do domínio |
| 1d | `id_saida` único | OK | 0 duplicados entre os 5 arquivos de resultado |
| 1e | Encoding | OK (ver B1) | UTF-8 sem BOM, LF, sem mojibake |
| 2a | Soma do rastro por id_saida = valor reportado | OK | 35 comissões, 237 divergências, 21 notas, 18 pendências e 184 lançamentos: 0 diferenças, 0 ids sem rastro, 0 rastros órfãos |
| 2b | Todo `ref_origem` do rastro existe na origem | OK | 5.203 linhas: id_transacao na Orbe, nº de operação no xlsx, `L<n>` dentro do arquivo Aurora, FITID no OFX. Nenhuma ref inexistente |
| 2c | Nenhuma transação Orbe duplicada ou faltando | OK | Toda linha Orbe que não é da Atlas aparece em exatamente uma COM-CHK (1.886 linhas). Nenhuma linha Atlas entra. Toda ref pertence ao EC da comissão |
| 2d | Remessa sem duplicata nem negativos | OK | COM-REM e NF-0021 têm 228 operações únicas. PC-0926-0162 entra uma vez. Os 4 negativos ficam fora |
| 3 | Recálculo manual de lojistas inteiros | OK | Recalculei **todos** os 21 lojistas de checkout (não só 3), batendo comissão, qtd e parte de antecipação. Bridge 11.916,02: 15–18/09 a Orbe cobrou 2,59% contra 2,19% contratado (5 transações, 29,95). Rota Global 15.621,27: +0,5 p.p. desde 12/09, 87 divergências, 1.546,28. Kiwi 10.711,41: AN88445076/AN88445093 e AN88446468/AN88446631 se anulam, antecipação líquida 503,02. Oxford 16.077,90: estorno de agosto TX88444848 a 3,79%, −83,12. Total 207.039,73 |
| 3b | Planilha de taxas | OK | Faixas 2–6x e 7–12x, vigência Bridge "até 14/09" e "a partir de 15/09", Globo Trotter tachada e ignorada, Oxford/Sol Nascente em texto ("3,09%"), CNPJ numérico sem zero, ECs de Kiwi, Horizonte e Novo Horizonte pelo de-para S03 |
| 4 | Amostra aleatória de 30 transações Orbe (seed 20261017) | OK 30/30 | Taxa, comissão e divergência certas em todas. Inclui Casa a 0%, Rota a +0,5 p.p., parcelado 7–12x da EduAbroad a 3,49% e 3 linhas da Atlas, fora da comissão como deve |
| 4b | Integridade da Orbe | OK | `valor_taxa` = trunc(bruto × taxa aplicada) em 1.943/1.943 linhas, então não há divergência escondida no valor. Cada estorno e reversão bate com a venda ou antecipação original (data, modalidade, taxa, valor). 9 estornos de agosto têm a venda original fora do arquivo e usam a taxa de agosto |
| 5a | Remessa: 50% por operação | OK | Recálculo 39.543,45 em 228 operações, por lojista idêntico às 14 linhas COM-REM |
| 5b | Exclusões: 4 negativos e a duplicata PC-0926-0162 | OK | Negativos −1.834,05 fora. A duplicata (linhas Excel 76 e 77, idênticas, obs "reprocessada") conta uma vez. O TED de 22/09 (325.387,31) bate com as operações **sem** a duplicata, o que confirma que ela é só erro do relatório |
| 5c | Tolerância H06 e Mundo Aberto | OK | Fora da Mundo Aberto o maior desvio é 0,0016 p.p. (Maple, Kiwi). Mundo Aberto: 23 operações a ~1,50% contra 1,20%, total 1.418,85, recálculo idêntico por operação |
| 5d | Spread contratado ≠ 1,5% e "padrão" | OK | Nórdica 1,25%, EduAbroad 1,30%, Novo Horizonte 1,40% e Lisboa 1,60% foram aplicados certo pela Ponte (sem divergência). Canguru "padrão" e células em branco (Kiwi, Ponte Aérea) entram como 1,5% |
| 6a | 184 lançamentos (84 Aurora + 100 Meridiano), conta analítica | OK | Todas as 22 contas usadas são ANALITICA com ACEITA_LANCTO=S. Os 100 FITIDs e os 84 movimentos do Aurora estão presentes, com valor, data e descrição iguais à origem |
| 6b | `ref_origem` Aurora = linha física | OK | Conferi as 84 linhas por script e 5 à mão (`cat -n`): L9 TED Orbe 66.026,00; L10 TAR 389,00; L50 PIX 7.350; L65 devolução 12.400; L92 transferência 300.000 |
| 6c | Classificação R40–R44 / H10–H18 | OK (ver M4) | Folha, ISS, INSS, FGTS, IRRF, PIS e COFINS de agosto baixam o passivo. 04/09 MRD2026090132 baixa 1.1.03.002. Tarifas, condomínio, AWS, Google, contabilidade, seguro e IOF são despesa direta. Créditos Orbe vão para 1.1.03.001, aplicação/resgate para 1.1.02.001, rendimento para 3.2.01. TED Ponte: os 21 TEDs batem com Valor R$ + IOF do dia. PIX de lojista: recálculo próprio por CNPJ e janela, só o MRD2026090425 (18.240) fica sem operação |
| 7 | Notas | OK | 20 notas de checkout (lojistas com saldo > 0), Casa (−5,50) sem nota, Atlas sem nota, NF-0021 tomador 75374179000146 = 39.543,45 |
| 8 | Pendências | OK com ressalvas | As 18 têm motivo e quem_decide. Conteúdo: ver M1, M3, B3 |
| 9 | Robustez outubro (nomes diferentes) | OK com ressalva | Com nomes como `Orbe_Relatorio_Comissoes_OUT-2026.CSV`, `Tabela de Taxas (atualizada).xlsx`, `RE Relatorio mensal Ponte.eml` e `extrato AURORA out.csv`, as 5 saídas saem byte a byte iguais e o rastro difere só em `arquivo_origem`. Sem as palavras-chave no nome, o programa para com erro claro (ver B4) |
| 10 | `pytest -q` e `python -m src.fechamento` numa cópia limpa | OK | 28 passed. Numa cópia do projeto sem `saida/` as 6 saídas são regeneradas byte a byte iguais às entregues |

## 2. Achados

### CRÍTICO (número errado)
Nenhum. Todas as comissões, notas e divergências "pago a mais" batem com o recálculo independente.

### MÉDIO (classificação, rastro ou interpretação questionável)

**M1. Spread negativo lançado como divergência de taxa, com valor sem sentido de negócio.**
- Exemplo: DIV-0222 / PC-0926-0210 com diferenca_brl = **−1.351,87**. É o resultado de (−1,5523% − 1,5%) × PTAX × ME. O mesmo vale para DIV-0226 (−1.001,30), DIV-0233 (−574,90) e DIV-0236 (−637,91), somando −3.565,98.
- Efeito: o total de divergências de remessa no arquivo e no resumo do CLI fica em **−2.147,13**, quando o que o lojista pagou a mais (S10) é **+1.418,85**.
- Por que está errado: S05 trata o spread negativo como trava D-1 vencida a contestar da participação da Tarvo. O lojista não pagou a mais. É exatamente o risco de alarme falso que H08 (ABERTA) admite, e o edital pune alarme falso.
- Correção: tirar os 4 negativos de `divergencias_taxa.csv` e mantê-los só em PEN-0009..0012 (que já trazem o valor realizado e o D-1). Atualizar `test_divergencia_remessa` (27 → 23) e H08.

**M2. Estornos com divergência negativa (H02) em `divergencias_taxa.csv`.**
- 5 linhas, −107,53: DIV-0158 TX88446419 (−52,10), DIV-0163, DIV-0166, DIV-0176 (Rota) e DIV-0201 TX88446763 (Casa, −9,09).
- A regra é coerente com S01 (taxa aplicada ≠ contratada), e o líquido por lojista na pendência está certo.
- Risco: se o gabarito só lista cobranças a mais, viram 5 alarmes falsos.
- Sugestão: manter (é defensável), mas deixar explícito no README/pitch que 16.973,65 é líquido e 17.081,18 é bruto. Se P2 voltar contrária, remover as 5 linhas.

**M3. PEN-0014 (conferir repasse da Ponte) não avisa a diferença já previsível.**
- O próprio relatório da Ponte traz "Spread total R$: 78.073,59". Esse total inclui a duplicata (+821,88) e os negativos (−1.834,05), e 50% dele dá **39.036,80**, que é R$ 506,65 abaixo da NF-0021 (39.543,45). Também há R$ 0,57 de diferença porque a Tarvo arredonda os 50% operação por operação (S11).
- Correção: incluir no motivo da PEN-0014 que o TED provavelmente virá em ~39.036,80 e por quê (duplicata + negativos), para a Helena não estranhar nem aceitar o desconto sem contestar (S14).

**M4. MRD2026090425 (PIX de R$ 18.240,00 da "PONTE AEREA ESTUDANTIL") classificado com `metodo=REGRA` em 2.1.02.001.**
- Confirmei que nenhuma combinação de operações da Ponte Aérea explica o valor: as 15 operações dela são cobertas pelos outros 5 PIX, e só este fica sobrando.
- A conta é uma premissa (H10, ABERTA). Pela lógica do próprio código, que só marca REGRA quando a conciliação fecha, aqui caberia `HUMANO` ou `IA`.
- Correção: manter a conta, mas usar `metodo=HUMANO` e baixar a confiança, ou usar 1.1.09.002 até o lojista confirmar (mesmo critério do PIX de 7.350). Os casos L50 e L65 (REGRA com confiança 0,70) são aceitáveis porque a regra é explícita no Slack (S09).

### BAIXO (cosmético ou robustez)

**B1. Encoding.** Os CSVs são UTF-8 sem BOM. Para a correção automática isso é o ideal. Abertos por duplo clique no Excel PT-BR, os acentos aparecem quebrados ("IntercÃ¢mbio"). Não mudar o arquivo oficial; se quiser, gerar uma cópia `utf-8-sig` só para a Helena.

**B2. Nome do tomador nas notas.** As notas usam o apelido da planilha, não a razão social: NF-0002 "Kiwi Experience", NF-0006 "Vela", NF-0012 "Canguru", NF-0005 "Mundo Aberto", NF-0004 "EduAbroad", NF-0017 "Horizonte Viagens". O CNPJ está certo. Sugestão: razão social ("Kiwi Experience Turismo Ltda", da aba 2025 ou do cadastro), já que vai para nota fiscal.

**B3. PEN-0006 (risco de antecipação da Atlas), `quem_decide = Risco`.** O cliente não citou área de Risco (o time é Helena + Comercial). Os números conferem: 4 antecipações em 15/09 = 179.592,82, vendas até 15/09 = 55.357,50. Mas é uma pendência que ninguém pediu (H15) e pode contar como alarme. Sugestão: "Helena (Financeiro) / Comercial", com texto curto.

**B4. Descoberta de arquivos depende do nome.** O programa procura `*orbe*.csv`, `*taxas*.xlsx`, `*plano_de_contas*.csv`, `*aurora*.csv`, `*.eml` e `*.ofx`. Arquivos chamados `relatorio_comissoes_out2026.csv`, `tabela_tarifas.xlsx` ou `extrato_cc4471.csv` param o programa com `FileNotFoundError` claro (falha visível, não silenciosa). Sugestão: reconhecer pelo conteúdo (cabeçalho `id_transacao;data_movimento`, aba "Taxas vigentes", "Banco Aurora" na linha 1) ou documentar no README a regra de nomes para outubro.

**B5. Testes de "gabarito" são snapshot dos próprios números.** `tests/test_gabarito.py` confere os totais que o próprio código gerou (docs/01). Isso pega regressão, mas não prova correção. O recálculo desta auditoria é a prova independente. Sugestão: citar esta validação no README.

**B6. Cadastro da planilha.** Kiwi, Horizonte Viagens e Novo Horizonte continuam sem EC na planilha, e o código depende do de-para fixo em `config.py` (S03). Sugestão: uma pendência leve para a Bia preencher o EC na planilha. Assim outubro não depende do config.

## 3. Números conferidos (recálculo independente = saída)

| Item | Saída | Recálculo |
|---|---|---|
| Comissão checkout (21 lojistas, 1.886 linhas) | 207.039,73 | 207.039,73 |
| Notas checkout (20) | 207.045,23 | 207.045,23 (sem Casa −5,50) |
| Divergências checkout (210 linhas, líquido) | 16.973,65 | 16.973,65 (Casa 15.397,42; Rota 1.546,28; Bridge 29,95) |
| Comissão/nota remessa (228 operações) | 39.543,45 | 39.543,45 |
| Divergência Mundo Aberto (23 operações) | 1.418,85 | 1.418,85 (fórmula alternativa Spread R$ − 1,2%×PTAX×ME: 1.418,88) |
| Spread negativo (4 operações, realizado) | −1.834,05 | −1.834,05 |
| Atlas fora (57 linhas, bruto) | 262.138,61 | 262.138,61 |
