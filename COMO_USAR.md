# Como usar no fechamento do mês (guia da analista)

Este guia é para quem fecha o mês no financeiro. Não precisa saber programar. A instalação (feita uma vez) está no `README.md`.

## Jeito mais fácil: dois cliques em `fechar_mes.bat`

> **Atualizou o programa?** Feche todas as janelas pretas abertas e dê dois cliques em `fechar_mes.bat` de novo. Uma janela antiga continua mostrando a versão anterior (por exemplo, a aba Clientes aparece vazia).
Não precisa abrir terminal nem digitar comando.

1. Na pasta do programa, dê **dois cliques em `fechar_mes.bat`**. Abre uma janela preta e, em seguida, o navegador com a tela **"Fechamento mensal — Tarvo"**. **Deixe a janela preta aberta** enquanto usa a tela (fechá-la encerra o programa).
2. **Passo 1 da tela, Arquivos de entrada**: arraste os arquivos do mês para a área tracejada, todos de uma vez se quiser (ou clique nela para escolher). A lista mostra um ✓ verde, o nome e o tamanho de cada arquivo reconhecido, e "faltando" no que ainda não chegou. Os nomes precisam seguir a tabela da seção 1 abaixo. Um arquivo que não for reconhecido aparece num aviso amarelo e não é usado. Mandou o arquivo errado? Envie o certo por cima (ele substitui o anterior) ou clique em **Limpar e recomeçar**.
3. **Passo 2, Rodar o fechamento**: o botão só acende quando os arquivos do mês estão reconhecidos (pelo menos 1 da Orbe mais os outros 5). Clique e espere alguns segundos. Aparece o resumo: competência, comissão de checkout e de remessa, notas a emitir, divergências, lançamentos e pendências por responsável. Se algo der errado, aparece uma caixa vermelha explicando o que o programa não conseguiu ler.
4. **Passo 3, Arquivos para baixar**: os 6 CSVs, cada um com o número de linhas e uma frase do que contém, e um botão **Baixar**. **Baixar tudo (.zip)** traz os 6 de uma vez. Logo abaixo aparecem as primeiras pendências, que são o primeiro arquivo a olhar (seção 4).
5. **Passo 4, Investigação de divergências**: fatos de cada divergência e, se a IA estiver configurada, hipóteses de causa para você aceitar ou recusar (seção "Investigação de divergências" abaixo).
6. Para abrir os CSVs no Excel, siga a seção 3 abaixo.
7. Terminou: feche a janela preta.

Onde ficam os arquivos: cada vez que você usa a tela, o programa guarda uma cópia do que você enviou e o que ele gerou em `execucoes\<data_hora>\entrada` e `execucoes\<data_hora>\saida`, dentro da pasta do programa (o caminho aparece no rodapé da tela). Os arquivos originais que você enviou não são alterados.

Se a janela preta disser **"Não encontrei um Python com as bibliotecas necessárias"**, a instalação do `README.md` ainda não foi feita neste computador: peça a quem mantém o programa. Se o navegador não abrir sozinho, copie o endereço que aparece na janela preta (algo como `http://127.0.0.1:8765/`) para o navegador. A tela só funciona neste computador, não fica acessível pela rede.

As seções abaixo explicam o mesmo processo pela linha de comando e como ler cada arquivo.

## Investigação de divergências: como ler e decidir
Aparece na tela como **Passo 4**, depois que o fechamento roda. Serve para descobrir **por que** cada divergência aconteceu antes de falar com a Orbe, a Ponte ou o Comercial. Nada aqui muda os arquivos do fechamento.

