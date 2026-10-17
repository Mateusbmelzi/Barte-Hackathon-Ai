"""Parâmetros de negócio do fechamento. Cada um cita a regra (R##, REGRAS_DE_NEGOCIO.md)
ou a hipótese (H##, HIPOTESES.md) que o justifica. Mudou a regra? Mude AQUI, não no código."""
from decimal import Decimal

# ---------------------------------------------------------------- descoberta de arquivos
# Padrões (glob, sem diferenciar maiúsculas) para achar cada fonte na pasta de entrada.
# Em outubro basta colocar os arquivos novos na pasta: o nome só precisa conter o padrão.
PADROES_ARQUIVOS = {
    "orbe": "*orbe*.csv",
    "taxas": "*taxas*.xlsx",
    "ponte": "*.eml",
    "plano": "*plano_de_contas*.csv",
    "aurora": "*aurora*.csv",
    "meridiano": "*.ofx",
}

# Fontes que podem vir em 1 ou mais arquivos no mesmo mês (a Orbe manda ajustes tardios à parte).
# Os arquivos são lidos todos, em ordem de nome, e concatenados; cada linha guarda o arquivo de origem.
FONTES_MULTIPLAS = {"orbe"}

# ---------------------------------------------------------------- geral
DIVISAO_PCT = Decimal("100")          # taxas vêm em % (2,69 = 2,69%)
QUEM_HELENA = "Helena (Financeiro)"
QUEM_COMERCIAL = "Comercial"
QUEM_RISCO = "Helena (Financeiro) / Comercial"   # B3: cliente não citou área de Risco; S23: alerta p/ Helena e Comercial
QUEM_HELENA_COMERCIAL = "Helena (Financeiro) / Comercial"   # S18: devolução por isenção não informada

# ---------------------------------------------------------------- checkout (Orbe)
# Condições ESPECÍFICAS DE CLIENTE (isenções, taxas especiais, de-para de EC Orbe, EC bloqueado/CNPJ do bloqueado,
# notas de pendência por lojista) saíram daqui: ficam no CADASTRO versionado, cadastro/condicoes_comerciais.csv
# (módulo src/cadastro.py; a planilha de taxas do cliente nunca é alterada). Aqui ficam só as regras GERAIS.

# R57/S38: a Tarvo não vende acima de 12x; se aparecer, a linha fica fora de comissões/notas e vira pendência.
MAX_PARCELAS = 12

# Dupla reversão: estorno/reversão cujo id_referencia já foi estornado/revertido por outra linha.
# False (padrão) = a 2ª NÃO é aplicada (fica fora de comissões) e vira pendência ORBE_ESTORNO_DUPLICADO
# para o gestor decidir. True = a 2ª é aplicada normalmente (a pendência continua sendo aberta).
APLICAR_ESTORNO_DUPLICADO = False

# H04: Orbe cobrar menos que o contrato também é divergência (valor negativo).
# Comparação exata: as taxas são percentuais com 2 casas; truncamento da Orbe
# no valor_taxa NÃO é divergência (R02), por isso comparamos a TAXA, não o valor.

# S42/S50: ALERTA_ANTECIPACAO. Critério NOSSO (o financeiro não definiu limite). A antecipação é sobre a agenda
# inteira do lojista, então comparar com as vendas do mês acenderia lojista demais. Preocupação (S42) = lojista
# NOVO, sem histórico, antecipando alto. Acende para qualquer lojista (com ou sem contrato) que:
#  (1) seja novo: nenhuma transação com data de referência anterior ao mês do relatório (no estorno/reversão,
#      a data da venda/antecipação original) E primeira transação depois do 1º dia do mês; e
#  (2) tenha, em algum dia, antecipação acumulada (líquida das reversões já ocorridas) maior que as vendas
#      acumuladas até aquele dia. O alerta é pelo PICO (S50); o motivo cita as reversões posteriores ao pico e o
#      saldo líquido de antecipação no fim do mês.
ALERTA_ANTECIPACAO_SO_LOJISTA_NOVO = True   # False = regra antiga (qualquer lojista com antecipação > vendas)

