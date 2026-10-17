# Como usar no fechamento do mês (guia da analista)

Este guia é para quem fecha o mês no financeiro. Não precisa saber programar. A instalação (feita uma vez) está no `README.md`.

## 1. Juntar os arquivos do mês
Crie uma pasta só para o mês, por exemplo `C:\Fechamento\2026-10`, e coloque nela os **6 arquivos**, sem abrir, sem editar e sem renomear de forma que perca a palavra-chave do nome:

| Arquivo | De onde vem | O nome precisa conter |
|---|---|---|
| Relatório de comissões da Orbe (.csv) | Portal da Orbe | `orbe` |
| Planilha de taxas contratadas (.xlsx) | Planilha do financeiro | `taxas` |
| E-mail da Ponte Câmbio com o relatório anexo (.eml) | Caixa de entrada: salvar o e-mail inteiro ("Salvar como" .eml) | qualquer nome terminando em `.eml` |
| Plano de contas (.csv) | ERP Fênix | `plano_de_contas` |
| Extrato Aurora (.csv) | Internet banking Aurora | `aurora` |
| Extrato Meridiano (.ofx) | Internet banking Meridiano | qualquer nome terminando em `.ofx` |

Os nomes que os sistemas já usam servem (ex.: `01_orbe_relatorio_comissoes_out2026.csv`). Só pode haver **um** arquivo de cada tipo na pasta.

## 2. Rodar um comando
Abra o terminal na pasta do programa e rode:
```
python -m src.fechamento --entrada C:\Fechamento\2026-10 --saida C:\Fechamento\2026-10\saida
```
Leva poucos segundos. No fim aparece um resumo: comissão de checkout e remessa, valor das notas, divergências, quantidade de lançamentos e de pendências por responsável.

Se aparecer erro, ele diz o que faltou (ex.: "esperado 1 arquivo '*orbe*.csv', achei []" = o arquivo da Orbe não está na pasta ou tem outro nome). Nenhum arquivo é alterado.

## 3. Abrir os CSVs no Excel do jeito certo
Os arquivos usam **ponto e vírgula** como separador e **ponto** como decimal (formato exigido pela banca/sistemas). Se abrir com duplo clique, o Excel em português pode ler `1234.56` como texto ou data, e cortar o zero inicial do CNPJ. Use a importação:

1. Excel → **Dados** → **Obter Dados** → **De Arquivo** → **De Texto/CSV** → escolha o arquivo.
2. Origem do arquivo: **65001: Unicode (UTF-8)**. Delimitador: **Ponto e vírgula**.
3. Clique em **Transformar Dados**.
4. Colunas de CNPJ (`cnpj`, `tomador_cnpj`): botão direito → **Alterar Tipo** → **Texto** (mantém os 14 dígitos com zeros).
5. Colunas de valor (`comissao_brl`, `diferenca_brl`, `valor_brl`, `valor`, taxas): botão direito → **Alterar Tipo** → **Usando a Localidade...** → Tipo **Decimal**, Localidade **Inglês (Estados Unidos)**.
6. **Fechar e Carregar**.

Atalho: abrir com o Bloco de Notas mostra o arquivo exatamente como é, útil para conferir um valor.

## 4. O que olhar primeiro: `pendencias.csv`
É a lista do que a solução **não decide sozinha**. Cada linha tem o tipo, a referência, o valor, o motivo em português e **quem decide** (Helena/Financeiro ou Comercial). Comece por ela e distribua: cada responsável recebe as suas linhas.

Depois:
- `notas_a_emitir.csv`: as notas fiscais prontas (tomador, CNPJ, valor e texto da discriminação).
- `divergencias_taxa.csv`: transação por transação onde a Orbe ou a Ponte cobrou diferente do contrato. Base para devolver ao lojista e cobrar o parceiro. Estorno de uma venda cobrada a mais aparece com sinal negativo, então a soma por lojista é o líquido (setembro: R$ 16.973,65 no checkout, R$ 1.418,85 na remessa). Spread negativo da Ponte não aparece aqui: está em pendências, para contestar.
- `comissoes_por_lojista.csv`: comissão de cada lojista em cada linha de negócio.
- `lancamentos_classificados.csv`: os extratos com a conta contábil. Filtre `metodo` = HUMANO (a solução não sabe a conta) e depois `confianca` menor que 1 para revisar primeiro.

