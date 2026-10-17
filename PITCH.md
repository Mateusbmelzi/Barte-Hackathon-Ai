# Pitch: pré-esboço (15 min, para Helena e o CFO da Tarvo)

Público: financeiro e CFO, não engenheiros. Todos os números vêm de `saida/*.csv` (fechamento de setembro/2026) e a origem de cada um está indicada. Formato: 9 slides, cerca de 1,5 min cada, mais as perguntas.

---

## Slide 1: Título
**Mensagem-chave:** O mês da Tarvo fecha numa regra escrita, não na cabeça de uma pessoa.
- Fechamento de setembro/2026: comissões, divergências, notas, lançamentos e pendências
- Cada número com o caminho até a linha de origem
- **Número de destaque:** R$ 243.284,29 em 21 notas fiscais a emitir (`notas_a_emitir.csv`)

> Nota do apresentador: abrir com a frase do time ("Se eu sair de férias, o mês não fecha") e dizer que o objetivo é que o mês feche com ou sem a pessoa.

---

## Slide 2: O que está quebrado, e por quê
**Mensagem-chave:** O problema não é falta de braço. É condição comercial que não chega ao parceiro, regra sem lugar, planilha sem chave e ninguém comparando contratado com cobrado.
- **Causa raiz: ninguém avisa os parceiros.** O Comercial fecha a condição e, "quando lembra", manda e-mail; ninguém tem essa função (S30). A Casa do Estudante (isenção) e a Mundo Aberto (spread 1,20%) não foram avisadas; a Bridge foi avisada dias depois de 15/09. Resultado: parceiro cobrando fora do contrato o mês inteiro, e o lojista recebendo a menos (S34).
- **O caso que prova a causa raiz: Casa do Estudante.** O Comercial fechou isenção de tarifa no checkout de setembro a dezembro (S07). O acordo não chegou à Orbe nem à planilha de taxas (S18, S30). Em setembro, a Orbe cobrou a taxa cheia em **118 transações: R$ 15.397,42 a devolver ao lojista**. Não há nada a recuperar da Orbe, porque ela cobrou certo pelo que sabia; o custo é todo da Tarvo (`divergencias_taxa.csv`, natureza ISENCAO_NAO_INFORMADA; PEN-0001).
- **Caso de apoio: Mundo Aberto.** Spread de 1,20% negociado em julho; a Ponte nunca foi avisada (S30) e aplicou o padrão de 1,50% em **23 operações: R$ 1.418,85** pagos a mais pelo lojista (`divergencias_taxa.csv`, REMESSA; PEN-0007).
- **Onde vão os ~8 dias hoje (S33):** checkout ~3 dias (metade casando nome com EC/CNPJ, metade refazendo conta por planilha desatualizada); remessa ~2 dias (esperando Ponte ou Comercial); extratos ~2 dias (linha a linha); último dia notas e revisão. Quase nada desse tempo é decisão.
- **Regras só na cabeça de uma pessoa:** taxa zero da Casa do Estudante, spread de 1,20% da Mundo Aberto, "spread negativo não se aceita", "operação repetida conta uma vez". Nada disso estava escrito; tivemos de perguntar (39 respostas no Slack, S01–S39). Nas férias da Helena, ninguém fecha (S32).
- **Planilha de taxas manual e sem chave confiável:** 3 lojistas sem código da Orbe (Horizonte Viagens, Kiwi, Novo Horizonte), CNPJ sem o zero inicial (Fluente, Campus Global), taxas digitadas como texto (Oxford Prep, Sol Nascente), Atlas Idiomas transacionando sem contrato vigente.
- **Ninguém compara taxa contratada × taxa cobrada:** a conferência é manual, arquivo por arquivo; só se descobre quando o lojista reclama.
- **Cobrança a mais sem ninguém notar:** Rota Global pagou +0,50 p.p. no crédito desde 12/09, contrato inalterado.
- **Ponte sem critério:** operação duplicada e spread negativo eram aceitos ou não "no feeling".
- **Número de destaque:** R$ 15.397,42 da Casa do Estudante: um acordo que não foi avisado vira 118 cobranças erradas em um mês (de 210 transações de checkout cobradas fora do contrato, `divergencias_taxa.csv`)

