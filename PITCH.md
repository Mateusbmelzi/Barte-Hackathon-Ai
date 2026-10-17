# Pitch: pré-esboço (15 min, para Helena e o CFO da Tarvo)

Público: financeiro e CFO, não engenheiros. Todos os números vêm de `saida/*.csv` (fechamento de setembro/2026) e a origem de cada um está indicada. Formato: 9 slides, cerca de 1,5 min cada, mais as perguntas.

---

## Slide 1: Título
**Mensagem-chave:** O mês da Tarvo fecha numa regra escrita, não na cabeça de uma pessoa.
- Fechamento de setembro/2026: comissões, divergências, notas, lançamentos e pendências
- Cada número com o caminho até a linha de origem
- **Número de destaque:** R$ 246.588,68 em 21 notas fiscais a emitir (`notas_a_emitir.csv`)

> Nota do apresentador: abrir com a frase do time ("Se eu sair de férias, o mês não fecha") e dizer que o objetivo é que o mês feche com ou sem a pessoa.

---

## Slide 2: O que está quebrado, e por quê
**Mensagem-chave:** O problema não é falta de braço. É regra sem lugar, planilha sem chave e ninguém comparando contratado com cobrado.
- **Regras só na cabeça de uma pessoa:** taxa zero da Casa do Estudante, spread de 1,20% da Mundo Aberto, "spread negativo não se aceita", "operação repetida conta uma vez". Nada disso estava escrito; tivemos de perguntar (17 respostas no Slack, S01–S17).
- **Planilha de taxas manual e sem chave confiável:** 3 lojistas sem código da Orbe (Horizonte Viagens, Kiwi, Novo Horizonte), CNPJ sem o zero inicial (Fluente, Campus Global), taxas digitadas como texto (Oxford Prep, Sol Nascente), Atlas Idiomas transacionando sem contrato vigente.
- **Ninguém compara taxa contratada × taxa cobrada:** a conferência é manual, arquivo por arquivo; só se descobre quando o lojista reclama.
- **Acordo que não chegou ao sistema:** a Casa do Estudante tem taxa zero de setembro a dezembro, mas a Orbe cobrou normalmente.
- **Cobrança a mais sem ninguém notar:** Rota Global pagou +0,50 p.p. no crédito desde 12/09, contrato inalterado.
- **Ponte sem critério:** operação duplicada e spread negativo eram aceitos ou não "no feeling".
- **Número de destaque:** 210 transações de checkout cobradas fora do contrato num só mês (`divergencias_taxa.csv`, linha CHECKOUT)

> Nota do apresentador: este é o slide da causa raiz. Automatizar o processo como ele é só faria o erro mais rápido. A correção foi tirar a regra da cabeça e a taxa da planilha solta.

---

## Slide 3: O que a solução faz (em linguagem de financeiro)
**Mensagem-chave:** Você coloca os 6 arquivos do mês numa pasta e recebe o fechamento pronto para conferir.
- Lê os arquivos como chegam: relatório Orbe, planilha de taxas, e-mail da Ponte, plano de contas, extratos Aurora e Meridiano
- Calcula a comissão de cada lojista pela **taxa contratada**, no checkout e na remessa
- Lista cada transação cobrada diferente do contrato, com o valor em reais
- Monta as notas fiscais: para quem, de qual linha, de quanto, com o texto
- Classifica os 184 lançamentos dos dois extratos no plano de contas
- Separa o que precisa de gente: 18 pendências, cada uma com motivo e responsável
- **Número de destaque:** comissão checkout R$ 207.039,73 (21 lojistas, 1.886 transações) e remessa R$ 39.543,45 (228 operações) (`comissoes_por_lojista.csv`)

> Nota do apresentador: mostrar o resumo que o comando imprime na tela. Nota checkout soma R$ 207.045,23 porque a Casa do Estudante fecha negativa (−R$ 5,50) e não emite nota.

---

## Slide 4: Quanto dinheiro está em jogo
**Mensagem-chave:** Três tipos de dinheiro diferentes, que não se somam: o que volta ao lojista, o que a Tarvo pode deixar de receber e o caixa sem dono.