## 5. Como conferir um número
Todo número tem um código na coluna `id_saida` (ex.: `NF-0005`, `COM-CHK-0003`, `DIV-0012`).
1. Abra `rastro.csv` (passo 3) e filtre `id_saida` pelo código.
2. Cada linha mostra o arquivo de origem, a referência (id da transação Orbe, nº da operação Ponte, linha `L##` do extrato Aurora ou FITID do Meridiano) e quanto aquela linha contribui.
3. A soma da coluna `valor` dá exatamente o número reportado.
4. Para ir à fonte: procure a referência no arquivo original (ex.: `TX88410932` no relatório Orbe).

## 6. Quando a planilha de taxas muda
A solução lê a aba cujo nome contém "vigentes". Mantenha as colunas com os mesmos títulos.

| Situação | O que fazer |
|---|---|
| **Lojista novo** | Incluir uma linha na aba vigente com nome, CNPJ, **EC Orbe**, taxas e vigência. Sem EC, as transações dele não acham contrato e viram pendência `TAXA_CONTRATADA_INDEFINIDA` (fora da nota). |
| **Nova vigência de taxa** (mudou a taxa a partir de uma data) | Manter a linha antiga com vigência `até DD/MM/AAAA` e criar a nova com `a partir de DD/MM/AAAA` (ou só `DD/MM/AAAA`). São os únicos formatos reconhecidos. Outro texto → o lojista inteiro vira pendência ("vigência não reconhecida"), sem chute. |
| **EC faltando na planilha** | Preencher o EC na planilha (melhor) ou, se não der, pedir para incluir o de-para EC → CNPJ em `DEPARA_EC_CNPJ` (`src/config.py`). |
| **Lojista saiu** | Riscar a linha (tachado). Linha riscada é ignorada. |
| **Spread de remessa padrão** | Deixar em branco ou escrever "padrão" = 1,5%. |
| **Taxa digitada como texto ("1,49%") ou CNPJ sem zero** | Funciona, a solução corrige. Mas o ideal é padronizar. |

