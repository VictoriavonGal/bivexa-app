"""Dados da demonstração: um escritório de uma advogada só, no tamanho real.

Uma advogada autônoma que vive da advocacia costuma ter algo como seis a dez
contratos ativos e outros tantos contatos em negociação. Os exemplos seguem
essa escala e são coerentes entre si: quem já pagou parcela tem proposta
aceita, contrato assinado e consulta no passado; quem tem consulta amanhã
ainda não tem proposta; e assim por diante.

Tudo é criado com datas relativas a hoje, para a demonstração nunca envelhecer.
"""

from datetime import timedelta

from . import regras, servicos
from .banco import executar, um


def quando(dias, hora="10:00"):
    """Data e hora a `dias` de hoje (negativo = passado)."""
    return f"{(regras.hoje() + timedelta(days=dias)).isoformat()} {hora}:00"


def util(dias):
    """Ajusta o deslocamento para cair num dia útil: futuro vai para segunda, passado volta para sexta."""
    data = regras.hoje() + timedelta(days=dias)
    while data.weekday() >= 5:
        data += timedelta(days=1 if dias > 0 else -1)
    return (data - regras.hoje()).days


def nome_dia(dias):
    """'quinta', 'amanhã'... do jeito que a assistente falaria no dia da conversa."""
    return regras.DIAS_SEMANA[(regras.hoje() + timedelta(days=dias)).weekday()]


def dia(dias):
    return (regras.hoje() + timedelta(days=dias)).isoformat()