- **Um bloco por grupo** (parceiro × lojista × natureza). No cabeçalho: lojista, parceiro, natureza (*divergência de contrato* = cobrar o parceiro e devolver ao lojista; *isenção não informada ao parceiro* = só devolver ao lojista), quantidade e os valores **devolver ao lojista** e **recuperar do parceiro**.
- **Fatos (esquerda)**: calculados pelo programa a partir dos arquivos (datas, faixas afetadas e não afetadas, diferença em p.p., se a taxa cobrada bate com outra vigência, com a aba antiga ou com o spread padrão…) e as respostas do financeiro (S##) que tocam o caso. São os mesmos de `saida/investigacao/dossie.md`, que funciona sem IA.
- **Hipóteses (direita)**: clique em **Gerar hipóteses com IA**. Leva alguns segundos por grupo ("Analisando…"). Cada hipótese mostra a causa provável, os fatos que ela cita (passe o mouse para destacá-los à esquerda) e a confiança. O grupo mostra também o que conferir, com quem falar, que dado falta, o modelo que respondeu e o aviso "Sugestão da IA, não verificada". Hipótese que não cita fato do grupo é descartada pelo programa. Se a IA falhar num grupo, o erro aparece só nele.
- **Botão desabilitado?** A IA não está configurada neste computador (o motivo aparece em amarelo). Os fatos continuam na tela. Para habilitar, veja "Investigação com IA (opcional)" no `README.md`.
- **Decidir**: escreva **seu nome** no topo (fica lembrado neste navegador). Em cada hipótese, se quiser, um comentário, e **Aceitar** ou **Recusar**. Pode mudar de ideia: vale a última decisão. A decisão fica gravada com nome, data e hora em `execucoes\<data_hora>\decisoes_investigacao.csv`, e as hipóteses em `investigacao_ia.json` na mesma pasta. **Baixar decisões (.csv)** traz o arquivo. Gerar as hipóteses de novo apaga as decisões daquela execução.
- A IA **não decide, não altera valores, não fecha pendência e não envia nada**. Quem confere e fala com o parceiro é você.

## Aba "Clientes": ver um lojista e registrar mudança de taxa

No topo da tela há duas abas: **Fechamento** (o de sempre) e **Clientes**.

1. Em **Clientes**, busque o lojista por nome, CNPJ ou código do EC da Orbe e clique nele. Os selos mostram o que merece atenção: "isenção ativa", "taxa especial", "bloqueado", "sem contrato".
2. A ficha traz, num lugar só: identificação (razão social da planilha, CNPJ, EC Orbe e, se você já rodou o fechamento, os nomes que o lojista tem na Orbe e na Ponte), **taxas que valem hoje** por faixa com "de onde vem" (planilha linha X ou cadastro C00X), condições comerciais (vigentes e encerradas, com quem aprovou e a fonte), como o lojista é faturado, as regras que se aplicam e o resumo do mês.
3. **+ Nova condição**: escolha o tipo, a linha, as faixas, o valor em %, a vigência, **quem aprovou** (obrigatório para taxa e isenção: Comercial ou Helena) e **seu nome**. **Encerrar** (nas condições ativas) pede a data de fim; só dá para antecipar o fim, não adiar.
4. Nada disso altera a planilha de taxas do cliente: as mudanças ficam em `cadastro/condicoes_comerciais.csv`, com o histórico em `cadastro/historico_alteracoes.csv`. **Depois de salvar, rode o fechamento de novo para aplicar.**

## 1. Juntar os arquivos do mês
Crie uma pasta só para o mês, por exemplo `C:\Fechamento\2026-10`, e coloque nela os **arquivos do mês** (1 de cada tipo, exceto a Orbe, que pode mandar mais de um), sem abrir, sem editar e sem renomear de forma que perca a palavra-chave do nome:

| Arquivo | De onde vem | O nome precisa conter |
|---|---|---|
| Relatório de comissões da Orbe (.csv), mais os arquivos de ajuste que ela mandar no mês (.csv) | Portal da Orbe | `orbe` |
| Planilha de taxas contratadas (.xlsx) | Planilha do financeiro | `taxas` |
| E-mail da Ponte Câmbio com o relatório anexo (.eml) | Caixa de entrada: salvar o e-mail inteiro ("Salvar como" .eml) | qualquer nome terminando em `.eml` |
| Plano de contas (.csv) | ERP Fênix | `plano_de_contas` |
| Extrato Aurora (.csv) | Internet banking Aurora | `aurora` |
| Extrato Meridiano (.ofx) | Internet banking Meridiano | qualquer nome terminando em `.ofx` |

Os nomes que os sistemas já usam servem (ex.: `01_orbe_relatorio_comissoes_out2026.csv`). Só pode haver **um** arquivo de cada tipo na pasta, **exceto a Orbe**: ela às vezes manda um segundo arquivo no mês com ajustes tardios (estornos, reversões de antecipação, vendas). Basta incluí-lo na pasta (ou arrastá-lo na tela) com `orbe` no nome; o programa lê todos os arquivos `orbe` em ordem de nome, soma as linhas e o `rastro.csv` aponta o arquivo certo de cada transação. Se o mesmo `id_transacao` aparecer duas vezes, conta uma só e abre a pendência `ORBE_LINHA_DUPLICADA`; se uma venda ou antecipação for estornada/revertida duas vezes, a segunda não é aplicada e abre a pendência `ORBE_ESTORNO_DUPLICADO`.

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
- `divergencias_taxa.csv`: transação por transação onde a Orbe ou a Ponte cobrou diferente do contrato. Base para devolver ao lojista e cobrar o parceiro. Estorno de uma venda cobrada a mais aparece com sinal negativo, então a soma por lojista é o líquido (setembro: R$ 16.973,65 no checkout, R$ 1.418,85 na remessa). O valor a devolver ao lojista nas pendências usa o que o parceiro descontou de fato (S51): pode diferir em centavos da soma desta lista, que segue a fórmula. Spread negativo da Ponte não aparece aqui: está em pendências, para contestar.
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
| **EC faltando na planilha** | Preencher o EC na planilha (melhor) ou, se não der, incluir o de-para EC → CNPJ na aba **Clientes** (cadastro de condições, C###). |
| **Lojista saiu** | Riscar a linha (tachado). Linha riscada é ignorada. |
| **Spread de remessa padrão** | Deixar em branco ou escrever "padrão" = 1,5%. |
| **Taxa digitada como texto ("1,49%") ou CNPJ sem zero** | Funciona, a solução corrige. Mas o ideal é padronizar. |

## Quando falta um arquivo ou o layout muda

O programa **avisa em vez de quebrar** e não segura o mês inteiro. Se um arquivo não está na pasta, ou veio com colunas
diferentes das esperadas (nome trocado, coluna removida), ele fecha o que não depende daquilo:

| Falta / mudou | O que fica bloqueado | O que continua saindo |
|---|---|---|
| Orbe (nenhum arquivo) ou taxas | comissões, notas e divergências do **checkout** | remessa, lançamentos |
| E-mail da Ponte | nota da Ponte e comissões de **remessa**; conciliação de TED/PIX da Ponte | checkout, lançamentos |
| Plano de contas | todos os **lançamentos** classificados | checkout, remessa |
| Extrato Aurora **ou** Meridiano | só os lançamentos daquele banco | o outro banco, checkout, remessa |

No resumo e na tela aparece o aviso grande **FECHAMENTO PARCIAL — bloqueado: ...**. Os 6 arquivos são gerados com o
que foi possível; `notas_a_emitir.csv` e `comissoes_por_lojista.csv` ganham a coluna `status = PROVISORIO` (no fechamento
completo essa coluna não existe). Cada bloqueio vira uma pendência em `pendencias.csv`, valor 0, **quem decide: Helena**:

- `FONTE_AUSENTE`: diz qual arquivo falta e o que ficou sem calcular.
- `LAYOUT_INESPERADO`: lista as colunas que faltam e as que foram encontradas.

Na tela, o botão "Rodar fechamento" liga com pelo menos um arquivo reconhecido e mostra antes "faltam: ... — o
fechamento será parcial". Para virar definitivo: enviar o arquivo certo e rodar de novo. A liberação do que saiu
provisório é da Helena.

## 7. Mudar uma regra (para quem mantém o programa)
Todas as regras ficam em `src/config.py`, cada uma com o código da regra (R##) ou da premissa (H##).

| Quero mudar... | Edite em `src/config.py` |
|---|---|
| Um lojista que não pode ser faturado (sem contrato) ou liberar a Atlas | Aba **Clientes** (condição C005 em `cadastro/condicoes_comerciais.csv`) |
| Período de taxa zero de um lojista (acordo comercial, ex.: Casa do Estudante, condição C001) | Aba **Clientes**, com quem aprovou e a vigência |
| De-para de EC Orbe sem código na planilha (C002 a C004) | Aba **Clientes** |
| Percentual da Tarvo no spread de remessa (hoje 50%) | `PARTICIPACAO_REMESSA` |
| Spread padrão (hoje 1,5%) | `SPREAD_PADRAO` |
| Tolerância para divergência de remessa (hoje 0,01 p.p.) | `TOLERANCIA_SPREAD` |
| CNPJ/nome da Ponte Câmbio na nota | `CNPJ_PONTE`, `NOME_PONTE` |
| Conta contábil de um tipo de lançamento, ou ensinar um lançamento novo | `REGRAS_EXTRATO` (descrição → conta; a primeira regra que casar vence) |
| Janela para casar PIX de lojista com remessas (hoje 7 dias) | `JANELA_PIX_REMESSA_DIAS` |
| Nome de quem decide nas pendências | `QUEM_HELENA`, `QUEM_COMERCIAL`, `QUEM_RISCO`, `QUEM_HELENA_COMERCIAL` |
| Respostas do financeiro (S##) mostradas no dossiê de investigação, por lojista | `RESPOSTAS_FINANCEIRO`, `TEXTOS_FINANCEIRO` |
| Nome dos arquivos de entrada | `PADROES_ARQUIVOS` |

Depois de mudar: rodar `python -m pytest -q` (148 testes, inclusive um outubro simulado; todos devem passar) e o fechamento de novo, e registrar a mudança em `HIPOTESES.md`/`REGRAS_DE_NEGOCIO.md` (regra geral) ou no cadastro de condições (condição de cliente). O que aconteceu no mês fica em `docs/fechamento_2026-09.md` (um registro por fechamento).

## 8. Quando a solução não resolve sozinha
Nesses casos ela **não inventa**: separa o caso, explica o motivo e indica quem decide. Tipos de pendência em `pendencias.csv`:

| Tipo | O que significa | Quem decide | O que fazer |
|---|---|---|---|
| `DIVERGENCIA_TAXA_CHECKOUT` | A Orbe cobrou de um lojista taxa diferente da contratada (natureza CONTRATO). Valor = total líquido do lojista. | Helena | Devolver ao lojista e recuperar da Orbe o valor indicado: o descontado de fato menos a comissão contratada (R60, R74). Lista em `divergencias_taxa.csv` (`cobrar_parceiro` = S). |
| `DEVOLUCAO_LOJISTA_ISENCAO` | Concessão comercial fora do contrato que ninguém avisou à Orbe (ex.: Casa do Estudante): a Orbe cobrou o contratado (o contrato decide, S41). **Não entra na cobrança da Orbe.** | Helena / Comercial | Devolver ao lojista (R52). Detalhe em `divergencias_taxa.csv` (`natureza` = ISENCAO_NAO_INFORMADA, `cobrar_parceiro` = N). |
| `SALDO_CHECKOUT_NAO_POSITIVO` | Lojista fechou o mês com comissão zero ou negativa: não sai nota, saldo não transporta. | Helena | Decidir o tratamento. |
| `LOJISTA_SEM_CONTRATO` | Lojista sem contrato vigente (Atlas). Fora das comissões e das notas. Valor = taxa que a Orbe cobrou, só referência. | Comercial | Confirmar a taxa; depois liberar em `ECS_BLOQUEADOS`. |
| `TAXA_CONTRATADA_INDEFINIDA` | A planilha não permite achar a taxa (EC sem linha, vigência não reconhecida, faixa sem taxa). | Comercial | Corrigir a planilha e rodar de novo. |
| `ALERTA_ANTECIPACAO` | Só lojista novo (sem histórico antes do mês) cuja antecipação acumulada, líquida de reversões, passou das vendas acumuladas (ex.: Atlas, pico em 24/09; critério H28). | Helena / Comercial | Avaliar o risco (R54). |
| `PARCELAMENTO_ACIMA_12X` | Venda parcelada em mais de 12x (a Tarvo não vende acima de 12x). Fora das comissões e das notas. | Helena / Comercial | Esclarecer com o lojista/Orbe (R57). |
| `DIVERGENCIA_SPREAD_REMESSA` | A Ponte aplicou spread acima do contratado. Valor cheio pago a mais pelo lojista. | Helena | Devolver ao lojista e recuperar da Ponte (R60); contestar com a Ponte. |
| `EXCESSO_NA_NOTA_REMESSA` | A nota da Ponte inclui a metade da Tarvo sobre esse excesso. | Helena | Se a Ponte devolver, ajustar no mês da devolução. |
| `SPREAD_NEGATIVO` | Operações com spread negativo (trava vencida), uma pendência por lojista com as operações no motivo e no rastro. Fora da comissão e da nota. O motivo traz dois valores rotulados: o spread realizado e a diferença até o contratado (`valor_brl`, o que se pede à Ponte; S43). | Helena | Contestar com a Ponte (R53, R69). |
| `ORBE_LINHA_DUPLICADA` | Mesmo id em dois arquivos da Orbe com valores diferentes: vale o último arquivo (o de ajuste) e a pendência mostra os dois valores (H31). | Helena | Conferir qual valor vale. |
| `FONTE_AUSENTE` / `LAYOUT_INESPERADO` | Um arquivo não veio ou mudou de layout. O fechamento sai parcial: o que depende da fonte fica bloqueado e as notas e comissões ganham `status = PROVISORIO` (S53, H32). | Helena | Providenciar o arquivo certo e rodar de novo; Helena libera o parcial. |
| `OPERACAO_DUPLICADA` | Nº de operação repetido no relatório da Ponte. Contado uma vez. | Helena | Pedir correção do relatório à Ponte. |
| `REMESSA_FORA_COMPETENCIA` | Operações do relatório da Ponte contratadas em outro mês (o mês do fechamento vem sempre da Orbe). Ficam fora da comissão e da nota; sai 1 pendência por mês de contratação, e o resto do fechamento roda. | Helena | Verificar se o relatório da Ponte recebido é o do mês certo. |
| `REMESSA_SEM_CONTRATO` | CNPJ de remessa sem linha válida na planilha: comissão contada, divergência não verificada. | Comercial | Cadastrar o lojista. |
| `CONFERIR_REPASSE_PONTE` | O TED da Ponte deve vir pelo valor da nota. O motivo mostra quanto daria 50% do total bruto do relatório da Ponte (que inclui duplicata e spreads negativos) e a diferença para a nota (em setembro, R$ 506,65). | Helena | Conferir o TED quando cair, sem presumir desconto. |
| `CREDITO_NAO_IDENTIFICADO` | Crédito sem pagador identificado. Não é receita. | Helena | Identificar e reclassificar. |
| `DEVOLUCAO_REPASSE` | Repasse a lojista que voltou. | Helena | Confirmar motivo e repagar. |
| `ACOMPANHAR_REMESSA_FUTURA` | PIX de lojista na conta de remessas sem operação Ponte no mês: adiantamento para remessa do mês seguinte (S22). Conta 2.1.02.001, lançamento HUMANO com confiança 1,00. | Helena | Conferir se a operação aparece no relatório da Ponte do mês seguinte; se não aparecer, falar com o lojista. |
| `TRANSFERENCIA_EM_TRANSITO` | Transferência entre contas sem par no outro banco dentro do mês. | Helena | Conferir no extrato do mês seguinte. |
| `TED_PONTE_NAO_CONCILIADO` | TED à Ponte não bate com as operações do dia. | Helena | Conferir com a Ponte. |
| `LANCAMENTO_NAO_CLASSIFICADO` | Descrição de extrato que nenhuma regra conhece. Lançado provisoriamente em 1.1.09.002. | Helena | Definir a conta; pedir a inclusão da regra em `REGRAS_EXTRATO`. |
| `EXTRATO_NAO_FECHA` | Saldo inicial + movimentos ≠ saldo final do Aurora (arquivo incompleto?). | Helena | Baixar o extrato de novo. |

Regra geral: resolveu a pendência mudando a planilha ou a configuração → rode de novo; os números novos saem com o rastro atualizado.

Critérios novos de 17/10 (S40–S54, `REGRAS_DE_NEGOCIO.md` R67–R76): devolver ao lojista = o que o parceiro descontou de fato menos a comissão contratada (Casa R$ 15.396,77; a lista `divergencias_taxa.csv` segue a fórmula e soma R$ 15.397,42); o contrato decide quem deve, não o aviso, e a Casa é concessão fora do contrato; alerta de antecipação só para lojista novo (em setembro, só a Atlas); com fonte ausente ou layout inesperado o fechamento sai **parcial**, com `status = PROVISORIO` e pendência `FONTE_AUSENTE`/`LAYOUT_INESPERADO`.