## 7. Mudar uma regra (para quem mantém o programa)
Todas as regras ficam em `src/config.py`, cada uma com o código da regra (R##) ou da premissa (H##).

| Quero mudar... | Edite em `src/config.py` |
|---|---|
| Um lojista que não pode ser faturado (sem contrato) ou liberar a Atlas | `ECS_BLOQUEADOS` |
| Período de taxa zero de um lojista (acordo comercial, ex.: Casa do Estudante) | `TAXA_ZERO_CHECKOUT` |
| De-para de EC Orbe sem código na planilha | `DEPARA_EC_CNPJ` |
| Percentual da Tarvo no spread de remessa (hoje 50%) | `PARTICIPACAO_REMESSA` |
| Spread padrão (hoje 1,5%) | `SPREAD_PADRAO` |
| Tolerância para divergência de remessa (hoje 0,01 p.p.) | `TOLERANCIA_SPREAD` |
| CNPJ/nome da Ponte Câmbio na nota | `CNPJ_PONTE`, `NOME_PONTE` |
| Conta contábil de um tipo de lançamento, ou ensinar um lançamento novo | `REGRAS_EXTRATO` (descrição → conta; a primeira regra que casar vence) |
| Janela para casar PIX de lojista com remessas (hoje 7 dias) | `JANELA_PIX_REMESSA_DIAS` |
| Nome de quem decide nas pendências | `QUEM_HELENA`, `QUEM_COMERCIAL`, `QUEM_RISCO` |
| Nome dos arquivos de entrada | `PADROES_ARQUIVOS` |

Depois de mudar: rodar `python -m pytest -q` (51 testes, inclusive um outubro simulado; todos devem passar) e o fechamento de novo, e registrar a mudança em `HIPOTESES.md`/`REGRAS_DE_NEGOCIO.md`.

## 8. Quando a solução não resolve sozinha
Nesses casos ela **não inventa**: separa o caso, explica o motivo e indica quem decide. Tipos de pendência em `pendencias.csv`:

| Tipo | O que significa | Quem decide | O que fazer |
|---|---|---|---|
| `DIVERGENCIA_TAXA_CHECKOUT` | A Orbe cobrou de um lojista taxa diferente da contratada. Valor = total líquido do lojista. | Helena | Decidir devolução ao lojista e cobrança da Orbe. Lista em `divergencias_taxa.csv`. |
| `SALDO_CHECKOUT_NAO_POSITIVO` | Lojista fechou o mês com comissão zero ou negativa: não sai nota, saldo não transporta. | Helena | Decidir o tratamento. |
| `LOJISTA_SEM_CONTRATO` | Lojista sem contrato vigente (Atlas). Fora das comissões e das notas. Valor = taxa que a Orbe cobrou, só referência. | Comercial | Confirmar a taxa; depois liberar em `ECS_BLOQUEADOS`. |
| `TAXA_CONTRATADA_INDEFINIDA` | A planilha não permite achar a taxa (EC sem linha, vigência não reconhecida, faixa sem taxa). | Comercial | Corrigir a planilha e rodar de novo. |
| `RISCO_ANTECIPACAO` | Lojista antecipou mais do que vendeu até a data (ex.: Atlas). | Helena / Comercial | Avaliar o risco. |
| `DIVERGENCIA_SPREAD_REMESSA` | A Ponte aplicou spread acima do contratado. Valor cheio pago a mais pelo lojista. | Helena | Contestar com a Ponte. |
| `EXCESSO_NA_NOTA_REMESSA` | A nota da Ponte inclui a metade da Tarvo sobre esse excesso. | Helena | Se a Ponte devolver, ajustar no mês da devolução. |
| `SPREAD_NEGATIVO` | Operação com spread negativo (trava vencida). Fora da comissão e da nota. | Helena | Contestar com a Ponte. |
| `OPERACAO_DUPLICADA` | Nº de operação repetido no relatório da Ponte. Contado uma vez. | Helena | Pedir correção do relatório à Ponte. |
| `REMESSA_FORA_COMPETENCIA` | Operações do relatório da Ponte contratadas em outro mês (o mês do fechamento vem sempre da Orbe). Ficam fora da comissão e da nota; sai 1 pendência por mês de contratação, e o resto do fechamento roda. | Helena | Verificar se o relatório da Ponte recebido é o do mês certo. |
| `REMESSA_SEM_CONTRATO` | CNPJ de remessa sem linha válida na planilha: comissão contada, divergência não verificada. | Comercial | Cadastrar o lojista. |
| `CONFERIR_REPASSE_PONTE` | O TED da Ponte deve vir pelo valor da nota. O motivo mostra quanto daria 50% do total bruto do relatório da Ponte (que inclui duplicata e spreads negativos) e a diferença para a nota (em setembro, R$ 506,65). | Helena | Conferir o TED quando cair, sem presumir desconto. |
| `CREDITO_NAO_IDENTIFICADO` | Crédito sem pagador identificado. Não é receita. | Helena | Identificar e reclassificar. |
| `DEVOLUCAO_REPASSE` | Repasse a lojista que voltou. | Helena | Confirmar motivo e repagar. |
| `PIX_LOJISTA_SEM_OPERACAO` | PIX de lojista na conta de remessas sem operação Ponte correspondente. O lançamento sai com método HUMANO. | Helena | Confirmar com o lojista e definir a conta. |
| `TRANSFERENCIA_EM_TRANSITO` | Transferência entre contas sem par no outro banco dentro do mês. | Helena | Conferir no extrato do mês seguinte. |
| `TED_PONTE_NAO_CONCILIADO` | TED à Ponte não bate com as operações do dia. | Helena | Conferir com a Ponte. |
| `LANCAMENTO_NAO_CLASSIFICADO` | Descrição de extrato que nenhuma regra conhece. Lançado provisoriamente em 1.1.09.002. | Helena | Definir a conta; pedir a inclusão da regra em `REGRAS_EXTRATO`. |
| `EXTRATO_NAO_FECHA` | Saldo inicial + movimentos ≠ saldo final do Aurora (arquivo incompleto?). | Helena | Baixar o extrato de novo. |

Regra geral: resolveu a pendência mudando a planilha ou a configuração → rode de novo; os números novos saem com o rastro atualizado.