**(a) A devolver aos lojistas e cobrar de Orbe/Ponte: R$ 18.392,50**
| O quê | Valor | Origem |
|---|---|---|
| Divergências checkout (Orbe cobrou fora do contrato), líquido de estornos | R$ 16.973,65 em 210 transações | `divergencias_taxa.csv`, linha CHECKOUT |
| · Casa do Estudante (taxa zero ignorada) | R$ 15.397,42 em 118 transações | idem (PEN-0001) |
| · Rota Global (+0,50 p.p.) | R$ 1.546,28 em 87 transações | idem (PEN-0003) |
| · Escola Bridge (nova taxa de 15/09 não aplicada: 2,59% cobrado × 2,19% contratado) | R$ 29,95 em 5 transações | idem (PEN-0002) |
| Divergência remessa: Mundo Aberto pagou spread de ~1,50% com contrato de 1,20% | R$ 1.418,85 em 23 operações | `divergencias_taxa.csv`, linha REMESSA (PEN-0007) |

**(b) Receita da Tarvo em risco: R$ 8.687,51**
| O quê | Valor | Origem |
|---|---|---|
| Atlas Idiomas não faturada (sem contrato; referência = taxa que a Orbe cobrou) | R$ 7.876,05 em 57 transações | `pendencias.csv` PEN-0005 |
| Participação não recebida nos 4 spreads negativos: 50% do spread estimado D-1 (R$ 1.622,90), por operação | R$ 811,46 | `pendencias.csv` PEN-0009 a PEN-0012 (estimado D-1 no motivo) |

**(c) Caixa sem dono (não é receita): R$ 37.990,00**
| O quê | Valor | Origem |
|---|---|---|
| PIX sem identificação (Aurora L50) | R$ 7.350,00 | `pendencias.csv` PEN-0015 |
| Devolução de repasse Mundo Aberto (Aurora L65) | R$ 12.400,00 | PEN-0016 |
| PIX "Ponte Aérea" sem operação Ponte (Meridiano) | R$ 18.240,00 | PEN-0018 |

- Também evitado: duplicata da Ponte que inflaria a base da nota, R$ 821,88 (PEN-0013)
- **Número de destaque:** R$ 15.397,42 a devolver à Casa do Estudante

> Nota do apresentador: não somar os três grupos. (a) é dinheiro do lojista; (b) é o que a Tarvo deixa de faturar se ninguém agir (a Atlas é estimativa pela taxa da Orbe; o spread negativo é pelo que a Ponte prometeu no D-1); (c) é dinheiro já no banco cuja origem só o financeiro confirma.

---

## Slide 5: Como a analista usa em outubro
**Mensagem-chave:** Um comando, seis arquivos, e o tempo vai para decidir, não para bater planilha.
1. Salvar os 6 arquivos de outubro numa pasta
2. Rodar `python -m src.fechamento --entrada <pasta> --saida <pasta>\saida`
3. Abrir `pendencias.csv` e distribuir por responsável (Helena, Comercial, Risco)
4. Conferir e emitir as notas de `notas_a_emitir.csv`
5. Duvidou de um número? Filtrar `rastro.csv` pelo código e ver as transações que o compõem
6. Mudou taxa ou entrou lojista: atualizar a planilha e rodar de novo
- Guia passo a passo: `COMO_USAR.md`
- **Número de destaque:** 18 pendências em setembro (16 Helena, 1 Comercial, 1 Helena/Comercial) (`pendencias.csv`)

> Nota do apresentador: o oito dias úteis vira conferir 18 itens. A solução já traz pendências preventivas para outubro (vigência que não entende, CNPJ sem contrato, operação fora do mês, saldo que não fecha).

---

