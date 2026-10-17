# Validação independente do cadastro de condições comerciais

Escopo: condições por cliente saíram de `src/config.py` para `cadastro/condicoes_comerciais.csv` (`src/cadastro.py`); aba **Clientes** na tela grava nesse cadastro; a planilha 02 não é alterada. Tudo foi testado em cópias do projeto (sem `.env`, sem `saida/`); `src/`, `app/`, `tests/`, `saida/`, `cadastro/` e os dados reais não foram tocados (o `git status` ficou idêntico). Data da auditoria: 17/10/2026.

## Resultado por item

| # | Verificação | Resultado |
|---|---|---|
| 1 | Fechamento completo na cópia: 6 CSVs + `investigacao/dossie.json` + `dossie.md` idênticos byte a byte (`cmp`) à pasta real. Checkout 203.735,34; notas 203.740,84; remessa 39.543,45 | **OK** |
| 2 | Nada específico de cliente em `src/config.py` além de texto do financeiro | **OK com ressalva** (A1, A2) |
| 3a | Taxa especial Rota, crédito à vista 2,99% desde 12/09 | **OK** |
| 3b | Encerrar C001 em 15/09 | **OK** |
| 3c | Cadastro apagado | **OK, mas com risco** (A3) |
| 3d | Cadastro malformado | **OK** (A4: truncamento não é detectado) |
| 4 | Tela/API | **OK com defeito** (A5); planilha 02 com o mesmo SHA-256 antes e depois (d0c7d2b1...) |
| 5 | `pytest -q` na pasta real | **OK**: 204 passed |

## Detalhe dos testes

**1.** Cópia sem `.env` e sem `saida/`, `python -m src.fechamento --entrada . --saida saida`. Saída idêntica à real em: comissoes_por_lojista, divergencias_taxa, lancamentos_classificados, notas_a_emitir, pendencias, rastro, investigacao/dossie.json e dossie.md.

