# Fechamento mensal Tarvo Pagamentos

Programa de linha de comando (Python + pandas) que lê os 6 arquivos do fechamento **do jeito que chegam** (relatório Orbe, planilha de taxas, e-mail da Ponte Câmbio com anexo, plano de contas Fênix, extratos Aurora e Meridiano) e gera em `saida/` os 6 CSVs do formato oficial: comissões, divergências de taxa, notas a emitir, lançamentos classificados, pendências e rastro. Todo número de saída aponta para as linhas de origem (`rastro.csv`).

Todo o cálculo é feito por regras fixas, escritas em `src/config.py`. Nenhum número sai de IA/LLM.

Documentos relacionados:
- [COMO_USAR.md](COMO_USAR.md): passo a passo para a analista do financeiro
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md): regras confirmadas (R##), com a fonte
- [HIPOTESES.md](HIPOTESES.md): premissas assumidas (H##), perguntas feitas e respostas
- [PERGUNTAS_SLACK.md](PERGUNTAS_SLACK.md): perguntas ainda abertas ao financeiro
- [PITCH.md](PITCH.md): roteiro do pitch
- [PROMPTS/MOMENTOS.md](PROMPTS/MOMENTOS.md): momentos de uso de IA
- [docs/00_slack_respostas_financeiro.md](docs/00_slack_respostas_financeiro.md): respostas do financeiro (S01–S17)
- [docs/01_entendimento_dados.md](docs/01_entendimento_dados.md): entendimento dos dados (layout, anomalias, gabarito)
- [docs/02_validacao.md](docs/02_validacao.md): validação independente (auditor)
- [PLANO.md](PLANO.md): plano de execução

## Pré-requisitos
- Python 3.10 ou superior
- Dependências em `requirements.txt`: pandas, openpyxl, pytest

## Instalação do zero
```bash
git clone <url-do-repositorio>
cd <pasta-do-repositorio>
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```
Nota sobre o interpretador: use o `python` do ambiente virtual (ou outro que tenha as dependências instaladas). Se o `python` do PATH não tiver pandas, chame o interpretador certo pelo caminho completo, por exemplo `C:\caminho\python.exe -m src.fechamento ...`.

## Como rodar
```bash
python -m src.fechamento --entrada <pasta com os 6 arquivos> --saida <pasta de saída>
```
- Sem argumentos: entrada = raiz do repositório (onde está o data pack de setembro), saída = `saida/`.
- Os arquivos são achados por padrão de nome (`src/config.py`, `PADROES_ARQUIVOS`): o nome precisa conter `orbe` (.csv), `taxas` (.xlsx), `plano_de_contas` (.csv), `aurora` (.csv); o e-mail da Ponte é o único `.eml` e o extrato Meridiano o único `.ofx`. Deve haver exatamente 1 arquivo por padrão na pasta.
- Ao final, o programa imprime um resumo (totais por linha de negócio, notas, divergências, lançamentos e pendências por responsável).
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
- Fluxo: enviar os 6 arquivos (arrastar e soltar) → **Rodar fechamento** → baixar cada CSV ou um .zip com todos. O arquivo enviado é reconhecido pelos mesmos padrões de nome de `config.PADROES_ARQUIVOS` (a interface usa a função de `src/leitores.py`). O botão só habilita com os 6 reconhecidos.
- A interface não calcula nada: chama `src.fechamento.executar()` no mesmo processo e mostra os mesmos totais do resumo da linha de comando. Um erro aparece como mensagem curta na tela (o stack trace vai só para a janela do terminal).
- Cada uso grava em `execucoes/<AAAA-MM-DD_HHMMSS>/entrada` (cópia dos arquivos enviados) e `/saida` (os 6 CSVs). `execucoes/` está no `.gitignore`.
- Código em `app/servidor.py` (servidor) e `app/pagina.html` (tela). Teste em `tests/test_app.py`.

## Como testar
```bash
python -m pytest -q
```
55 testes. Rodam o fechamento numa pasta temporária (os arquivos originais não são tocados) e conferem:
- leitura dos arquivos, arredondamento, formato das saídas e soma do rastro;
- `tests/test_gabarito.py` e `tests/test_gabarito_independente.py`: totais de setembro e valores fixos por lojista auditados de forma independente (`docs/02_validacao.md`), conferidos contra os CSVs gerados;
- `tests/test_app.py`: sobe a interface numa porta livre, envia os 6 arquivos, roda e confere os totais e que o CSV baixado é idêntico ao de `saida/`; também confere que um erro aparece sem stack trace.
- `tests/test_outubro_simulado.py`: uma cópia dos dados com as datas da Orbe deslocadas para outubro, um lojista novo fora da planilha e um lançamento de extrato desconhecido. Confere que a competência vira 10/2026, que o lojista novo vira pendência e fica fora da nota, que o lançamento vai para HUMANO, que a Casa do Estudante continua com taxa zero, que as remessas de setembro ficam fora de outubro e que o rastro fecha.

Resultado de setembro (para conferência): comissão checkout R$ 207.039,73 (21 lojistas), remessa R$ 39.543,45 (228 operações), 21 notas, divergências checkout R$ 16.973,65 em 210 transações (valor **líquido**: R$ 17.081,18 cobrados a mais menos R$ 107,53 de estornos dessas vendas, H02), divergência remessa R$ 1.418,85 em 23 operações, 184 lançamentos, 18 pendências.

## Chaves necessárias
Nenhuma. Não há chamada a API externa nem a LLM. Roda offline.

## Estrutura de pastas
```
README.md, COMO_USAR.md, PITCH.md, REGRAS_DE_NEGOCIO.md, HIPOTESES.md, PERGUNTAS_SLACK.md, PLANO.md
PROMPTS/           histórico das sessões de IA + MOMENTOS.md
docs/              respostas do financeiro, entendimento dos dados, validação
src/
  config.py        TODAS as regras de negócio parametrizadas (cada uma cita R## ou H##)
  leitores.py      leitura dos 6 arquivos como vêm (encoding, CNPJ, taxas em texto, anexo do e-mail, OFX)
  dinheiro.py      Decimal e arredondamento meio-centavo-para-cima (ROUND_HALF_UP)
  checkout.py      comissão, divergências e pendências da Orbe
  remessa.py       participação no spread, divergências e pendências da Ponte
  extratos.py      classificação dos extratos no plano de contas + conciliações por valor e data
  saidas.py        escrita dos CSVs no formato oficial
  fechamento.py    linha de comando
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
- **Depende do layout dos arquivos.** Mudança de colunas, de nome de aba ("vigentes") ou de formato do anexo da Ponte faz o programa parar com erro explicando o que não achou. Ele não tenta adivinhar.
- **Planilha de taxas é manual.** O programa trata os defeitos atuais (CNPJ sem zero à esquerda, taxa em texto, "padrão", vigência em texto, linha riscada), mas um formato novo de vigência ou um EC sem código vira pendência, e o lojista fica fora da nota até alguém corrigir a planilha ou o de-para em `config.py`.
- **Hipóteses abertas.** Alguns números dependem de premissas ainda não confirmadas pelo financeiro (H01, H02, H03, H08, H10–H13, H15; ver `HIPOTESES.md` e `PERGUNTAS_SLACK.md`). Mudando a resposta, muda-se o parâmetro em `config.py` e roda de novo.
- **Competência** vem sempre da Orbe (mês mais frequente de `data_movimento`). Se o relatório da Ponte for de outro mês (ou trouxer operações de outro mês), essas operações ficam fora da comissão e da nota e viram **1 pendência por mês de contratação** (`REMESSA_FORA_COMPETENCIA`, H24); o resto do fechamento roda normalmente.
- Não emite nota fiscal nem faz lançamento no ERP: gera os arquivos para a analista conferir e lançar.