## Slide 6: Onde a IA atua e onde não atua
**Mensagem-chave:** A IA ajudou a construir e a auditar. Nenhum número do fechamento sai de IA.
- **Cálculo é determinístico, por regra escrita:** taxa contratada × valor, arredondamento meio-centavo-para-cima, linha a linha. Mesmo arquivo → mesmo resultado, sempre.
- **Por que não usar IA no número:** (1) rastreabilidade: cada centavo precisa apontar para a linha de origem, e um modelo de linguagem não garante isso; (2) o resultado é conferido contra um gabarito: um número "quase certo" é errado; (3) a nota fiscal e a devolução ao lojista não podem depender de uma resposta que muda de uma execução para outra.
- **Onde a IA foi usada:** ler e entender os arquivos, achar anomalias, redigir perguntas ao financeiro, escrever o código, revisar com um auditor independente que recalculou amostras a partir do arquivo bruto.
- **Onde a IA errou e nós corrigimos:** ver `PROMPTS/MOMENTOS.md` (ex.: listar spreads negativos como divergência gerava 4 alarmes falsos; um auditor independente pegou e corrigimos. E o arredondamento padrão do Python erraria R$ 0,60 na nota da Ponte).
- **Número de destaque:** 0 lançamentos por IA: 183 de 184 por REGRA, 1 por HUMANO (o PIX de R$ 18.240,00 sem origem) (`lancamentos_classificados.csv`, coluna `metodo`)

> Nota do apresentador: "A IA trabalhou para nós, não no lugar da regra de vocês."

---

## Slide 7: Onde a solução falha, e o que acontece
**Mensagem-chave:** Quando não sabe, ela não chuta: vira pendência com dono.
- Lojista sem contrato ou taxa indefinida → fora da nota, pendência para o Comercial
- Vigência escrita num formato novo → o lojista inteiro vai para pendência, não escolhe a "mais provável"
- Lançamento de extrato com descrição nova → conta provisória 1.1.09.002, pendência para a Helena
- Nome parecido não serve de vínculo: "HORIZONTE INTERCAMBIO" (Orbe) é a Novo Horizonte, não a Horizonte Viagens. Vínculo só por EC/CNPJ, confirmado pelo financeiro
- Ainda não concilia Orbe × banco parcela a parcela (falta a agenda de recebíveis)
- Mudança de layout de arquivo → o programa para e diz o que não achou
- Relatório da Ponte de outro mês → as operações ficam fora e vira 1 pendência por mês de contratação; o resto do fechamento roda
- **Como sabemos que funciona:** teste de outubro simulado (datas deslocadas para outubro, lojista novo fora da planilha, lançamento desconhecido no extrato: tudo vira pendência, a Casa continua a taxa zero, o rastro fecha); auditoria independente feita por outro agente sem acesso ao código, recalculando do arquivo bruto (amostra aleatória de 30 transações: 30/30 certas; soma do rastro conferida para todos os id_saida); 51 testes automáticos verdes
- **Número de destaque:** 47 lançamentos com confiança menor que 1 sinalizados para revisão (`lancamentos_classificados.csv`)

> Nota do apresentador: dizer explicitamente quais premissas ainda esperam resposta (HIPOTESES.md) e que mudar uma resposta é mudar um parâmetro e rodar de novo.

---

## Slide 8: Próximo mês de desenvolvimento
**Mensagem-chave:** Tirar o que ainda é manual e avisar antes do fechamento, não depois.
- Agenda de recebíveis da Orbe para conciliar Orbe × banco parcela a parcela
- Cadastro de taxas estruturado (com EC, CNPJ, vigência de data a data) no lugar da planilha
- Interface simples: subir os arquivos, ver pendências, aprovar
- Alertas de divergência em tempo real (diário), não só no fim do mês
- Geração das notas fiscais via API da prefeitura/emissor
- IA só para **sugerir** a conta de lançamentos novos no extrato, com revisão humana obrigatória (método IA, confiança < 1)
- **Número de destaque:** a Rota Global pagou a mais por 19 dias (12/09 a 30/09) até o fechamento; com alerta diário seria 1 dia

> Nota do apresentador: priorizar cadastro de taxas e alertas: são os que atacam a causa raiz do slide 2.

---

## Slide 9: Fechamento
**Mensagem-chave:** Regra escrita, número rastreável, exceção com dono.
- R$ 246.588,68 em notas, cada centavo com origem
- R$ 18.392,50 a devolver e cobrar dos parceiros; R$ 8.687,51 de receita da Tarvo em risco; R$ 37.990,00 de caixa sem dono, agora visíveis
- 18 decisões para pessoas, em vez de 8 dias de conferência
- Perguntas

> Nota do apresentador: terminar devolvendo a palavra para a Helena: "Quais dessas 18 pendências vocês decidem hoje?"