> Nota do apresentador: este é o slide da causa raiz. Automatizar o processo como ele é só faria o erro mais rápido. A correção foi tirar a regra da cabeça (REGRAS_DE_NEGOCIO.md, com quem aprovou e quando), a taxa da planilha solta e mostrar todo mês o que foi cobrado fora do contrato. O próximo passo é avisar o parceiro quando a condição muda (slide 8).

---

## Slide 3: O que a solução faz (em linguagem de financeiro)
**Mensagem-chave:** Você coloca os 6 arquivos do mês numa pasta e recebe o fechamento pronto para conferir.
- Lê os arquivos como chegam: relatório Orbe, planilha de taxas, e-mail da Ponte, plano de contas, extratos Aurora e Meridiano
- Calcula a comissão de cada lojista pela **taxa contratada**, no checkout e na remessa
- Lista cada transação cobrada diferente do contrato, com o valor em reais
- Monta as notas fiscais: para quem, de qual linha, de quanto, com o texto
- Classifica os 184 lançamentos dos dois extratos no plano de contas
- Separa o que precisa de gente: 18 pendências, cada uma com motivo e responsável
- **Número de destaque:** comissão checkout R$ 203.735,34 (21 lojistas, 1.900 transações) e remessa R$ 39.543,45 (228 operações) (`comissoes_por_lojista.csv`)

> Nota do apresentador: mostrar o resumo que o comando imprime na tela. Nota checkout soma R$ 203.740,84 porque a Casa do Estudante fecha negativa (−R$ 5,50) e não emite nota.

---

## Slide 4: Quanto dinheiro está em jogo
**Mensagem-chave:** Quatro tipos de dinheiro diferentes, que não se somam: o que a Tarvo recupera dos parceiros, o que devolve aos lojistas, o que pode deixar de faturar e o caixa à espera de confirmação.

**(a) A recuperar dos parceiros (divergência de contrato, `natureza = CONTRATO`, `cobrar_parceiro = S`)**
| De quem | O quê | Valor | Origem |
|---|---|---|---|
| Orbe | Rota Global (+0,50 p.p. no crédito desde 12/09, contrato inalterado) | R$ 1.546,28 em 87 transações | `divergencias_taxa.csv` CHECKOUT/CONTRATO; PEN-0003 |
| Orbe | Escola Bridge (taxa nova de 15/09 aplicada só a partir de 23/09: 2,59% × 2,19%) | R$ 29,95 em 5 transações | idem; PEN-0002 |
| **Orbe, total** | | **R$ 1.576,23 em 92 transações** (líquido de estornos, R51) | `divergencias_taxa.csv`, CHECKOUT, natureza CONTRATO |
| Ponte | Mundo Aberto pagou spread ~1,50% com contrato de 1,20% (valor cheio, R22) | **R$ 1.418,85 em 23 operações** | `divergencias_taxa.csv` REMESSA/CONTRATO; PEN-0007 |
| Ponte | Contestação dos 4 spreads negativos (prejuízo da Tarvo, outra natureza, R53) | realizado −R$ 1.834,05 em 4 operações | `pendencias.csv` PEN-0009 a PEN-0012 |

**(b) A devolver aos lojistas: R$ 18.392,50** (a taxa sai descontada na liquidação, então o lojista já recebeu a menos, S34)
| O quê | Valor | Origem |
|---|---|---|
| Casa do Estudante: isenção set–dez **não informada à Orbe** (`ISENCAO_NAO_INFORMADA`). A Orbe cobrou certo pelo que sabia; **não há o que recuperar**: a Tarvo devolve do próprio bolso (S18) | **R$ 15.397,42 em 118 transações** | `divergencias_taxa.csv` CHECKOUT/ISENCAO_NAO_INFORMADA; PEN-0001 |
| Lojistas das divergências de contrato (Rota, Bridge, Mundo Aberto), compensado pelo que se recupera em (a) | R$ 2.995,08 | (a) |

