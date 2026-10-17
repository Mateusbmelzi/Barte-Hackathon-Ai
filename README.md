# Fechamento mensal Tarvo Pagamentos

Programa de linha de comando (Python + pandas) que lê os arquivos do fechamento **do jeito que chegam** (relatório Orbe, mais os arquivos de ajuste que ela mandar no mês, planilha de taxas, e-mail da Ponte Câmbio com anexo, plano de contas Fênix, extratos Aurora e Meridiano) e gera em `saida/` os 6 CSVs do formato oficial: comissões, divergências de taxa, notas a emitir, lançamentos classificados, pendências e rastro. Todo número de saída aponta para as linhas de origem (`rastro.csv`).

Todo o cálculo é feito por regras fixas, escritas em `src/config.py`. Nenhum número sai de IA/LLM.

## Como rodar (avaliadores)
**Os níveis mínimo e alvo (6 CSVs com rastro) rodam com um comando e não dependem de IA nem de chave; a investigação com IA é um complemento opcional.**

Testado do zero com Python 3.11 (pandas 2.2 e 3.0) e Python 3.14. Nenhuma chave de API é necessária.

1. Clonar e entrar na pasta:
   ```bash
   git clone https://github.com/Mateusbmelzi/Barte-Hackathon-Ai.git
   cd Barte-Hackathon-Ai
   ```
2. Criar o ambiente virtual e instalar as dependências:
   ```bash
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt      # Windows
   # .venv/bin/python -m pip install -r requirements.txt        # Linux/macOS
   ```