class Demo:
    def __init__(self, escritorio):
        self.e = escritorio
        self.eid = escritorio["id"]

    # ------------------------------------------------------------ peças básicas

    def cliente(self, nome, contato, contraria, area, relato, status, criado, urgente=0, motivo="",
                origem="link de atendimento", documentos=None):
        cid = executar(
            "INSERT INTO cliente (escritorio_id, nome, contato, parte_contraria, area, relato, resumo,"
            " documentos_pendentes, status, urgente, motivo_urgencia, etapa_conversa, origem, token, criado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'agendado', ?, ?, ?)",
            self.eid, nome, contato, contraria, area, relato,
            regras.resumo_simples(relato, area, urgente, motivo),
            documentos or regras.documentos_sugeridos(area), status, urgente, motivo, origem,
            regras.novo_token(), quando(criado, "09:12"))
        self.registro(cid, "Bivexa", "Triagem do primeiro contato", f"Área: {area}. Feita por: regras fixas.",
                      quando(criado, "09:13"), "triagem registrada")
        return cid

    def conversa(self, cid, falas):
        """falas: lista de (autor, texto, dias, hora)."""
        for autor, texto, d, hora in falas:
            executar("INSERT INTO mensagem (cliente_id, autor, texto, criado_em) VALUES (?, ?, ?, ?)",
                     cid, autor, texto, quando(d, hora))

    def registro(self, cid, ator, acao, detalhe, em, verificacoes=""):
        executar("INSERT INTO registro (escritorio_id, cliente_id, ator, acao, detalhe, verificacoes, criado_em)"
                 " VALUES (?, ?, ?, ?, ?, ?, ?)", self.eid, cid, ator, acao, detalhe, verificacoes, em)

    def compromisso(self, cid, tipo, titulo, inicio, confirmado=1, obs=""):
        return executar("INSERT INTO compromisso (escritorio_id, cliente_id, tipo, titulo, inicio, confirmado, observacao)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?)", self.eid, cid, tipo, titulo, inicio, confirmado, obs)

    def servico(self, nome):
        return um("SELECT * FROM servico WHERE escritorio_id = ? AND nome = ?", self.eid, nome)

    def proposta(self, cid, servico_nome, objeto, valor, parcelas, status, criada):
        cliente = um("SELECT * FROM cliente WHERE id = ?", cid)
        s = self.servico(servico_nome)
        texto = servicos.preencher(self.e["modelo_proposta"] or servicos.MODELO_PROPOSTA, self.e, cliente,
                                   objeto, valor, parcelas)
        pid = executar(
            "INSERT INTO proposta (escritorio_id, cliente_id, servico_id, descricao_servico, valor_total, parcelas,"
            " texto, status, token, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self.eid, cid, s["id"] if s else None, objeto, valor, parcelas, texto, status, regras.novo_token(),
            quando(criada, "18:20"))
        self.registro(cid, "Bivexa", "Proposta preparada no modelo do escritório",
                      f"{servico_nome}, {regras.moeda(valor)} em {parcelas}x.", quando(criada, "18:20"),
                      "valor conferido com a tabela de honorários")
        if status != "aguardando aprovação":
            self.registro(cid, "Bivexa", "Proposta enviada ao cliente", "Aprovada pela advogada.",
                          quando(criada, "19:05"), "sem opinião jurídica")
        return pid

    def contrato(self, cid, proposta_id, status, criado, assinado=None):
        cliente = um("SELECT * FROM cliente WHERE id = ?", cid)
        p = um("SELECT * FROM proposta WHERE id = ?", proposta_id)
        texto = servicos.preencher(self.e["modelo_contrato"] or servicos.MODELO_CONTRATO, self.e, cliente,
                                   p["descricao_servico"], p["valor_total"], p["parcelas"])
        kid = executar(
            "INSERT INTO contrato (escritorio_id, proposta_id, cliente_id, texto, status, token, assinado_por,"
            " assinado_em, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self.eid, proposta_id, cid, texto, status, regras.novo_token(),
            cliente["nome"] if assinado is not None else "", quando(assinado, "20:41") if assinado is not None else "",
            quando(criado, "11:00"))
        if assinado is not None:
            self.registro(cid, "Cliente", "Contrato assinado eletronicamente", f"Assinado por {cliente['nome']}.",
                          quando(assinado, "20:41"))
            executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'cliente', ?)",
                     self.eid, cliente["nome"], "incluído ao assinar contrato")
            if cliente["parte_contraria"]:
                executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'parte contrária', ?)",
                         self.eid, cliente["parte_contraria"], f"contra {cliente['nome']}")
        return kid

    def parcelas(self, cid, contrato_id, valor_total, situacoes):
        """situacoes: lista de (dias_do_vencimento, status). Pagas registram o pagamento no vencimento."""
        total = len(situacoes)
        valor = round(valor_total / total, 2)
        for n, (d, status) in enumerate(situacoes, 1):
            pid = executar(
                "INSERT INTO parcela (escritorio_id, cliente_id, contrato_id, numero, total_parcelas, valor, vencimento,"
                " status, token, pago_em, lembrete_enviado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self.eid, cid, contrato_id, n, total, valor, dia(d), status, regras.novo_token(),
                quando(d - 1, "14:30") if status == "paga" else "", 1 if status == "paga" else 0)
            if status in ("emitida", "paga"):
                executar("UPDATE parcela SET codigo_pagamento = ? WHERE id = ?",
                         servicos.codigo_pagamento(um("SELECT * FROM parcela WHERE id = ?", pid)), pid)
            if status == "paga":
                self.registro(cid, "Cliente", "Pagamento recebido", f"Parcela {n}/{total} – {regras.moeda(valor)}",
                              quando(d - 1, "14:30"))

    def processo(self, cid, numero, tribunal, descricao, criado, andamentos=()):
        pid = executar("INSERT INTO processo (escritorio_id, cliente_id, numero, tribunal, descricao, criado_em)"
                       " VALUES (?, ?, ?, ?, ?, ?)", self.eid, cid, numero, tribunal, descricao, quando(criado, "16:00"))
        for d, texto, resumo in andamentos:
            executar("INSERT INTO andamento (processo_id, texto, resumo, criado_em) VALUES (?, ?, ?, ?)",
                     pid, texto, resumo, quando(d, "08:30"))
        return pid

    def contratado(self, cid, consulta, servico_nome, objeto, valor, situacoes, assinado, hora="14:00"):
        """Atalho para o caminho completo: consulta → proposta → contrato → parcelas."""
        self.compromisso(cid, "consulta", f"Consulta – {self.nome(cid)}", quando(consulta, hora))
        p = self.proposta(cid, servico_nome, objeto, valor, len(situacoes), "aceita", consulta)
        k = self.contrato(cid, p, "assinado", consulta + 1, assinado)
        self.parcelas(cid, k, valor, situacoes)
        return k

    def nome(self, cid):
        return um("SELECT nome FROM cliente WHERE id = ?", cid)["nome"]