**(c) Receita da Tarvo em risco: R$ 8.687,51**
| O quê | Valor | Origem |
|---|---|---|
| Atlas Idiomas não faturada (sem contrato; referência = taxa que a Orbe cobrou). Fatura retroativa quando o Comercial confirmar (S27) | R$ 7.876,05 em 57 transações | `pendencias.csv` PEN-0005 |
| Participação não recebida nos 4 spreads negativos: 50% do spread estimado D-1 (R$ 1.622,90), por operação | R$ 811,46 | PEN-0009 a PEN-0012 (estimado D-1 no motivo) |

**(d) Caixa a confirmar (não é receita)**
| O quê | Valor | Origem |
|---|---|---|
| PIX sem identificação (Aurora L50) | R$ 7.350,00 | `pendencias.csv` PEN-0015 |
| Devolução de repasse Mundo Aberto (Aurora L65), motivo desconhecido | R$ 12.400,00 | PEN-0016 |
| PIX da Ponte Aérea Estudantil (Meridiano): **identificado** (S22) como adiantamento de remessa de outubro; acompanhar | R$ 18.240,00 | PEN-0018 |

- Também evitado: duplicata da Ponte que inflaria a base da nota, R$ 821,88 (PEN-0013)
- **Número de destaque:** R$ 15.397,42 a devolver à Casa do Estudante porque ninguém avisou a Orbe

> Nota do apresentador: não somar os grupos. (a) é o que se cobra de Orbe e Ponte; (b) é dinheiro do lojista, e a Casa sai do caixa da Tarvo porque o erro foi interno; (c) é o que a Tarvo deixa de faturar se ninguém agir (estimativas); (d) é dinheiro já no banco cuja origem ou destino só o financeiro confirma.

---

## Slide 5: Como a analista usa em outubro
**Mensagem-chave:** Um comando, seis arquivos, e o tempo vai para decidir, não para bater planilha.
1. Salvar os 6 arquivos de outubro numa pasta
2. Rodar `python -m src.fechamento --entrada <pasta> --saida <pasta>\saida`
3. Abrir `pendencias.csv` e distribuir por responsável (Helena, Comercial, Risco)
4. Conferir e emitir as notas de `notas_a_emitir.csv`
5. Duvidou de um número? Filtrar `rastro.csv` pelo código e ver as transações que o compõem
6. Mudou taxa ou entrou lojista: atualizar a planilha e rodar de novo
7. A Orbe mandou um arquivo de ajuste no meio do mês (estornos, reversões, vendas)? Colocar o arquivo na mesma pasta (com `orbe` no nome) e rodar de novo; não precisa mexer em nada
- Guia passo a passo: `COMO_USAR.md`
- **Número de destaque:** 18 pendências em setembro (15 Helena, 1 Comercial, 2 Helena/Comercial) (`pendencias.csv`)

> Nota do apresentador: o oito dias úteis vira conferir 18 itens. A solução já traz pendências preventivas para outubro (vigência que não entende, CNPJ sem contrato, operação fora do mês, saldo que não fecha).

---

## Slide 6: Onde a IA atua e onde não atua
**Mensagem-chave:** Os fatos e os números saem do código. A IA explica a causa provável e sugere o que conferir. A analista decide.