# ---------------------------------------------------------------- remessa (Ponte Câmbio)
CNPJ_PONTE = "75374179000146"            # R32/S04: tomadora da nota de remessa
NOME_PONTE = "Ponte Câmbio S.A."
# S40: ajuste de contestação da Ponte (a partir de outubro). Linha nova no relatório, Nº de Operação próprio,
# observação "AJUSTE REF PC-…". Não é spread negativo a contestar: entra na comissão do mês como
# PARTICIPACAO_REMESSA x Spread R$ do ajuste (PREMISSA NOSSA, pergunta em aberto: o Spread R$ do ajuste é o spread
# inteiro, não a participação já calculada), abate a nota única da Ponte; nota <= 0 não emite e vira pendência.
REGEX_AJUSTE_PONTE = r"AJUSTE\s+REF\.?\s+(PC-[\w-]+)"
PARTICIPACAO_REMESSA = Decimal("0.5")    # R20/S05: 50% do Spread R$ realizado, por operação
SPREAD_PADRAO = Decimal("0.015")         # CC03/S05: célula em branco ou "padrão" = 1,5%
TOLERANCIA_SPREAD = Decimal("0.0001")    # H06/S10: divergência só se |aplicado-contratado| >= 0,01 p.p.
                                         # (fração: 0,01 p.p. = 0,0001)

# ---------------------------------------------------------------- extratos / plano de contas
# R40/S12: conta_codigo = contrapartida do movimento bancário.
# Cada regra: (banco, regex na descrição, conta, referência, confiança, pendência?)
# A primeira que casar vence (ordem importa). pendência = None ou (tipo, motivo, quem_decide).
CONTA_NAO_IDENTIFICADO = "1.1.09.002"    # H12: crédito/lançamento sem regra -> créditos não identificados
REGRAS_EXTRATO = [
    # ---- Aurora
    ("AURORA", r"^TED RECEBIDA .*ORBE", "1.1.03.001", "R43/H18 crédito Orbe = recebível de adquirente", Decimal("1.00"), None),
    ("AURORA", r"^PIX ENVIADO CONTABILIDADE", "4.2.06", "R42 serviço contábil, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^PIX ENVIADO ", "2.1.01.001", "H18 repasse a lojista (baixa de repasses a pagar)", Decimal("0.95"), None),
    ("AURORA", r"^TRANSF ENTRE CONTAS", "1.1.09.001", "H13 transferência entre contas próprias", Decimal("1.00"), None),
    ("AURORA", r"^PAGTO SALARIOS", "2.1.04.001", "R41/H14 folha do mês anterior provisionada (baixa do passivo)", Decimal("1.00"), None),
    ("AURORA", r"^PAGTO ISS", "2.1.03.003", "R41/H14 ISS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"^GPS INSS", "2.1.04.002", "R41/H14 INSS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"^GRF FGTS", "2.1.04.003", "R41/H14 FGTS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 0561", "2.1.03.004", "R41/H14 IRRF (DARF 0561) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 8109", "2.1.03.001", "R41/H14 PIS (DARF 8109) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 2172", "2.1.03.002", "R41/H14 COFINS (DARF 2172) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"CONDOMINIO|ALUGUEL", "4.2.02", "R42 aluguel/condomínio, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"AMAZON WEB SERVICES", "4.2.03", "R42 cloud, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"GOOGLE WORKSPACE", "4.2.04", "R42 software/assinatura, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^TAR ", "4.2.01", "R42 tarifa bancária, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^PIX RECEBIDO .*SEM IDENTIFICACAO", "1.1.09.002", "R44/H12 crédito sem identificação não é receita", Decimal("0.70"),
     ("CREDITO_NAO_IDENTIFICADO",
      "PIX recebido sem identificação do pagador. Não é receita até identificar (R44/S09). Classificado em 1.1.09.002 (H12). Identificar o pagador e reclassificar.",
      QUEM_HELENA)),
    ("AURORA", r"^DEVOLUCAO PIX", "2.1.01.001", "H11 repasse a lojista devolvido; obrigação com o lojista continua", Decimal("0.70"),
     ("DEVOLUCAO_REPASSE",
      "PIX de repasse ao lojista voltou (devolução) por motivo desconhecido (S09). Classificado em 2.1.01.001 (H11): o repasse continua a pagar. Confirmar o motivo e se deve repagar em outubro.",
      QUEM_HELENA)),
    # ---- Meridiano
    ("MERIDIANO", r"^PIX RECEB ", "2.1.02.001", "H18 recurso de lojista para remessa", Decimal("1.00"), None),
    ("MERIDIANO", r"^TED ENVIADA PONTE CAMBIO", "2.1.02.001", "H18 liquidação de remessas na Ponte (Valor R$ + IOF)", Decimal("1.00"), None),
    ("MERIDIANO", r"REPASSE COMISSAO", "1.1.03.002", "R41/S08 repasse de comissão de câmbio já registrado (baixa do a receber)", Decimal("1.00"), None),
    ("MERIDIANO", r"MESMA TITULARIDADE", "1.1.09.001", "H13 transferência entre contas próprias", Decimal("1.00"), None),
    ("MERIDIANO", r"^RENDIMENTO", "3.2.01", "rendimento de aplicação automática", Decimal("1.00"), None),
    ("MERIDIANO", r"APLICACAO AUTOMATICA|RESGATE AUTOMATICO", "1.1.02.001", "aplicação/resgate automático (contrapartida na aplicação)", Decimal("1.00"), None),
    ("MERIDIANO", r"^TARIFA", "4.2.01", "R42 tarifa bancária, despesa do mês", Decimal("1.00"), None),
    ("MERIDIANO", r"SEGURO", "4.2.05", "R42 seguro, despesa do mês (sem provisão)", Decimal("1.00"), None),
    ("MERIDIANO", r"^IOF", "4.3.01", "IOF debitado pelo banco", Decimal("1.00"), None),
]