**2.** `grep` por CNPJ (14 dígitos), ECs e nomes em `src/*.py` (exceto `cadastro.py`) e `config.py`: nenhum lojista fora de `config.py`. Em `config.py` restam: `TEXTOS_FINANCEIRO` (texto S##, aceito pelo combinado) e `RESPOSTAS_FINANCEIRO`, que é uma tabela **por CNPJ** (ver A1). `CNPJ_PONTE` é do parceiro tomador da nota, não de lojista (aceitável).

**3a.** `cadastro.adicionar` (C007, TAXA_ESPECIAL, CREDITO A VISTA, 2,99, de 2026-09-12, aprovado_por Comercial). Resultado: divergências de Rota em crédito à vista (taxa 2,49 contra 2,99): 38 linhas, todas sumiram (49 linhas da Rota restantes: 31 de 2–6x e 18 de 7–12x, intactas). Comissão da Rota 15.621,27 -> 15.920,90 (**+299,63**); checkout total 203.735,34 -> 204.034,97 (+299,63), notas +299,63. Cálculo independente a partir dos CSVs da Orbe (vendas com `data_movimento` >= 12/09 e estornos com `data_venda_original` >= 12/09, 38 linhas, half-up por linha de bruto x 2,99% menos bruto x 2,49%): **299,63** (a soma sem arredondar dá 299,62, a diferença de 1 centavo é o arredondamento por linha, como manda a R01). Estornos de vendas anteriores a 12/09 e antecipações não mudam, conforme R11/R72.

**3b.** `cadastro.encerrar('C001', 2026-09-15)`. Casa passa a ter comissão **6.632,76** (era -5,50), 119 transações, e ganha nota (21 notas). Cálculo independente: vendas de 16 a 30/09 5.440,77 + antecipações 1.206,58 + estornos de vendas de 16/09 em diante -9,09 = 6.638,26, menos o estorno de venda de agosto (-5,50, já na base, pela taxa da planilha) = **6.632,76**. Confere. Vendas de 01 a 15/09 seguem isentas; checkout total 210.373,60.

**3c.** Sem a pasta `cadastro/`: o fechamento roda (exit 0), abre `PEN-0001 CADASTRO_AUSENTE` (valor 0, Helena/Comercial) e segue só com a planilha. Números mudam muito: checkout 203.735,34 -> **191.464,34**; Casa passa a ser faturada em **15.391,92** (devia ser zero); os três ECs do de-para (Novo Horizonte, Horizonte Viagens, Kiwi) e a Atlas caem em `TAXA_CONTRATADA_INDEFINIDA`; divergências do checkout 16.973,65 -> 1.576,23; o dossiê perde o grupo da Casa. A pendência diz com clareza que isenções, taxas especiais, de-para e bloqueios **não foram aplicados** e que "comissões, notas e divergências podem estar diferentes". Falta o essencial: ver A3.

**3d.** Casos testados via arquivo: data inválida, tipo inválido, cabeçalho errado, arquivo vazio, binário (não UTF-8), id duplicado, isenção sem aprovador: todos terminam com `ERRO: condicoes_comerciais.csv, linha N: ...` em português, exit 1, sem stack trace. Via `adicionar`: valor "abc", negativo, com vírgula, 250, faixa inválida, CNPJ de 13 dígitos, fim antes do início, sem lojista, faixa PIX em REMESSA, sem aprovador, data em dd/mm/aaaa: todos recusados com mensagem legível. Ressalva: a mensagem aparece com acentos corrompidos quando a saída é redirecionada no Windows (cp1252), no terminal interativo não foi avaliado (A6).

**4.** `python -m app --sem-navegador` em cópia (a 8765 já estava ocupada por outra instância, a minha subiu na 8766 sem interferir). `GET /api/clientes` (25 lojistas com selos), `GET /api/clientes/00520815000100` (ficha com taxas, origem "cadastro C001", condições, faturamento, regras), 404 legível para lojista inexistente. `POST /api/condicoes` sem `aprovado_por` e com aprovador inventado: 400 "Informe quem aprovou (Comercial ou Helena (Financeiro))..."; sem `usuario`: 400 "Informe seu nome..."; JSON inválido ou lista: 400 "Pedido inválido.". POST válido: linha C007 em `condicoes_comerciais.csv` e `CRIAR` no histórico com hora e usuário. Encerrar: sem usuário 400; C999 400 "Condição não encontrada."; adiar o fim 400 "só é possível antecipar o fim"; antecipar grava `ENCERRAR` no histórico. Observação com `;`, quebra de linha e aspas, e usuário com `;` e `\n`, foram escritos com aspas corretas e relidos sem perda; o fechamento seguinte rodou normalmente.

Navegador embutido, aba **Clientes** > Casa do Estudante: cabeçalho com selo verde "isenção ativa"; bloco de identificação (razão social na planilha, CNPJ 00.520.815/0001-00, EC 1018325654, observação da planilha "cliente estratégico - ver c/ comercial", nome na Orbe/Ponte "disponível depois de rodar o fechamento"); tabela "Taxas que valem hoje (17/10/2026)" com Débito, Crédito à vista, 2-6x, 7-12x, Pix e Antecipação em 0,00% com origem "cadastro C001 (isenção, aprovado por Comercial)" e Spread da remessa 1,50% com origem "planilha linha 13"; cartão da condição C001 (vigência 01/09/2026 a 31/12/2026, Aprovado por Comercial, Fonte S07/S47, registrada em 17/10/2026, campo "Encerrar em" + "Seu nome" + botão); "+ Nova condição"; "Como é faturado" (nota zerada pela R31; remessa na nota única da Ponte); regras R10, R11, R12, R30, R31, R20, R22, R32, R72, R52, R68; "Resumo do mês" pede rodar o fechamento. Sem rolagem horizontal (largura 1009 px).

## Achados

### MÉDIO

**A1. `RESPOSTAS_FINANCEIRO` ainda é configuração por cliente em `src/config.py`.** Mapeia (linha, CNPJ da Rota, da Casa, da Bridge, da Mundo Aberto) para S##, com nomes e ECs em comentário. O objetivo "nada de cliente em `config.py`" não está cumprido para esta tabela: um lojista novo ou um S## novo exige mexer em código. Correção: mover para o cadastro como condição `REFERENCIA_FINANCEIRO` (cnpj + linha + lista de S##), ou para um arquivo `cadastro/respostas_financeiro.csv`; manter só `TEXTOS_FINANCEIRO` (texto S##) em `config.py`.

**A2. Texto de regra sobre a Casa gravado no código da tela.** `app/servidor.py:397`: `"R72": "Isenção da Casa: vale para venda desde 01/09 ..."` aparece na ficha de **qualquer** lojista que tenha isenção (e a data 01/09 não vem do cadastro). Se a isenção da Casa mudar de data, a ficha continua dizendo 01/09. Correção: texto genérico ("Isenção com vigência: vale para venda a partir da data de início, e para antecipação pela data da antecipação") e a data lida da condição.

**A3. Cadastro ausente muda números sem sinal de provisório.** Exemplo medido em 3c: checkout cai 12.271,00 e a Casa (isenta) é faturada em R$ 15.391,92; as notas saem normais, sem `PROVISORIO` (esse status só existe no fechamento parcial por fonte ausente), exit code 0, e a pendência é uma entre 20, de valor 0,00. Quem emitir as notas pelo CSV não vê o aviso. Correção: tratar CADASTRO_AUSENTE como fonte bloqueada da S53 (mesma regra do fechamento parcial): marcar comissões e notas como `PROVISORIO`, ou não gerar `notas_a_emitir.csv`; no mínimo, imprimir o aviso no resumo do terminal e destacar na tela. Incluir na pendência o efeito medido (quantos lojistas/ECs ficaram sem taxa).

**A4. Truncamento ou perda de linhas do cadastro não é detectado.** Arquivo cortado no meio da C001 (`head -c 300`) foi lido como válido: C002 a C006 sumiram, o checkout caiu para 176.066,92 e o fechamento seguiu com exit 0 e sem aviso. O próprio `historico_alteracoes.csv` registra C001 a C006 como CRIAR; ninguém cruza. Correção: na leitura, conferir que todo `id_condicao` com ação CRIAR no histórico existe no cadastro (e que o histórico ENCERRAR bate com `vigencia_fim`); divergência = erro legível ("o cadastro perdeu C002..C006 em relação ao histórico"). Opcional: gravar hash do cadastro no histórico a cada alteração.

**A5. Criar condição com várias faixas não é atômico.** Via API, TAXA_ESPECIAL com `faixas: ["PIX","CREDITO A VISTA"]` onde CREDITO A VISTA já tinha condição vigente: a resposta foi **400** ("Já existe a condição C007...") mas a linha de PIX foi gravada mesmo assim (C008, 2.99% de PIX da Rota, com histórico CRIAR). A analista vê erro, tenta de novo, e a taxa de PIX já está valendo sem ela saber. Correção: validar todas as faixas contra o cadastro antes de gravar qualquer linha (ou gravar em memória e escrever o CSV uma vez, desfazendo em caso de falha).

### BAIXO

**A6. Sem checagem de coerência entre cnpj, ec_orbe e nome do lojista em `adicionar`.** Foi aceita a C007 (isenção) com CNPJ e EC da Casa e `lojista` = "Rota" (por API de Python, fora da tela; a tela deriva os três da ficha e fica protegida). Também aceita isenção que se sobrepõe à C001 (a checagem de sobreposição cobre TAXA_ESPECIAL, DE_PARA_EC e BLOQUEIO, não ISENCAO). Correção: recusar quando cnpj/EC apontam para lojistas diferentes e incluir ISENCAO na checagem.

**A7. Retroatividade sem aviso.** Encerrar C001 em data passada (ex.: 10/09, depois de já ter fechado setembro) é aceito e só diz "Rode o fechamento de novo". A R03 diz que mês fechado não reabre. Correção: avisar, na resposta e na ficha, quando a vigência alterada atinge mês já fechado (há execução em `execucoes/` para a competência), e exigir observação.

**A8. "Taxas que valem hoje (17/10/2026)" usa a data de hoje, não a competência.** Em outubro, olhando setembro, a ficha da Casa mostraria a taxa da planilha se a C001 estiver encerrada, sem mostrar o que valeu em setembro. Correção: seletor de data de referência ou mostrar também "na competência do último fechamento".

**A9. Rótulos antigos CC## em textos de saída e comentários.** `comissoes_por_lojista.csv` traz "(CC01/CC04 cadastro)" na coluna de regra; `config.py` ainda cita "CC03/S05", "TAXA_ZERO_CHECKOUT" e `NATUREZA_ISENCAO` usa o nome antigo no comentário. Os IDs agora são C###; a rastreabilidade pelo texto fica confusa. Correção: trocar por "cadastro C###" e citar o id da condição aplicada. Cuidado: mudar o texto altera os CSVs (reexecutar a comparação byte a byte depois).

**A10. Acentos corrompidos nas mensagens de erro quando a saída do CLI é redirecionada no Windows.** `src/fechamento.py` reconfigura só o stdout para UTF-8; as linhas `ERRO:` saem pelo stderr e ficam em cp1252 quando redirecionadas. Correção: `sys.stderr.reconfigure(encoding="utf-8")` também.

## Pontos fortes confirmados

- Reprodução exata: migração sem alterar um byte dos 8 arquivos de saída.
- Precedência (isenção > taxa especial > planilha) e vigência por data da venda funcionam, inclusive para estornos (R11) e antecipações (R72).
- O cadastro só cresce: encerramento nunca apaga, só antecipa o fim; tudo fica no histórico com hora e usuário.
- Aprovação obrigatória validada no servidor, não só na tela.
- Planilha do cliente intacta (mesmo SHA-256 depois das gravações pela tela).
