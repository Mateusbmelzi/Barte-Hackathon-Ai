# 06 — Validação independente após o arquivo 06 (ajustes tardios da Orbe)

Auditor independente, 17/10/2026. Objetivo: tentar provar que `saida/` regerada com 01 + 06 está errada.
Método: recálculo do zero a partir dos brutos (01, 06, planilha 02 lida célula a célula com o tachado, anexo xlsx extraído do `.eml`, extratos 05a/05b), com scripts próprios que **não importam `src/`**, em `Decimal` com `ROUND_HALF_UP` linha a linha. Regras usadas: R01, R10–R13, R15, R50–R52, R59 e CC01/CC04/CC05/CC07. Scripts em `scratchpad/auditoria_06/` (`base.py`, `a_checkout.py`, `a_rastro_fmt.py`, `a_remessa.py`). Nenhum arquivo do projeto foi alterado (os testes rodaram sem mudar `saida/`; confirmado por md5 antes e depois).

**Conclusão: nenhum número errado.** Todos os totais esperados batem ao centavo. Os achados são só de documentação e higiene.

## 1. Tabela de verificações

| # | Verificação | Resultado | Evidência |
|---|---|---|---|
| 1a | Comissão checkout de todos os lojistas (01+06) = `comissoes_por_lojista.csv` | OK | Recálculo 203.735,34 em 1.900 linhas e 21 lojistas. Por lojista, comissão total, MDR, antecipação e quantidade batem em 21/21 (0 diferenças). Atlas (57 linhas) fica fora, como CC05/R15 |
| 1b | Notas de checkout | OK | 20 notas, 203.740,84; cada valor igual ao recálculo do lojista. Casa fecha em −5,50 e não tem nota (nem pendência de nota; vale R31) |
| 1c | Remessa | OK | 228 operações únicas (232 no xlsx, menos 1 duplicata PC-0926-0162 e 4 spreads negativos), 50% half-up por operação = 39.543,45; NF-0021 igual, tomador 75374179000146 |
| 1d | Divergências | OK | Checkout 210 linhas, líquido 16.973,65; as mesmas 210 refs, mesmos valores e mesma taxa contratada. Remessa 23 linhas, 1.418,85 (fórmula alternativa Spread R$ − 1,2%×PTAX×ME: 1.418,88; diferença de 0,03 de arredondamento, já conhecida) |
| 2a | As 14 linhas do 06: uma única comissão, taxa certa, rastro aponta o 06 | OK 14/14 | Taxa pela vigência da **data da venda original**: Dublin 2,59% (à vista), Maple débito 1,49% e à vista 2,69%, Mundo Aberto 2,49%, Bridge 3,19% (ambas parceladas), EduAbroad 3,19% (2–3x), Oxford 3,79% (9x) e 2,59%, antecipação 2,10% (Oxford ×2, Maple), Kiwi 3,19% (3x). Todas com `taxa_aplicada` = contratada, então nenhuma gera divergência. Rastro: `arquivo_origem = 06_orbe_ajustes_tardios_set2026.csv`, valor igual à comissão calculada |
| 2b | Nenhuma linha do 01 duplicada ou perdida | OK | 0 ids do 06 existem no 01. As 1.900 linhas não Atlas aparecem cada uma em exatamente um `COM-CHK` com arquivo e valor corretos (4.253 linhas de rastro do 01 + 28 do 06 = 14 comissões + 14 notas). Nenhum rastro do 01 aponta para o 06 e vice-versa |
| 3a | Rastro: soma por `id_saida` = valor reportado | OK | 491 ids (35 comissões, 233 divergências, 21 notas, 18 pendências, 184 lançamentos): 0 diferenças, 0 sem rastro, 0 rastros órfãos |
| 3b | Todo `ref_origem` existe no arquivo apontado | OK | 5.227 linhas de rastro: id_transacao no 01 ou no 06 (conforme o `arquivo_origem`), Nº Operação no xlsx do `.eml`, `L<n>` dentro do Aurora, FITID no OFX. 0 inexistentes; 0 também nos `ref_origem` das demais tabelas |
| 4 | Formato oficial dos 6 CSVs | OK | `;`, ponto decimal, datas AAAA-MM-DD, CNPJ `\d{14}`, UTF-8 sem BOM. Colunas obrigatórias na ordem do edital (págs 4–5), extras só depois. Domínios: `linha_negocio` CHECKOUT/REMESSA, `banco` AURORA/MERIDIANO, `metodo` REGRA/IA/HUMANO, confiança 0–1. `id_saida` sem repetição entre os 5 arquivos de resultado |
| 5a | Reprodutibilidade (cópia sem `.env`, sem `saida/`, `python -m src.fechamento`) | OK | Os 6 CSVs e `investigacao/dossie.json` e `dossie.md` ficam **idênticos byte a byte** (md5) à pasta real. A saída do CLI repete 203.735,34 / 39.543,45 / 203.740,84 / 16.973,65 / 1.418,85 |
| 5b | `python -m pytest -q` na pasta real | OK | 116 passed (8 s). `saida/` não mudou |
| 6 | Robustez: cópia SEM o 06 | OK | Volta a 207.039,73 (1.886 linhas) e notas 207.045,23 (20 notas), divergências iguais. O recálculo independente sem o 06 bate com a saída (0 diferenças, rastro íntegro) |
| 6b | Robustez extra: id do 01 repetido dentro do 06 | OK | Cópia com uma linha do 01 (TX88410128) reinserida no 06: total continua 203.735,34 / 1.900 e surge a pendência `ORBE_LINHA_DUPLICADA` (valor contado uma vez) |
| 7a | Chaves em arquivos versionados | OK | `git grep -E "sk-(or|ant)-[A-Za-z0-9_-]{20,}"` no working tree: 0. Em todos os commits (4): 0 |
| 7b | Chaves em arquivos não versionados, fora do `.env` | OK com ressalva (B2) | Só uma ocorrência com ≥20 caracteres: `tests/test_ia.py:198` (`CHAVE_OR`), valor visivelmente falso ("...CHAVE-FALSA-DE-TESTE-123"). Demais ocorrências são o prefixo em texto de exemplo (README, `.env.example`, docs, `src/ia.py`) |
| 7c | `.env` ignorado | OK | `git check-ignore -v .env` → `.gitignore:12`; `git ls-files` não o lista. Não foi lido. `.env.example` é versionável e só tem chaves vazias |