# Conciliações de apoio (só por VALOR e DATA, nunca por nome):
JANELA_PIX_REMESSA_DIAS = 7   # PIX de lojista no dia d cobre ops do mesmo CNPJ contratadas em [d, d+7) (doc §6.3)
CONF_NAO_CONCILIADO = Decimal("0.60")   # confiança quando a regra casa mas a conciliação não fecha
CONF_PIX_REMESSA_FUTURA = Decimal("1.00")  # S22: PIX de lojista sem operação Ponte no mês = recurso para
                                           # remessa futura (regra confirmada pelo financeiro) -> HUMANO 1,00 + acompanhamento
CONF_SEM_REGRA = Decimal("0.30")        # nenhuma regra casou -> HUMANO

# ---------------------------------------------------------------- natureza das divergências (R52, R60; S18, S34, S37)
# CONTRATO: o parceiro aplicou taxa diferente da informada a ele -> devolver ao lojista E cobrar o parceiro.
# ISENCAO_NAO_INFORMADA: isenção (TAXA_ZERO_CHECKOUT) que o parceiro não conhecia -> só devolver ao lojista.
NATUREZA_CONTRATO = "CONTRATO"
NATUREZA_ISENCAO = "ISENCAO_NAO_INFORMADA"
COBRAR_PARCEIRO = {NATUREZA_CONTRATO: "S", NATUREZA_ISENCAO: "N"}
# S41: o que decide cobrar a contraparte é a condição contratada (aditivo/negociação registrada), não o aviso à
# Orbe/Ponte. O valor do campo `natureza` nos CSVs não muda (compatibilidade); só o texto descritivo.
DESCRICAO_NATUREZA = {
    NATUREZA_CONTRATO: "divergência de contrato (vale a condição contratada: aditivo/negociação registrada, não o aviso)",
    NATUREZA_ISENCAO: ("concessão comercial fora do contrato (a Orbe cobrou o contratado; "
                       "devolução sai do bolso da Tarvo)"),
}