| Quem faz | O quê |
|---|---|
| **Código (determinístico)** | Todos os números dos 6 CSVs e o dossiê de fatos de cada divergência (datas, faixas, taxa aplicada × contratada, coincidências com a planilha). Mesmo arquivo → mesmo resultado, byte a byte. |
| **IA (Claude Sonnet 5.5)** | Lê só os fatos do dossiê e sugere até 3 hipóteses de causa, cada uma citando os fatos que a sustentam e os que a contrariam, mais o que conferir, com quem falar e o dado que falta. |
| **Analista** | Aceita, recusa ou comenta cada hipótese. A decisão fica registrada com nome, data e hora. |
| **A IA não faz** | Nenhum número, nenhuma decisão (devolver, cobrar, contestar), nenhum envio, nenhuma pendência fechada. A saída da IA fica fora dos 6 CSVs, que são idênticos com ou sem IA. |

- **Guarda-corpos no código:** hipótese sem fato citado é descartada; ID de fato inexistente é removido; hipótese "alta" com fato contrário cai para "média"; máximo 3, ordenadas por confiança. Sem chave, o fechamento roda igual e a analista recebe só o dossiê.
- **Exemplo real (G02 Rota, execução 3, `docs/exemplo_investigacao_ia.md`):** fatos do código: +0,50 p.p. constante nas 3 faixas de crédito desde 12/09 (inclusive 7–12x a 4,09%, que não existe em nenhuma aba); débito, Pix e antecipação na taxa certa; a aba 2025 só coincide em 2 de 5 faixas. A IA sugeriu como principal "cadastro do EC na Orbe alterado por volta de 12/09" (média) e rebaixou "tabela antiga de 2025" para baixa, citando os fatos contrários. Conferir: histórico de alterações do EC 1074504011 na Orbe. Falar com: Orbe.
- **Por que não usar IA no número:** (1) cada centavo precisa apontar para a linha de origem; (2) um número "quase certo" é errado; (3) nota fiscal e devolução ao lojista não podem depender de uma resposta que muda de uma execução para outra. A própria IA varia: em 3 execuções, a causa principal da Rota mudou entre a v2 e a v3 do prompt; por isso ela só sugere.
- **Onde a IA errou e nós corrigimos:** `PROMPTS/MOMENTOS.md` (spreads negativos como divergência; exemplo real vazando no prompt; fato errado no pedido; hipótese contradita por fato que ela mesma citou).
- **Número de destaque:** 0 números e 0 lançamentos por IA: 183 de 184 lançamentos por REGRA, 1 por HUMANO (o PIX de R$ 18.240,00, origem confirmada pelo financeiro, S22) (`lancamentos_classificados.csv`, coluna `metodo`)

> Nota do apresentador: "A IA trabalha para a analista, não no lugar da regra de vocês." Mostrar o cartão da Rota na tela, com os botões Aceitar/Recusar.

---