def carregar(escritorio):
    d = Demo(escritorio)
    ola = f"Olá! Sou a assistente virtual do escritório {escritorio['nome']}."

    # ------------------------------------------------------------ contratados

    carlos = d.cliente(
        "Carlos Eduardo Souza", "(11) 98712-4410", "LATAM Airlines Brasil", "Consumidor",
        "Meu voo de Guarulhos para Recife foi cancelado na véspera, perdi o casamento do meu irmão e a companhia "
        "só ofereceu remarcação para três dias depois. Já pedi reembolso duas vezes e nada.",
        "contratado", -48, documentos="Bilhete e cartão de embarque; e-mails e protocolos com a companhia; "
                                      "comprovantes de gastos extras; convite do casamento")
    cc = util(-45)
    d.conversa(carlos, [
        ("cliente", "Boa noite. Meu voo de Guarulhos para Recife foi cancelado na véspera e a LATAM não devolveu o dinheiro.", cc - 3, "21:40"),
        ("bivexa", f"{ola} Sinto muito pelo transtorno. Para adiantar, qual é o seu nome completo?", cc - 3, "21:40"),
        ("cliente", "Carlos Eduardo Souza", cc - 3, "21:42"),
        ("bivexa", f"Obrigada, Carlos. A Dra. Helena tem horário para a consulta na {nome_dia(cc)} às 14h ou "
                   f"na {nome_dia(util(cc + 1))} às 10h. Qual fica melhor?", cc - 3, "21:42"),
        ("cliente", f"{nome_dia(cc).capitalize()} às 14h", cc - 3, "21:45"),
        ("bivexa", f"Consulta marcada para {nome_dia(cc)}, às 14h. Se puder, traga o bilhete, os e-mails com a "
                   "companhia e os comprovantes de gastos extras.", cc - 3, "21:45"),
        ("advogado", "Carlos, recebi os documentos. Ingressamos com a ação hoje; a Bivexa vai te avisando de cada movimentação.", -30, "17:10"),
        ("cliente", "Ótimo, muito obrigado doutora!", -30, "17:32"),
    ])
    k = d.contratado(carlos, cc, "Ação no Juizado Especial Cível",
                     "Ação de indenização por danos materiais e morais contra LATAM Airlines Brasil, pelo cancelamento "
                     "do voo GRU–REC, no Juizado Especial Cível", 2500, [(-36, "paga"), (-6, "emitida")], -42)
    pid_carlos = d.processo(carlos, "1004321-55.2026.8.26.0002", "TJSP – Juizado Especial Cível de Santo Amaro",
                            "Indenização por cancelamento de voo", -30, [
                                (-28, "Distribuído por sorteio. Cite-se a ré.", "Ação distribuída; a companhia será citada."),
                                (-15, "Juntada de AR positivo. Ré citada.", "A companhia foi citada."),
                            ])

    ana = d.cliente(
        "Ana Paula Ferreira", "ana.ferreira@gmail.com", "Ricardo Ferreira", "Família",
        "Eu e meu marido decidimos nos separar de forma amigável. Temos um apartamento financiado e um carro, "
        "sem filhos. Queremos resolver rápido e sem briga.", "contratado", -70)
    ca = util(-66)
    d.conversa(ana, [
        ("cliente", "Oi, eu e meu marido queremos nos divorciar, é tudo amigável.", -70, "12:05"),
        ("bivexa", f"{ola} Obrigada por escrever. Qual é o seu nome completo?", -70, "12:05"),
        ("cliente", "Ana Paula Ferreira", -70, "12:07"),
        ("bivexa", f"Obrigada, Ana. A Dra. Helena pode atender na {nome_dia(ca)} às 10h ou na "
                   f"{nome_dia(util(ca + 1))} às 16h. Qual prefere?", -70, "12:07"),
        ("cliente", f"{nome_dia(ca).capitalize()} às 10h", -70, "12:10"),
        ("advogado", f"Ana, a minuta do acordo está pronta. Vamos revisar juntas na reunião de {nome_dia(util(3))}?", -2, "18:00"),
        ("cliente", "Perfeito, estarei lá.", -2, "18:22"),
    ])
    d.contratado(ana, ca, "Divórcio consensual", "Divórcio consensual, com partilha do apartamento e do veículo",
                 3500, [(-58, "paga"), (-28, "paga")], ca + 2, hora="10:00")
    d.compromisso(ana, "reunião", "Reunião – revisão do acordo de partilha (Ana Paula Ferreira)", quando(util(3), "11:00"))

    roberto = d.cliente(
        "Roberto Almeida", "(11) 99654-2287", "Construtora Horizonte Ltda.", "Trabalhista",
        "Trabalhei 4 anos como mestre de obras e fui dispensado sem receber as horas extras nem o FGTS dos últimos meses.",
        "contratado", -40)
    cr = util(-37)
    d.conversa(roberto, [
        ("cliente", "Bom dia. Fui mandado embora da construtora e não pagaram minhas horas extras.", -40, "07:58"),
        ("bivexa", f"{ola} Vou te ajudar a marcar uma conversa com a Dra. Helena. Qual é o seu nome completo?", -40, "07:58"),
        ("cliente", "Roberto Almeida", -40, "08:01"),
        ("bivexa", f"Obrigada, Roberto. Ela pode te atender na {nome_dia(cr)} às 17h ou na "
                   f"{nome_dia(util(cr + 1))} às 9h.", -40, "08:01"),
        ("cliente", f"{nome_dia(cr).capitalize()} às 17h, saio do serviço antes", -40, "08:03"),
        ("bivexa", "Lembrete: a parcela 2/3 dos honorários vence em breve. O link está acima. Qualquer dúvida, é só responder.", -1, "09:00"),
    ])
    d.contratado(roberto, cr, "Reclamação trabalhista",
                 "Reclamação trabalhista contra Construtora Horizonte Ltda., com pedido de horas extras e FGTS",
                 3000, [(-28, "paga"), (2, "emitida"), (32, "programada")], cr + 2, hora="17:00")
    d.processo(roberto, "1001234-12.2026.5.02.0011", "TRT-2 – 11ª Vara do Trabalho de São Paulo",
               "Horas extras e FGTS", -26, [
                   (-25, "Designada audiência inicial.", "Audiência inicial marcada."),
               ])
    d.compromisso(roberto, "audiência", "Audiência inicial – Roberto Almeida (TRT-2, 11ª Vara)", quando(util(8), "14:00"),
                  obs="Sala 3 · levar carta de preposto da parte contrária, se houver acordo")

    juliana = d.cliente(
        "Juliana Martins", "(11) 97433-9021", "Marcos Martins", "Família",
        "Me separei há um ano e o pai da minha filha de 4 anos parou de ajudar com as despesas.",
        "contratado", -95)
    cj = util(-92)
    d.conversa(juliana, [
        ("cliente", "Oi, preciso entrar com pensão pra minha filha.", -95, "22:15"),
        ("bivexa", f"{ola} Entendi. Qual é o seu nome completo?", -95, "22:15"),
        ("cliente", "Juliana Martins", -95, "22:16"),
        ("bivexa", f"Obrigada, Juliana. A Dra. Helena pode te atender na {nome_dia(cj)} às 11h ou na "
                   f"{nome_dia(util(cj + 1))} às 15h. Também dá para ser online.", -95, "22:16"),
        ("cliente", f"Online na {nome_dia(cj)}", -95, "22:18"),
        ("bivexa", "Olá, Juliana. Uma atualização do seu processo: foi marcada audiência de conciliação no CEJUSC. "
                   "A Dra. Helena vai te passar os detalhes.", -12, "10:00"),
    ])
    d.contratado(juliana, cj, "Ação de alimentos", "Ação de alimentos em favor da filha menor, contra Marcos Martins",
                 4500, [(-85, "paga"), (-55, "paga"), (-25, "paga")], cj + 2, hora="11:00")
    d.processo(juliana, "1012876-40.2026.8.26.0100", "TJSP – 2ª Vara da Família e Sucessões do Foro Central",
               "Alimentos – filha menor", -80, [
                   (-78, "Fixados alimentos provisórios. Cite-se.", "Alimentos provisórios fixados."),
                   (-12, "Designada audiência de conciliação no CEJUSC.", "Audiência de conciliação marcada."),
               ])
    d.compromisso(juliana, "audiência", "Conciliação – Juliana Martins (CEJUSC Central)", quando(util(15), "10:30"))

    fernando = d.cliente(
        "Fernando Lima", "fernando.lima@outlook.com", "Claro S.A.", "Consumidor",
        "Cancelei meu plano em março e continuam cobrando. Agora meu nome foi parar no Serasa.",
        "contratado", -18)
    cf = util(-15)
    d.conversa(fernando, [
        ("cliente", "Cancelei a Claro e eles negativaram meu nome mesmo assim.", -18, "13:30"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -18, "13:30"),
        ("cliente", "Fernando Lima", -18, "13:31"),
        ("bivexa", f"Obrigada, Fernando. Horários com a Dra. Helena: {nome_dia(cf)} às 14h ou "
                   f"{nome_dia(util(cf + 1))} às 10h.", -18, "13:31"),
        ("cliente", nome_dia(cf).capitalize(), -18, "13:35"),
    ])
    d.contratado(fernando, cf, "Ação no Juizado Especial Cível",
                 "Ação declaratória de inexistência de débito com indenização por negativação indevida, contra Claro S.A.",
                 2500, [(-7, "paga"), (23, "programada")], cf + 2)
    d.processo(fernando, "1009988-21.2026.8.26.0003", "TJSP – Juizado Especial Cível do Jabaquara",
               "Negativação indevida", -5, [(-5, "Distribuído. Tutela de urgência em análise.", "Ação distribuída.")])

    patricia = d.cliente(
        "Patrícia Gomes", "(11) 98100-3344", "Rede Farma Saúde Ltda.", "Trabalhista",
        "A empresa me ofereceu um acordo para sair e quero saber se devo assinar.",
        "contratado", -25)
    d.conversa(patricia, [
        ("cliente", "A empresa me ofereceu um acordo pra sair. Devo assinar?", -25, "19:02"),
        ("bivexa", f"{ola} Não posso orientar sobre o caso: quem avalia é a Dra. Helena, na consulta. "
                   "Para adiantar, qual é o seu nome completo?", -25, "19:02"),
        ("cliente", "Patrícia Gomes", -25, "19:03"),
    ])
    d.contratado(patricia, util(-22), "Análise de acordo trabalhista",
                 "Análise da proposta de acordo rescisório apresentada por Rede Farma Saúde Ltda.", 800, [(-17, "paga")], -21)

    # ------------------------------------------------------------ contrato para assinar

    marcelo = d.cliente(
        "Marcelo Andrade", "(11) 96222-1830", "Padaria Bella Vista Ltda.", "Trabalhista",
        "Trabalhei 2 anos sem carteira assinada como padeiro. Saí e não recebi nada.", "proposta aceita", -12)
    d.conversa(marcelo, [
        ("cliente", "Trabalhei sem registro e saí sem receber nada.", -12, "15:20"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -12, "15:20"),
        ("cliente", "Marcelo Andrade", -12, "15:21"),
        ("bivexa", "Olá, Marcelo. Obrigada por aceitar a proposta. O contrato está pronto para a sua assinatura eletrônica.", -4, "10:15"),
        ("cliente", "Vou ver com calma no fim de semana", -4, "12:40"),
    ])
    d.compromisso(marcelo, "consulta", "Consulta – Marcelo Andrade", quando(util(-8), "16:00"))
    p = d.proposta(marcelo, "Reclamação trabalhista",
                   "Reclamação trabalhista contra Padaria Bella Vista Ltda., com pedido de reconhecimento de vínculo "
                   "e verbas rescisórias", 3000, 3, "aceita", -7)
    d.contrato(marcelo, p, "enviado para assinatura", -4)

    beatriz = d.cliente(
        "Beatriz Rocha", "beatriz.rocha@icloud.com", "Paulo Rocha", "Família",
        "Quero me divorciar. Temos dois filhos e precisamos definir guarda e pensão.", "proposta aceita", -9)
    d.conversa(beatriz, [
        ("cliente", "Preciso de ajuda com meu divórcio, temos 2 filhos.", -9, "08:45"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -9, "08:45"),
        ("cliente", "Beatriz Rocha", -9, "08:46"),
        ("cliente", "Li a proposta e aceito.", 0, "08:10"),
    ])
    d.compromisso(beatriz, "consulta", "Consulta – Beatriz Rocha", quando(util(-6), "10:00"))
    p = d.proposta(beatriz, "Divórcio consensual",
                   "Divórcio consensual com definição de guarda compartilhada, convivência e alimentos dos dois filhos",
                   4200, 3, "aceita", -5)
    k = d.contrato(beatriz, p, "aguardando aprovação", 0)
    servicos.criar_pendencia(d.eid, "contrato", k, "Contrato pronto para assinatura",
                             "Beatriz Rocha aceitou a proposta hoje. O contrato foi preenchido no seu modelo.", beatriz)

    # ------------------------------------------------------------ proposta enviada

    lucas = d.cliente(
        "Lucas Pereira", "(11) 95870-6612", "Magazine Luiza S.A.", "Consumidor",
        "Comprei uma geladeira há 40 dias, paguei e nunca entregaram. O atendimento só dá protocolo.",
        "proposta enviada", -14)
    d.conversa(lucas, [
        ("cliente", "Comprei uma geladeira e nunca chegou.", -14, "11:11"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -14, "11:11"),
        ("cliente", "Lucas Pereira", -14, "11:12"),
        ("bivexa", "Olá, Lucas. Conforme conversado na consulta, segue a proposta de honorários. Para aceitar, use o link.", -5, "19:05"),
    ])
    d.compromisso(lucas, "consulta", "Consulta – Lucas Pereira", quando(util(-6), "15:00"))
    d.proposta(lucas, "Ação no Juizado Especial Cível",
               "Ação de obrigação de entregar com indenização, contra Magazine Luiza S.A.", 2500, 2, "enviada", -5)

    camila = d.cliente(
        "Camila Ribeiro", "(11) 99301-7458", "André Ribeiro", "Família",
        "O pai do meu filho quer mudar o regime de visitas e eu não concordo.", "proposta enviada", -6)
    d.conversa(camila, [
        ("cliente", "Quero entender como fica a guarda do meu filho.", -6, "20:30"),
        ("bivexa", f"{ola} Quem avalia o caso é a Dra. Helena, na consulta. Qual é o seu nome completo?", -6, "20:30"),
        ("cliente", "Camila Ribeiro", -6, "20:31"),
        ("bivexa", "Olá, Camila. Segue a proposta de honorários conversada na consulta.", -1, "18:40"),
        ("cliente", "Recebi, vou ler hoje à noite.", -1, "19:00"),
    ])
    d.compromisso(camila, "consulta", "Consulta – Camila Ribeiro", quando(util(-3), "11:00"))
    d.proposta(camila, "Ação de alimentos", "Ação de regulamentação de convivência do filho menor", 3800, 2, "enviada", -1)

    # ------------------------------------------------------------ consulta marcada

    mariana = d.cliente(
        "Mariana Costa", "(11) 94561-0099", "Rodrigo Costa", "Família",
        "Quero entrar com pedido de pensão alimentícia para minha filha de 6 anos. O pai ajuda só quando quer.",
        "consulta marcada", -3)
    d.conversa(mariana, [
        ("cliente", "Oi, quero pedir pensão para minha filha de 6 anos.", -3, "10:20"),
        ("bivexa", f"{ola} Entendi. Qual é o seu nome completo?", -3, "10:20"),
        ("cliente", "Mariana Costa", -3, "10:21"),
        ("bivexa", "Obrigada, Mariana. Há algum outro envolvido? Pode ser o nome do pai da criança.", -3, "10:21"),
        ("cliente", "Rodrigo Costa", -3, "10:22"),
        ("bivexa", f"Horários com a Dra. Helena: {nome_dia(util(1))} às 10h ou {nome_dia(util(util(1) + 1))} às 14h. "
                   "Qual prefere?", -3, "10:22"),
        ("cliente", f"{nome_dia(util(1)).capitalize()} às 10h", -3, "10:25"),
        ("bivexa", "Combinado. Se puder, traga a certidão de nascimento da sua filha e comprovantes das despesas dela.", -3, "10:25"),
    ])
    d.compromisso(mariana, "consulta", "Consulta – Mariana Costa", quando(util(1), "10:00"))

    rafael = d.cliente(
        "Rafael Oliveira", "rafael.oliveira@gmail.com", "Logística Rápida Transportes Ltda.", "Trabalhista",
        "Sou motorista e faço jornada de 12 horas sem receber hora extra.", "consulta marcada", -2)
    d.conversa(rafael, [
        ("cliente", "Trabalho 12h por dia e não recebo hora extra.", -2, "23:10"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -2, "23:10"),
        ("cliente", "Rafael Oliveira", -2, "23:11"),
        ("bivexa", f"Tenho {nome_dia(util(2))} às 15h ou {nome_dia(util(util(2) + 1))} às 17h. Qual fica melhor?", -2, "23:11"),
        ("cliente", f"{nome_dia(util(2)).capitalize()}, mas talvez eu esteja em viagem, confirmo depois", -2, "23:14"),
        ("bivexa", f"Sem problema, deixei {nome_dia(util(2))} às 15h reservado. Vou te pedir confirmação na véspera.", -2, "23:14"),
    ])
    d.compromisso(rafael, "consulta", "Consulta – Rafael Oliveira", quando(util(2), "15:00"), confirmado=0,
                  obs="Cliente pode estar em viagem; confirmar na véspera")

    sonia = d.cliente(
        "Sônia Barbosa", "(11) 98877-1203", "Banco Pan S.A.", "Consumidor",
        "Apareceu um empréstimo consignado no meu benefício do INSS que eu nunca contratei.",
        "consulta marcada", -5)
    d.conversa(sonia, [
        ("cliente", "Tem um empréstimo no meu benefício que eu não fiz.", -5, "09:40"),
        ("bivexa", f"{ola} Qual é o seu nome completo?", -5, "09:40"),
        ("cliente", "Sônia Barbosa", -5, "09:42"),
        ("bivexa", f"Obrigada, dona Sônia. A Dra. Helena pode atender {nome_dia(util(-1))} às 14h. Pode ser?", -5, "09:42"),
        ("cliente", "Pode sim", -5, "09:50"),
    ])
    d.compromisso(sonia, "consulta", "Consulta – Sônia Barbosa", quando(util(-1), "14:00"))
    p = d.proposta(sonia, "Ação no Juizado Especial Cível",
                   "Ação declaratória de inexistência de contrato de empréstimo consignado, com devolução em dobro "
                   "e indenização, contra Banco Pan S.A.", 2500, 2, "aguardando aprovação", 0)
    servicos.criar_pendencia(d.eid, "proposta", p, "Proposta de honorários pronta",
                             "Ação no Juizado Especial Cível para Sônia Barbosa: R$ 2.500,00 em 2x.", sonia)

    thiago = d.cliente(
        "Thiago Nunes", "(11) 97012-5588", "", "Família",
        "Meu pai faleceu e preciso fazer o inventário. Somos três irmãos e há uma casa em Osasco.",
        "consulta marcada", -9, origem="indicação (cadastro manual)")
    d.compromisso(thiago, "consulta", "Consulta – Thiago Nunes", quando(util(-2), "17:00"))

    # ------------------------------------------------------------ novo contato

    gabriel = d.cliente(
        "Gabriel Santos", "(11) 96655-4321", "Mercado Bom Preço Ltda.", "Trabalhista",
        "Fui demitido ontem e me mandaram assinar um acordo em até três dias, senão não recebo nada.",
        "novo contato", 0, urgente=1, motivo="prazo para assinar acordo em até três dias")
    d.conversa(gabriel, [
        ("cliente", "Fui demitido ontem e querem que eu assine um acordo em até três dias.", 0, "08:02"),
        ("bivexa", f"{ola} Entendi que há urgência (prazo em até três dias); vou avisar o escritório agora mesmo. "
                   "Para adiantar, qual é o seu nome completo?", 0, "08:02"),
        ("cliente", "Gabriel Santos", 0, "08:04"),
        ("bivexa", "Obrigada, Gabriel. A Dra. Helena já foi avisada e vai priorizar o seu caso. "
                   "Por qual telefone podemos falar com você?", 0, "08:04"),
        ("cliente", "(11) 96655-4321", 0, "08:05"),
    ])
    servicos.criar_pendencia(d.eid, "urgencia", gabriel, "Urgente: novo contato",
                             "Prazo para assinar acordo em até três dias. Relato: \"Fui demitido ontem e me mandaram "
                             "assinar um acordo em até três dias, senão não recebo nada.\"", gabriel, urgente=True)

    renata = d.cliente(
        "Renata Carvalho", "renata.carvalho@yahoo.com.br", "Unimed Paulistana", "Consumidor",
        "O plano de saúde negou a cirurgia que o médico pediu para a minha mãe.", "novo contato", -2)
    d.conversa(renata, [
        ("cliente", "O plano negou a cirurgia da minha mãe.", -2, "17:45"),
        ("bivexa", f"{ola} Sinto muito. Qual é o seu nome completo?", -2, "17:45"),
        ("cliente", "Renata Carvalho", -2, "17:47"),
        ("bivexa", f"Obrigada, Renata. Tenho {nome_dia(util(2))} às 11h ou {nome_dia(util(util(2) + 1))} às 14h. "
                   "Qual fica melhor?", -2, "17:47"),
    ])

    eduardo = d.cliente(
        "Eduardo Prado", "(11) 3255-8890", "", "Trabalhista",
        "Ligou indicado pela Juliana Martins. Quer revisar o contrato de trabalho antes de aceitar uma proposta nova.",
        "novo contato", -1, origem="telefone (cadastro manual)")

    # ------------------------------------------------------------ compromissos sem cliente

    d.compromisso(None, "reunião", "Contador – fechamento do mês", quando(util(1), "16:00"))
    d.compromisso(None, "compromisso", "Curso na ESA OAB-SP – atualização em Direito de Família", quando(4, "19:00"))
    d.compromisso(fernando, "prazo", "Prazo: réplica – Fernando Lima (JEC Jabaquara)", quando(util(6), "23:59"))

    # ------------------------------------------------------------ publicação nova (fluxo real da Bivexa)

    proc = um("SELECT * FROM processo WHERE id = ?", pid_carlos)
    data_aud = (regras.hoje() + timedelta(days=21)).strftime("%d/%m/%Y")
    servicos.registrar_publicacao(
        escritorio, proc,
        f"Processo 1004321-55.2026.8.26.0002. Fica designada audiência de conciliação para {data_aud}, às 14h, "
        "por videoconferência. Intimem-se as partes.")

    servicos.registrar(d.eid, "Bivexa", "Exemplos de demonstração carregados", "17 clientes, 5 processos.")
    return pid_carlos