# ---------------------------------------------------------------- dossiê de investigação (src/investigacao.py)
# Respostas do financeiro (docs/00_slack_respostas_financeiro.md) que tocam cada lojista.
# Chave = (linha_negocio, CNPJ). O dossiê só copia estes textos: nunca gera texto livre sobre S##.
TEXTOS_FINANCEIRO = {
    "S05": "Mundo Aberto negociou spread de 1,20% em julho; aplicar mais é divergência, Helena contesta com a Ponte.",
    "S06": "Rota Global: o contrato não mudou este ano; a cobrança de +0,50 p.p. desde 12/09 é divergência.",
    "S07": "Casa do Estudante: tarifa zerada no checkout de setembro a dezembro (MDR e antecipação), acordo comercial; a Orbe cobrou e a Helena devolve ao lojista.",
    "S10": "Divergência de remessa vale pelo valor cheio que o lojista pagou a mais, não só os 50% da Tarvo.",
    "S13": "O excesso da Mundo Aberto entra na nota de setembro pelo realizado; se a Ponte devolver, a metade da Tarvo sai no mês do ajuste.",
    "S18": "Casa do Estudante: a Orbe cobrou certo pela planilha porque ninguém avisou a isenção; não há o que cobrar da Orbe, é devolução ao lojista (Helena com o Comercial).",
    "S41": ("O que decide cobrar a contraparte é o contrato, não o aviso: Bridge (aditivo assinado, 2,19% desde 15/09) e "
            "Mundo Aberto (1,20% negociado e registrado desde julho) são divergência, a Helena contesta com Orbe/Ponte e o "
            "lojista é ressarcido; Casa do Estudante é concessão do comercial fora do contrato: a Orbe cobrou o contratado "
            "e a devolução sai do bolso da Tarvo."),
    "S51": ("Devolve-se ao lojista o que saiu do bolso dele: o valor_taxa que a Orbe descontou menos a comissão contratada. "
            "A lista de divergências segue a fórmula bruto x diferença de taxa; a diferença entre as duas é o truncamento da Orbe."),
    "S30": "Ninguém tem a função de avisar Orbe/Ponte das condições novas; a Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas.",
    "S37": "Casa do Estudante: uma pendência com o total e o detalhe por transação; não pode entrar na cobrança da Orbe.",
}
# (O contexto de fronteira por lojista no motivo da pendência é a condição NOTA_PENDENCIA do cadastro.)
RESPOSTAS_FINANCEIRO = {
    ("CHECKOUT", "95927868000148"): ["S06", "S51"],                      # Rota Global (EC 1074504011)
    ("CHECKOUT", "00520815000100"): ["S07", "S18", "S37", "S30", "S41", "S51"],  # Casa do Estudante (EC 1018325654)
    ("CHECKOUT", "22224579000109"): ["S30", "S41", "S51"],                      # Escola Bridge (EC 1075624862)
    ("REMESSA", "17217888000111"): ["S05", "S10", "S13", "S30", "S41"],  # Mundo Aberto
}


# ---------------------------------------------------------------- fonte ausente / layout inesperado (S53)
# "Prefiro que a solução avise a que quebre sem ninguém perceber ... Quem libera sou eu." Fonte que falta ou
# vem com layout diferente não derruba o mês: fecha-se o que não depende dela, marca-se o provisório e
# abre-se pendência (FONTE_AUSENTE / LAYOUT_INESPERADO) para a Helena.
STATUS_PROVISORIO = "PROVISORIO"      # coluna extra 'status' em comissoes/notas, só no fechamento parcial
ROTULO_FONTE = {
    "orbe": "relatório da Orbe", "taxas": "tabela de taxas", "ponte": "e-mail da Ponte",
    "plano": "plano de contas", "aurora": "extrato Aurora", "meridiano": "extrato Meridiano",
    "cadastro": "cadastro de condições comerciais",
}
# O que fica sem calcular quando a fonte não está disponível.
EFEITO_BLOQUEIO = {
    "orbe": "comissões, notas e divergências do checkout não calculadas",
    "taxas": "comissões, notas e divergências do checkout não calculadas; divergências de remessa e alerta de antecipação bloqueados",
    "ponte": "nota da Ponte e comissões de remessa não calculadas; conciliação de TED/PIX da Ponte nos extratos não feita",
    "plano": "lançamentos dos extratos Aurora e Meridiano não classificados",
    "aurora": "lançamentos do extrato Aurora não classificados; transferências entre contas não conferidas",
    "meridiano": "lançamentos do extrato Meridiano não classificados; transferências entre contas e TED/PIX da Ponte não conferidos",
    "cadastro": "condições comerciais não aplicadas: isenções, de-para e bloqueios ignorados; notas e comissões podem estar erradas",
}