## 2. Achados

### CRÍTICO
Nenhum.

### MÉDIO
Nenhum.

### BAIXO

**B1. Manchete desatualizada em `docs/01_entendimento_dados.md`.**
- Exemplo: linhas 20–21 ainda trazem "R$ 207.039,73" e "R$ 207.045,23" como os totais do checkout; a linha 363 avisa, mais abaixo, que a análise é só com o 01. Quem ler só a tabela de abertura vê os números antigos. O mesmo vale para a tabela de lojistas (linha 390, "1.886 / 207.039,73").
- Correção sugerida: acrescentar na própria linha 20–21 "(só 01; com o 06: 203.735,34 / 203.740,84)", ou mover o aviso da linha 363 para o topo do arquivo.

**B2. Constante que parece chave em `tests/test_ia.py:198`.**
- Exemplo: `CHAVE_OR = "sk-or-teste (chave falsa, já encurtada)"` casa com o padrão `sk-or-` + 20 caracteres que um scanner (ou a banca) usaria. Não é chave real, mas gera alarme falso e a pessoa que revisar vai ter que abrir o arquivo para descobrir.
- Correção sugerida: montar o valor em tempo de execução (`"sk-or-" + "v1-falsa"`, ou `"sk-or-FALSA"`, com menos de 20 caracteres), ou deixar um comentário "valor fictício" na linha. O arquivo ainda é não versionado: vale incluí-lo no commit só depois dessa troca.

**B3. A duplicata entre arquivos Orbe é tratada pela 1ª ocorrência em ordem de nome, sem checar quem é o mais novo.**
- Exemplo: se um arquivo de ajuste reenviar um `id_transacao` do 01 com valor corrigido, vale a linha do 01 (nome vem antes) e a do 06 vai para `ORBE_LINHA_DUPLICADA` com `identica = false`. O comportamento é seguro (nunca conta em dobro e avisa), mas a Helena precisa decidir à mão.
- Correção sugerida: nenhuma obrigatória; basta deixar essa regra escrita em `COMO_USAR.md` ou H27 (hoje H27 descreve a leitura, não esse caso).

**B4. Um arquivo extra com `orbe` no nome entra no cálculo.**
- Exemplo: um `orbe_copia.csv` ou `orbe_backup.csv` colado na pasta é lido como ajuste. Como o id repetido vira duplicata (item 6b), o risco real é só de linhas novas indevidas.
- Correção sugerida: imprimir no CLI e no `rastro` a lista de arquivos Orbe lidos (o rastro já mostra o nome; falta uma linha no resumo do CLI: "Orbe: 2 arquivos").

## 3. Números conferidos

| Item | Saída | Recálculo independente |
|---|---|---|
| Comissão checkout (21 lojistas, 1.900 linhas) | 203.735,34 | 203.735,34 |
| Efeito do 06 sobre o checkout | −3.304,39 (207.039,73 → 203.735,34) | idem |
| Notas checkout (20) | 203.740,84 | 203.740,84 (sem Casa −5,50) |
| Divergências checkout (210, líquido) | 16.973,65 | 16.973,65 |
| Comissão/nota remessa (228 operações) | 39.543,45 | 39.543,45 |
| Divergência remessa Mundo Aberto (23) | 1.418,85 | 1.418,85 (alternativa 1.418,88) |
| Spreads negativos (4, fora da nota) | −1.834,05 | −1.834,05 |
| Sem o 06 (1.886 linhas / notas) | 207.039,73 / 207.045,23 | 207.039,73 / 207.045,23 |