## Slide 7: Onde a solução falha, e o que acontece
**Mensagem-chave:** Quando não sabe, ela não chuta: vira pendência com dono.
- Lojista sem contrato ou taxa indefinida → fora da nota, pendência para o Comercial
- Vigência escrita num formato novo → o lojista inteiro vai para pendência, não escolhe a "mais provável"
- Lançamento de extrato com descrição nova → conta provisória 1.1.09.002, pendência para a Helena
- Nome parecido não serve de vínculo: "HORIZONTE INTERCAMBIO" (Orbe) é a Novo Horizonte, não a Horizonte Viagens. Vínculo só por EC/CNPJ, confirmado pelo financeiro
- Ainda não concilia Orbe × banco parcela a parcela (falta a agenda de recebíveis)
- Mudança de layout de arquivo → o programa para e diz o que não achou
- **Caso real (17/10, 13h): a Orbe mandou 14 ajustes tardios** (10 estornos, 3 reversões de antecipação e 1 venda, arquivo `06_orbe_ajustes_tardios_set2026.csv`) depois de a primeira versão estar pronta. A solução antiga quebrava com 2 arquivos da Orbe na pasta; agora ela lê todo arquivo `orbe` da pasta, soma as linhas e o `rastro.csv` diz de qual arquivo veio cada uma. Basta colocar o arquivo na pasta e rodar de novo. Impacto no mês: **−R$ 3.304,39** na comissão de checkout (R$ 207.039,73 → R$ 203.735,34), quase todo da Oxford (−R$ 2.232,19, por 2 reversões de antecipação) e da Maple (−R$ 845,01). Divergências e pendências não mudaram. Linha repetida ou estorno em dobro não conta duas vezes: vira pendência.
- **Arquivo aberto no Excel na hora de rodar:** em vez de um erro técnico, o programa diz qual CSV de `saida/` está aberto e pede para fechá-lo no Excel (ou em outro programa) e rodar de novo
- Relatório da Ponte de outro mês → as operações ficam fora e vira 1 pendência por mês de contratação; o resto do fechamento roda
- **Como sabemos que funciona:** teste de outubro simulado (datas deslocadas para outubro, lojista novo fora da planilha, lançamento desconhecido no extrato: tudo vira pendência, a Casa continua a taxa zero, o rastro fecha); auditoria independente feita por outro agente sem acesso ao código, recalculando do arquivo bruto (amostra aleatória de 30 transações: 30/30 certas; soma do rastro conferida para todos os id_saida); 116 testes automáticos verdes (inclusive os da IA, com resposta simulada e sem rede)
- **Número de destaque:** 46 lançamentos com confiança menor que 1 sinalizados para revisão (`lancamentos_classificados.csv`)

> Nota do apresentador: dizer explicitamente quais premissas ainda esperam resposta (HIPOTESES.md) e que mudar uma resposta é mudar um parâmetro e rodar de novo.

---

## Slide 8: Próximo mês de desenvolvimento
**Mensagem-chave:** Tirar o que ainda é manual e avisar antes do fechamento, não depois.
- Agenda de recebíveis da Orbe para conciliar Orbe × banco parcela a parcela
- Cadastro de taxas estruturado (com EC, CNPJ, vigência de data a data) no lugar da planilha
- Interface simples: subir os arquivos, ver pendências, aprovar
- Alertas de divergência em tempo real (diário), não só no fim do mês
- Geração das notas fiscais via API da prefeitura/emissor
- **Próximos usos de IA (sempre com revisão da Helena, nada enviado sozinho):**
  - **Rascunho de contestação por contraparte** (S31: "serve, e muito"): um e-mail para a Orbe (Rota, Bridge) e um para a Ponte (Mundo Aberto, spreads negativos, duplicata), com as operações anexadas; a Helena revisa e envia. A Casa do Estudante não entra (S18): vira um rascunho separado para Comercial/lojista.
  - **Aviso de condição nova aos parceiros** (S30): quando a planilha muda (isenção, taxa ou spread novo), a solução gera o aviso para a Orbe ou a Ponte. Ataca a causa raiz do slide 2.
  - Sugerir a conta de lançamentos novos no extrato, com revisão humana obrigatória (método IA, confiança < 1)
- **Número de destaque:** a Rota Global pagou a mais por 19 dias (12/09 a 30/09) até o fechamento; com alerta diário seria 1 dia

> Nota do apresentador: priorizar cadastro de taxas, alertas e o aviso de condição nova: são os que atacam a causa raiz do slide 2.

---

## Slide 9: Fechamento
**Mensagem-chave:** Regra escrita, número rastreável, exceção com dono.
- R$ 243.284,29 em notas, cada centavo com origem
- R$ 1.576,23 a recuperar da Orbe e R$ 1.418,85 da Ponte (mais a contestação dos spreads negativos); R$ 15.397,42 a devolver à Casa do Estudante; R$ 8.687,51 de receita em risco, agora visíveis
- 18 decisões para pessoas, em vez de 8 dias de conferência
- Perguntas

> Nota do apresentador: terminar devolvendo a palavra para a Helena: "Quais dessas 18 pendências vocês decidem hoje?"