# ---------------------------------------------------------------- regras aplicáveis por natureza (dossiê, etapa 2c)
# Texto curto e fiel a REGRAS_DE_NEGOCIO.md (que NÃO é lido em tempo de execução). Mudou a regra lá? Mude aqui.
TEXTOS_REGRAS = {
    "R02": "A Orbe trunca centavos; a diferença de centavo causada por truncamento não é divergência.",
    "R13": ("Divergência de checkout = transação com taxa aplicada diferente da contratada; valor = valor bruto × "
            "(taxa aplicada − contratada). Cobrar o parceiro é decisão da Helena, caso a caso."),
    "R20": ("Remessa: comissão da Tarvo = 50% do Spread R$ realizado por operação; o excesso contestável entra na nota "
            "do mês e o ajuste só entra no mês em que a Ponte devolver."),
    "R22": ("Divergência de remessa = valor cheio que o lojista pagou a mais: (spread % aplicado − contratado) × PTAX "
            "× valor em moeda estrangeira."),
    "R50": ("Divergência é o lojista pagar diferente do contrato, para mais ou para menos (abaixo do contrato = valor "
            "negativo); a Helena decide caso a caso."),
    "R51": "Venda cobrada fora do contrato e depois estornada: venda e estorno se anulam; cobra-se só a diferença líquida.",
    "R52": ("Concessão comercial fora do contrato (ex.: isenção que o Comercial deu e ninguém comunicou) não é divergência "
            "de contrato: não se cobra o parceiro e a devolução ao lojista sai do bolso da Tarvo; fica separada, em uma "
            "pendência para Helena e Comercial."),
    "R60": ("Toda divergência de taxa é dinheiro a devolver ao lojista; quando é de contrato, também a recuperar do "
            "parceiro."),
    "R68": ("Quem deve é decidido pelo contrato, não pelo aviso: aditivo ou condição negociada e registrada é divergência "
            "de contrato (a Helena contesta o parceiro e o lojista é ressarcido); aviso atrasado é problema de processo. "
            "Concessão do Comercial fora do contrato: o parceiro cobrou o contratado e a devolução sai do bolso da Tarvo."),
    "R70": "A taxa do estorno é a da data da venda original.",
    "R71": "Na lista de divergências, o estorno de uma venda com taxa errada também entra, com valor negativo.",
    "R72": ("Isenção ou taxa zero com vigência vale para venda a partir da data de início; para antecipação vale a data "
            "da antecipação; estorno segue a taxa da venda."),
    "R74": ("Valor a devolver ao lojista = o que o parceiro descontou de fato (valor_taxa; na remessa, o Spread R$) menos "
            "a comissão contratada. A lista de divergências segue a fórmula; a diferença entre as duas é truncamento "
            "da Orbe."),
}
# (natureza, linha_negocio) -> R## que valem para o caso. REGRAS_ACAO = as que sustentam a ação (acao_regra.regras).
REGRAS_APLICAVEIS = {
    (NATUREZA_CONTRATO, "CHECKOUT"): ["R13", "R50", "R68", "R60", "R74", "R51", "R70", "R71", "R02"],
    (NATUREZA_CONTRATO, "REMESSA"): ["R22", "R50", "R68", "R60", "R74", "R20"],
    (NATUREZA_ISENCAO, "CHECKOUT"): ["R52", "R68", "R13", "R60", "R74", "R72"],
}
REGRAS_ACAO = {
    (NATUREZA_CONTRATO, "CHECKOUT"): ["R13", "R68", "R74"],
    (NATUREZA_CONTRATO, "REMESSA"): ["R22", "R68", "R74"],
    (NATUREZA_ISENCAO, "CHECKOUT"): ["R52", "R68", "R74"],
}