3. Rodar o fechamento (um comando, a partir da raiz do repositório):
   ```bash
   .venv\Scripts\python -m src.fechamento                       # Windows
   # .venv/bin/python -m src.fechamento                         # Linux/macOS
   ```
   Sem argumentos, lê os arquivos do case na raiz e **sobrescreve** os 6 CSVs de `saida/`. Para outro mês ou outra pasta: `--entrada <pasta com os arquivos do mês> --saida <pasta de saída>` (o nome de cada arquivo precisa conter a palavra-chave descrita em [Como rodar](#como-rodar)).
4. Comparar com o entregue: `git status --short saida/` (ou `git diff --stat saida/`) deve vir **vazio**, ou seja, os CSVs gerados são idênticos byte a byte aos do repositório. Testes: `.venv\Scripts\python -m pytest -q` (148 testes).

Alternativa sem terminal: `.venv\Scripts\python -m app` abre a interface no navegador (enviar os arquivos do mês, rodar, baixar os CSVs), ou dois cliques em `fechar_mes.bat` no Windows. Ver [Interface visual](#interface-visual-sem-terminal).

Se `.venv\Scripts\activate` for bloqueado pelo PowerShell (política de execução), não é preciso ativar: chamar `.venv\Scripts\python` direto, como acima, funciona.

Documentos relacionados:
- [COMO_USAR.md](COMO_USAR.md): passo a passo para a analista do financeiro
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md): regras confirmadas (R##), com a fonte
- [HIPOTESES.md](HIPOTESES.md): premissas assumidas (H##), perguntas feitas e respostas
- [CONTEXTO_EMPRESA.md](CONTEXTO_EMPRESA.md): a empresa, o processo atual e a causa raiz (1 página)
- [PERGUNTAS_SLACK.md](PERGUNTAS_SLACK.md): perguntas feitas ao financeiro (todas respondidas em 17/10)
- [PITCH.md](PITCH.md): roteiro do pitch
- [PROMPTS/MOMENTOS.md](PROMPTS/MOMENTOS.md): momentos de uso de IA
- [docs/00_slack_respostas_financeiro.md](docs/00_slack_respostas_financeiro.md): respostas do financeiro (S01–S54)
- [docs/01_entendimento_dados.md](docs/01_entendimento_dados.md): entendimento dos dados (layout, anomalias, gabarito)
- [docs/02_validacao.md](docs/02_validacao.md): validação independente (auditor)
- [docs/PLANO_IA_01_investigacao.md](docs/PLANO_IA_01_investigacao.md), [docs/04_validacao_ia.md](docs/04_validacao_ia.md) e [docs/exemplo_investigacao_ia.md](docs/exemplo_investigacao_ia.md): plano, auditoria e execução real da investigação com IA
- [PLANO.md](PLANO.md): plano de execução

## Pré-requisitos
- Python 3.11 ou superior (testado em 3.11 e 3.14)
- Dependências em `requirements.txt`: pandas (2.2 a 3.x, ambas geram os mesmos bytes), openpyxl, pytest

## Instalação do zero
```bash
git clone https://github.com/Mateusbmelzi/Barte-Hackathon-Ai.git
cd Barte-Hackathon-Ai
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```
Nota sobre o interpretador: use o `python` do ambiente virtual (ou outro que tenha as dependências instaladas). Se o `python` do PATH não tiver pandas, chame o interpretador certo pelo caminho completo, por exemplo `C:\caminho\python.exe -m src.fechamento ...`.

## Como rodar
```bash
python -m src.fechamento --entrada <pasta com os arquivos do mês> --saida <pasta de saída>
```
- Sem argumentos: entrada = raiz do repositório (onde está o data pack de setembro), saída = `saida/`.
- Os arquivos são achados por padrão de nome (`src/config.py`, `PADROES_ARQUIVOS`): o nome precisa conter `orbe` (.csv), `taxas` (.xlsx), `plano_de_contas` (.csv), `aurora` (.csv); o e-mail da Ponte é o único `.eml` e o extrato Meridiano o único `.ofx`. Deve haver exatamente 1 arquivo por padrão na pasta, **exceto a Orbe**: a Orbe pode mandar arquivos de ajuste no mês (mesmo formato), então vale 1 ou mais arquivos `*orbe*.csv` (`FONTES_MULTIPLAS`). Todos são lidos em ordem de nome e concatenados; o `rastro.csv` aponta o arquivo de cada transação. `id_transacao` repetido conta uma vez só (pendência `ORBE_LINHA_DUPLICADA`); estorno/reversão de original já estornada/revertida não é aplicado (pendência `ORBE_ESTORNO_DUPLICADO`; o parâmetro `APLICAR_ESTORNO_DUPLICADO` em `src/config.py` muda isso). Nada é fixo para setembro: a competência vem das datas da Orbe.
- O comando precisa ser executado a partir da raiz do repositório (`-m src.fechamento`); as pastas de entrada e saída podem estar em qualquer lugar.
- `rastro.csv` grava o nome do arquivo de origem de cada linha. Com os mesmos dados sob outros nomes, os outros 5 CSVs saem idênticos e o `rastro.csv` difere só nessa coluna.
- Ao final, o programa imprime um resumo (totais por linha de negócio, notas, divergências, lançamentos e pendências por responsável).
- Também grava `saida/investigacao/dossie.json` e `dossie.md`: fatos por grupo de divergência, sem nenhuma hipótese. A mesma entrada gera os mesmos bytes. `--ia` acrescenta hipóteses da IA fora de `saida/` (ver "Investigação com IA").
- Antes de gravar, o programa confere que a soma do rastro de cada número é igual ao número reportado, ao centavo. Se não for, ele para com erro.

## Interface visual (sem terminal)
Para a analista: dois cliques em **`fechar_mes.bat`** (Windows). Ele entra na pasta do projeto, procura um Python com pandas e openpyxl (nesta ordem: `.venv\Scripts\python.exe`, `C:\Users\<usuário>\AppData\Local\Python\bin\python.exe`, `py`, `python`), sobe a interface e abre o navegador. Se não achar, a janela fica aberta com a explicação.

Pela linha de comando:
```bash
python -m app                  # abre o navegador sozinho
python -m app --sem-navegador  # só sobe o servidor
```
- Página única em `http://127.0.0.1:8765/` (se a porta estiver ocupada, tenta 8766, 8767...). Escuta só em 127.0.0.1, então não fica acessível pela rede.
- Só biblioteca padrão (`http.server` + uma página HTML/CSS/JS). Nenhuma dependência nova. Fontes Inter/Outfit do Google Fonts, com fonte do sistema se estiver offline.
- Fluxo: enviar os arquivos do mês (arrastar e soltar; a Orbe pode ter mais de um) → **Rodar fechamento** → baixar cada CSV ou um .zip com todos. O arquivo enviado é reconhecido pelos mesmos padrões de nome de `config.PADROES_ARQUIVOS` (a interface usa a função de `src/leitores.py`). O botão só habilita com pelo menos 1 arquivo da Orbe e os outros 5 reconhecidos.
- A interface não calcula nada: chama `src.fechamento.executar()` no mesmo processo e mostra os mesmos totais do resumo da linha de comando. Um erro aparece como mensagem curta na tela (o stack trace vai só para a janela do terminal).
- Cada uso grava em `execucoes/<AAAA-MM-DD_HHMMSS>/entrada` (cópia dos arquivos enviados) e `/saida` (os 6 CSVs e o dossiê). Se a IA for usada, grava também `investigacao_ia.json` e `decisoes_investigacao.csv` na pasta da execução. `execucoes/` está no `.gitignore`.
- Cartão **Investigação de divergências**: fatos por grupo, botão **Gerar hipóteses com IA** (desabilitado sem chave, com o motivo), Aceitar/Recusar com comentário e **Baixar decisões (.csv)**.
- Código em `app/servidor.py` (servidor) e `app/pagina.html` (tela). Teste em `tests/test_app.py`.

## Quando falta um arquivo ou o layout muda

Fonte ausente ou com colunas diferentes não derruba o fechamento (S53): roda o que não depende dela, gera os 6 CSVs
com o possível, abre a pendência `FONTE_AUSENTE` ou `LAYOUT_INESPERADO` (valor 0, Helena decide) e mostra
**FECHAMENTO PARCIAL — bloqueado: ...** no resumo e na tela. `notas_a_emitir.csv` e `comissoes_por_lojista.csv`
ganham a coluna `status = PROVISORIO` só nesse caso; no fechamento completo os arquivos são idênticos aos de `saida/`.
Dependências: checkout = Orbe + taxas; remessa = e-mail da Ponte (divergência também precisa das taxas); lançamentos =
plano de contas + cada extrato (Aurora e Meridiano são independentes). Detalhes em `COMO_USAR.md`.

## Como testar
```bash
python -m pytest -q
```
148 testes. Rodam o fechamento numa pasta temporária (os arquivos originais não são tocados) e conferem:
- leitura dos arquivos, arredondamento, formato das saídas e soma do rastro;
- `tests/test_gabarito.py` e `tests/test_gabarito_independente.py`: totais de setembro e valores fixos por lojista auditados de forma independente (`docs/02_validacao.md`), conferidos contra os CSVs gerados;
- `tests/test_app.py`: sobe a interface numa porta livre, envia os arquivos, roda e confere os totais e que o CSV baixado é idêntico ao de `saida/`; também confere que um erro aparece sem stack trace.
- `tests/test_outubro_simulado.py`: uma cópia dos dados com as datas da Orbe deslocadas para outubro, um lojista novo fora da planilha e um lançamento de extrato desconhecido. Confere que a competência vira 10/2026, que o lojista novo vira pendência e fica fora da nota, que o lançamento vai para HUMANO, que a Casa do Estudante continua com taxa zero, que as remessas de setembro ficam fora de outubro e que o rastro fecha.

Resultado de setembro (para conferência): comissão checkout R$ 203.735,34 (21 lojistas, 1.900 transações, já com os 14 ajustes do arquivo `06_orbe_ajustes_tardios_set2026.csv`; MDR R$ 187.415,30 e antecipação R$ 16.320,04), remessa R$ 39.543,45 (228 operações), 21 notas (20 de checkout somando R$ 203.740,84, mais a da Ponte de R$ 39.543,45), divergências checkout R$ 16.973,65 em 210 transações (valor **líquido**: R$ 17.081,18 cobrados a mais menos R$ 107,53 de estornos dessas vendas, H02), divergência remessa R$ 1.418,85 em 23 operações (nas pendências, a devolução ao lojista usa o descontado de fato: Casa R$ 15.396,77, Rota R$ 1.545,86, Bridge R$ 29,94, Mundo Aberto R$ 1.418,88; spreads negativos: realizado −R$ 1.834,05 e diferença até o contratado −R$ 3.565,98), 184 lançamentos, 18 pendências.

Critérios novos de 17/10 (S40–S54, `REGRAS_DE_NEGOCIO.md` R67–R76): devolver ao lojista = o que o parceiro descontou de fato menos a comissão contratada (Casa R$ 15.396,77; a lista `divergencias_taxa.csv` segue a fórmula e soma R$ 15.397,42); o contrato decide quem deve, não o aviso, e a Casa é concessão fora do contrato; alerta de antecipação só para lojista novo (em setembro, só a Atlas); com fonte ausente ou layout inesperado o fechamento sai **parcial**, com `status = PROVISORIO` e pendência `FONTE_AUSENTE`/`LAYOUT_INESPERADO`.

## Chave de API
Nenhuma chave é necessária para o fechamento: ele roda offline. A chave só habilita a investigação com IA, que é opcional (seção abaixo).

## Investigação com IA (opcional)
O fechamento **não precisa** de chave nem de internet: os 6 CSVs e o dossiê de fatos (`saida/investigacao/dossie.json` e `.md`) saem iguais com ou sem IA. A IA (Claude Sonnet 5.5, `src/ia.py`, prompt em `src/prompts/`) só sugere hipóteses de causa para cada grupo de divergência. A analista aceita ou recusa cada uma na tela.

A IA é o mesmo modelo por dois caminhos; escolha **um** e coloque a chave no `.env` (copie de `.env.example`; `.env` está no `.gitignore`):
```bash
copy .env.example .env                       # Windows (Linux/macOS: cp .env.example .env)
```
| Opção | No `.env` | Instalar algo? | Modelo |
|---|---|---|---|
| **OpenRouter** | `OPENROUTER_API_KEY=sk-or-...` (uma chave `sk-or-` em `ANTHROPIC_API_KEY` também é reconhecida como OpenRouter) | **Não**: usa só a biblioteca padrão do Python | `anthropic/claude-sonnet-5.5` |
| **Anthropic direta** | `ANTHROPIC_API_KEY=sk-ant-...` | Sim: `pip install -r requirements-ia.txt` (biblioteca `anthropic`; só para esta opção) | `claude-sonnet-5-5` |

A chave também pode vir de variável de ambiente com o mesmo nome (tem precedência sobre o `.env`). Se as duas existirem, vale a do OpenRouter. O valor da chave nunca é impresso nem gravado. Não há troca automática para outro modelo: se o Sonnet 5.5 não responder, o grupo mostra o erro e o dossiê continua disponível. Detalhes e limites da IA: `HIPOTESES.md`, H26.

**Sem chave?** A banca pode ver uma execução real (OpenRouter, prompt `investigacao-v3`, os 4 grupos de setembro) em [docs/exemplo_investigacao_ia.md](docs/exemplo_investigacao_ia.md). A IA varia a cada execução; nenhum número oficial vem dela.

- **Tela:** cartão "Investigação de divergências" → **Gerar hipóteses com IA**. Sem chave (ou, na opção Anthropic direta, sem a biblioteca), o botão fica desabilitado com o motivo. As hipóteses vão para `execucoes/<execução>/investigacao_ia.json`. As decisões (aceitar/recusar, comentário, analista, data e hora, modelo, versão do prompt) vão para `execucoes/<execução>/decisoes_investigacao.csv`. Nada disso vai para `saida/`.
- **Linha de comando:** `python -m src.fechamento --ia` faz o fechamento normal e grava as hipóteses em `execucoes/cli_<data_hora>/investigacao_ia.json` (imprime o caminho). Sem chave, avisa e segue.
- A única outra conexão opcional é a das fontes do Google Fonts na interface, que cai para a fonte do sistema se estiver offline.

## Estrutura de pastas
```
README.md, COMO_USAR.md, PITCH.md, REGRAS_DE_NEGOCIO.md, HIPOTESES.md, PERGUNTAS_SLACK.md, PLANO.md
PROMPTS/           histórico das sessões de IA + MOMENTOS.md
docs/              respostas do financeiro, entendimento dos dados, validação
src/
  config.py        TODAS as regras de negócio parametrizadas (cada uma cita R## ou H##)
  leitores.py      leitura dos arquivos como vêm (encoding, CNPJ, taxas em texto, anexo do e-mail, OFX)
  dinheiro.py      Decimal e arredondamento meio-centavo-para-cima (ROUND_HALF_UP)
  checkout.py      comissão, divergências e pendências da Orbe
  remessa.py       participação no spread, divergências e pendências da Ponte
  extratos.py      classificação dos extratos no plano de contas + conciliações por valor e data
  saidas.py        escrita dos CSVs no formato oficial
  fechamento.py    linha de comando (--ia opcional)
  investigacao.py  dossiê determinístico de fatos por grupo de divergência
  ia.py, prompts/  hipóteses com IA (opcional; requirements-ia.txt só para a Anthropic direta)
app/               interface visual local (python -m app): servidor.py + pagina.html
fechar_mes.bat     atalho de dois cliques para a interface (Windows)
execucoes/         uma pasta por uso da interface (entrada + saida), fora do git
tests/             testes (pytest)
saida/             CSVs gerados
01_...05b_...      data pack de setembro (intocado)
```

## Arquivos de saída
Formato: separador `;`, ponto decimal, datas AAAA-MM-DD, CNPJ com 14 dígitos, UTF-8. Colunas obrigatórias primeiro; colunas extras no fim.

| Arquivo | Conteúdo |
|---|---|
| `comissoes_por_lojista.csv` | Uma linha por lojista e linha de negócio (CHECKOUT / REMESSA). Extras: nº de transações, EC Orbe, quebra MDR × antecipação, regra aplicada. |
| `divergencias_taxa.csv` | Uma linha por transação Orbe com taxa aplicada ≠ contratada, ou operação Ponte em que o lojista pagou spread acima do contratado, com a diferença em R$. Estorno de venda divergente entra com sinal negativo (H02). Spread negativo não entra aqui, só em pendências (H08). Extras: lojista, tipo, data, valor base, regra. |
| `notas_a_emitir.csv` | Uma nota por lojista com saldo de checkout positivo + uma nota para a Ponte Câmbio (remessa). Discriminação pronta. |
| `lancamentos_classificados.csv` | Cada movimento dos extratos Aurora (ref = linha física `L##`) e Meridiano (ref = FITID) com a conta do plano de contas, método (REGRA/IA/HUMANO) e confiança. Extras: nome da conta, regra, observação de conciliação. |
| `pendencias.csv` | O que precisa de uma pessoa: tipo, referência, valor, motivo e quem decide. |
| `rastro.csv` | Liga cada `id_saida` às linhas de origem (arquivo, referência, valor, detalhe). |

## Como a rastreabilidade funciona
Cada número de saída tem um `id_saida` (ex.: `COM-CHK-0005`, `DIV-0012`, `NF-0021`, `LAN-0040`, `PEN-0007`). Em `rastro.csv` há uma linha para cada linha de origem que compõe aquele número, com o nome do arquivo de origem, a referência (id_transacao Orbe, Nº Operação Ponte, `L##` do Aurora, FITID do Meridiano) e o valor que ela contribui. Filtrando `rastro.csv` por um `id_saida` e somando `valor`, obtém-se exatamente o número reportado. O programa verifica isso a cada execução. Pendências sem valor (ex.: "vigência não reconhecida") não aparecem no rastro.

## Limitações conhecidas
- **Classificação dos extratos por regras de texto (regex).** Um lançamento com descrição que nenhuma regra conhece cai em `1.1.09.002` com método HUMANO e vira pendência. É preciso acrescentar a regra em `config.REGRAS_EXTRATO`.
- **Sem conciliação Orbe × banco parcela a parcela** (S16): os créditos Orbe no Aurora são só classificados. Falta a agenda de recebíveis da Orbe.
- **Depende do layout dos arquivos.** Mudança de colunas, de nome de aba ("vigentes") ou de formato do anexo da Ponte, ou um arquivo que não chegou, não derruba o mês: o fechamento sai **parcial** (S53, R76). Fecha o que não depende da fonte, marca notas e comissões como `PROVISORIO`, bloqueia o resto e abre `FONTE_AUSENTE` ou `LAYOUT_INESPERADO` para a Helena. Ele não tenta adivinhar.
- **Planilha de taxas é manual.** O programa trata os defeitos atuais (CNPJ sem zero à esquerda, taxa em texto, "padrão", vigência em texto, linha riscada), mas um formato novo de vigência ou um EC sem código vira pendência, e o lojista fica fora da nota até alguém corrigir a planilha ou o de-para em `config.py`.
- **Premissas nossas.** As perguntas ao financeiro foram respondidas em 17/10 (S18–S54; H01, H02, H04, H08, H10, H14 e H15 viraram regra; H03 foi substituída por R52; H28–H34 são premissas novas, com H30, H33 e H34 ainda sem resposta). Seguem como decisão nossa, com o critério escrito, as premissas marcadas "Decidida" ou "Decisão do desenvolvedor" em `HIPOTESES.md` (ex.: H06 tolerância, H07 Spread %, H11–H13 contas). Mudando uma decisão, muda-se o parâmetro em `config.py` e roda de novo.
- **Competência** vem sempre da Orbe (mês mais frequente de `data_movimento`). Se o relatório da Ponte for de outro mês (ou trouxer operações de outro mês), essas operações ficam fora da comissão e da nota e viram **1 pendência por mês de contratação** (`REMESSA_FORA_COMPETENCIA`, H24); o resto do fechamento roda normalmente.
- Não emite nota fiscal nem faz lançamento no ERP: gera os arquivos para a analista conferir e lançar.