# ---------------------------------------------------------------- versões do mesmo arquivo (consolidação)
# Reenvio de arquivo (ex.: extrato baixado de novo no dia seguinte). Com 2+ arquivos do mesmo tipo na pasta de
# entrada, as linhas são consolidadas por fonte; nunca se soma em dobro e nunca se apaga linha em silêncio.
# Ordem das versões (da mais antiga para a mais nova):
#   Ponte = cabeçalho Date do e-mail; Meridiano = DTSERVER do OFX; Aurora = fim do "Período" do cabeçalho do CSV;
#   Orbe, planilha de taxas e plano de contas (sem data embutida) = ordem de NOME (natural: v2 < v10; "x (1)" depois
#   de "x"). Empate ou data ausente: ordem de nome. A data de modificação do arquivo NÃO é usada (upload a muda).
# Chave natural: Orbe = id_transacao; Meridiano = FITID; Ponte = Nº Operação (a repetição DENTRO do mesmo relatório
#   continua sendo OPERACAO_DUPLICADA); Aurora = (data, lançamento, documento, valor) como MULTICONJUNTO (duas tarifas
#   iguais no mesmo dia são legítimas: conta-se ocorrência).
# Fontes de referência: usa-se só a versão mais recente (ordem de nome); a outra é ignorada e vira VERSAO_SUBSTITUIDA.
FONTES_REFERENCIA = {"taxas", "plano"}
TIPO_VERSAO_CONFLITANTE = "VERSAO_CONFLITANTE"          # mesma chave, valores diferentes: vale a versão mais recente
TIPO_VERSAO_SOBREPOSTA = "VERSAO_SOBREPOSTA"            # Aurora: nenhuma versão contém a outra: união
TIPO_VERSAO_SUBSTITUIDA = "VERSAO_SUBSTITUIDA"          # referência (taxas/plano): versão antiga ignorada (informativa)
TIPO_LANCAMENTO_SUMIU = "LANCAMENTO_SUMIU_NA_NOVA_VERSAO"   # existia na versão antiga e não está na nova: mantido
ROTULO_VERSAO = {"orbe": "Orbe", "taxas": "Tabela de taxas", "ponte": "Ponte", "plano": "Plano de contas",
                 "aurora": "Aurora", "meridiano": "Meridiano"}
UNIDADE_VERSAO = {"orbe": ("transação", "transações", "a"), "ponte": ("operação", "operações", "a"),   # (singular, plural, o/a)
                  "aurora": ("lançamento", "lançamentos", "o"), "meridiano": ("lançamento", "lançamentos", "o")}


# ---------------------------------------------------------------- fila de trabalho (PLANO_03, src/fila.py)
# Papéis de contato (cadastro/contatos.csv) e, por tipo de item, o objetivo da ação e quem pode ser contatado.
# A IA de ação só pode sugerir destinos desta lista; tipo sem entrada -> FINANCEIRO_INTERNO.
PAPEIS_CONTATO = ["LOJISTA", "ORBE", "PONTE", "COMERCIAL", "BANCO_AURORA", "BANCO_MERIDIANO", "CONTABILIDADE",
                  "FINANCEIRO_INTERNO"]
ROTULO_PAPEL = {"LOJISTA": "Lojista", "ORBE": "Orbe", "PONTE": "Ponte Câmbio", "COMERCIAL": "Comercial",
                "BANCO_AURORA": "Banco Aurora", "BANCO_MERIDIANO": "Banco Meridiano", "CONTABILIDADE": "Contabilidade",
                "FINANCEIRO_INTERNO": "Financeiro (interno)"}
STATUS_FILA = ["ABERTA", "EM_ACOMPANHAMENTO", "BAIXADA", "DECLINADA"]
STATUS_ENCERRADOS = ("BAIXADA", "DECLINADA")
ACOES_FILA = ["SUGESTAO_IA", "EMAIL_PREPARADO", "EMAIL_ENVIADO", "BAIXA", "DECLINADA", "REABERTA", "COMENTARIO"]
TIPOS_ITEM_FILA = ["PENDENCIA", "DIVERGENCIA"]
DESTINO_PADRAO = ["FINANCEIRO_INTERNO"]


def tipo_divergencia(natureza, linha_negocio):
    """Chave de ACOES_POR_TIPO para um grupo de divergência (natureza x linha de negócio)."""
    return f"DIVERGENCIA_{'ISENCAO' if natureza == NATUREZA_ISENCAO else 'CONTRATO'}_{linha_negocio}"


def _acao(rotulo, objetivo, *destinos):
    return {"rotulo": rotulo, "objetivo": objetivo, "destinos": list(destinos)}


ACOES_POR_TIPO = {
    # ---- divergências (grupo do dossiê: contraparte x lojista x natureza)
    "DIVERGENCIA_CONTRATO_CHECKOUT": _acao(
        "Divergência de taxa no checkout", "Contestar a Orbe pela taxa aplicada a mais e devolver a diferença ao lojista.",
        "ORBE", "LOJISTA"),
    "DIVERGENCIA_CONTRATO_REMESSA": _acao(
        "Divergência de spread na remessa", "Contestar a Ponte pelo spread aplicado a mais e devolver a diferença ao lojista.",
        "PONTE", "LOJISTA"),
    "DIVERGENCIA_ISENCAO_CHECKOUT": _acao(
        "Isenção não informada à Orbe", "Combinar com o Comercial a devolução ao lojista da taxa cobrada em isenção concedida.",
        "COMERCIAL", "LOJISTA"),
    # ---- pendências do checkout
    "DEVOLUCAO_LOJISTA_ISENCAO": _acao(
        "Devolução ao lojista por isenção", "Alinhar com o Comercial e devolver ao lojista o que foi cobrado apesar da isenção.",
        "COMERCIAL", "LOJISTA"),
    "DIVERGENCIA_TAXA_CHECKOUT": _acao(
        "Divergência de taxa (checkout)", "Contestar a Orbe pela taxa diferente da contratada e ressarcir o lojista.",
        "ORBE", "LOJISTA"),
    "SALDO_CHECKOUT_NAO_POSITIVO": _acao(
        "Saldo de checkout não positivo", "Conferir o saldo do lojista no mês e avisá-lo antes de qualquer repasse.",
        "LOJISTA", "FINANCEIRO_INTERNO"),
    "LOJISTA_SEM_CONTRATO": _acao(
        "Lojista sem contrato", "Pedir ao Comercial o contrato ou as taxas do lojista para poder faturar.", "COMERCIAL"),
    "TAXA_CONTRATADA_INDEFINIDA": _acao(
        "Taxa contratada indefinida", "Pedir ao Comercial a taxa contratada da faixa que está em branco na planilha.",
        "COMERCIAL"),
    "ORBE_ESTORNO_DUPLICADO": _acao(
        "Estorno duplicado na Orbe", "Decidir se o segundo estorno vale e, se não, pedir correção à Orbe.", "ORBE"),
    "ORBE_LINHA_DUPLICADA": _acao(
        "Linha repetida no relatório da Orbe",
        "Confirmar com a Orbe se a linha repetida é duplicidade e pedir o relatório corrigido.", "ORBE"),
    "ALERTA_ANTECIPACAO": _acao(
        "Alerta de antecipação", "Avaliar o risco da antecipação de lojista novo acima das vendas e decidir o limite.",
        "COMERCIAL", "FINANCEIRO_INTERNO"),
    # ---- pendências da remessa
    "DIVERGENCIA_SPREAD_REMESSA": _acao(
        "Divergência de spread (remessa)", "Contestar a Ponte pelo spread diferente do contratado e ressarcir o lojista.",
        "PONTE", "LOJISTA"),
    "EXCESSO_NA_NOTA_REMESSA": _acao(
        "Excesso na nota da Ponte",
        "Registrar que o excesso contestado está na nota do mês e acompanhar a devolução da Ponte.",
        "FINANCEIRO_INTERNO"),
    "SPREAD_NEGATIVO": _acao(
        "Spread negativo", "Pedir à Ponte a explicação da operação com spread negativo e a correção.", "PONTE"),
    "AJUSTE_PONTE_APLICADO": _acao(
        "Ajuste da Ponte aplicado", "Conferir o ajuste de contestação aplicado na nota da Ponte.", "FINANCEIRO_INTERNO"),
    "SALDO_REMESSA_NAO_POSITIVO": _acao(
        "Saldo de remessa não positivo", "Conferir o resultado de remessa do mês antes de emitir a nota da Ponte.",
        "FINANCEIRO_INTERNO"),
    "OPERACAO_DUPLICADA": _acao(
        "Operação duplicada na Ponte", "Confirmar com a Ponte se a operação repetida é duplicidade e pedir correção.",
        "PONTE"),
    "REMESSA_FORA_COMPETENCIA": _acao(
        "Remessa fora da competência", "Decidir em que mês a operação fora da competência deve ser faturada.",
        "FINANCEIRO_INTERNO"),
    "REMESSA_SEM_CONTRATO": _acao(
        "Remessa sem contrato", "Pedir ao Comercial o spread contratado do lojista que operou sem contrato.", "COMERCIAL"),
    "CONFERIR_REPASSE_PONTE": _acao(
        "Conferir repasse da Ponte", "Conferir o valor do repasse da Ponte contra a nota emitida.", "FINANCEIRO_INTERNO"),
    # ---- pendências dos extratos
    "CREDITO_NAO_IDENTIFICADO": _acao(
        "Crédito não identificado", "Pedir ao banco o pagador do PIX recebido sem identificação.", "BANCO_AURORA"),
    "DEVOLUCAO_REPASSE": _acao(
        "Repasse devolvido", "Descobrir o motivo da devolução do repasse (banco e lojista) e decidir se repaga.",
        "LOJISTA", "BANCO_AURORA"),
    "TRANSFERENCIA_EM_TRANSITO": _acao(
        "Transferência em trânsito", "Confirmar com o banco de destino que a transferência entre contas foi creditada.",
        "BANCO_MERIDIANO"),
    "ACOMPANHAR_REMESSA_FUTURA": _acao(
        "Recurso para remessa futura", "Acompanhar com o lojista a remessa que usará o PIX recebido.", "LOJISTA"),
    "TED_PONTE_NAO_CONCILIADO": _acao(
        "TED para a Ponte não conciliada", "Conferir com a Ponte a liquidação da TED que não fecha com as operações.",
        "PONTE"),
    "LANCAMENTO_NAO_CLASSIFICADO": _acao(
        "Lançamento sem classificação", "Definir a conta contábil do lançamento sem regra.", "CONTABILIDADE"),
    "EXTRATO_NAO_FECHA": _acao(
        "Extrato não fecha", "Conferir o extrato (saldo inicial, final e movimentos) e pedir novo arquivo se preciso.",
        "FINANCEIRO_INTERNO"),
    # ---- fontes, cadastro e versões
    "FONTE_AUSENTE": _acao("Fonte ausente", "Enviar o arquivo que falta e fechar de novo, ou liberar o mês assim.",
                           "FINANCEIRO_INTERNO"),
    "LAYOUT_INESPERADO": _acao("Layout inesperado", "Conferir com quem gerou o arquivo ou ajustar o leitor.",
                               "FINANCEIRO_INTERNO"),
    "CADASTRO_AUSENTE": _acao("Cadastro ausente", "Restaurar o cadastro de condições comerciais e fechar de novo.",
                              "FINANCEIRO_INTERNO"),
    "VERSAO_CONFLITANTE": _acao("Versões conflitantes", "Conferir qual versão do arquivo vale.", "FINANCEIRO_INTERNO"),
    "VERSAO_SOBREPOSTA": _acao("Versões sobrepostas", "Conferir a união das versões do extrato.", "FINANCEIRO_INTERNO"),
    "VERSAO_SUBSTITUIDA": _acao("Versão substituída", "Conferir que a versão antiga ignorada não era a correta.",
                                "FINANCEIRO_INTERNO"),
    "LANCAMENTO_SUMIU_NA_NOVA_VERSAO": _acao(
        "Lançamento sumiu na nova versão", "Conferir por que o lançamento não está na versão nova (foi mantido).",
        "FINANCEIRO_INTERNO"),
}


def acao_do_tipo(tipo):
    """Entrada de ACOES_POR_TIPO; tipo sem entrada -> padrão (FINANCEIRO_INTERNO)."""
    return ACOES_POR_TIPO.get(tipo) or {"rotulo": tipo.replace("_", " ").capitalize(),
                                        "objetivo": "Verificar a pendência e decidir o encaminhamento.",
                                        "destinos": list(DESTINO_PADRAO)}


# ---------------------------------------------------------------- clientes novos e contratos (IA de contrato)
# Cliente novo = lojista que aparece nos arquivos do mês (EC na Orbe, CNPJ na Ponte) e não está em
# cadastro/clientes_conhecidos.csv. Só metadado do resultado/tela: não muda nenhum dos 6 CSVs oficiais.
STATUS_CLIENTE = ["CONTRATO_PENDENTE", "CONTRATO_ANALISADO", "CONFIRMADO"]
CONTRATO_LIMITE_CHARS = 60000        # texto do contrato enviado à IA (trunca e avisa)
CONTRATO_MAX_CORPO = 1500            # e-mail sugerido pela IA a partir do contrato
CONTRATO_DESTINOS = ["ORBE", "PONTE", "COMERCIAL", "LOJISTA", "CONTABILIDADE"]
