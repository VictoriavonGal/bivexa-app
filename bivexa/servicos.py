"""Regras de negócio da Bivexa.

Aqui fica o que o produto FAZ: atender, registrar, pedir aprovação, gerar
proposta, contrato e cobrança. As rotas (telas) só chamam estas funções.

Princípio central: nada sai em nome do advogado sem o "sim" dele. Tudo o que
a Bivexa prepara para o cliente vira uma PENDÊNCIA, que o advogado aprova ou
revisa. Tudo o que acontece fica no REGISTRO DE CONDUTA.
"""

import json
from datetime import timedelta

from . import ia, regras
from .banco import executar, um, varios

# ---------------------------------------------------------------- modelos padrão

MODELO_PROPOSTA = """PROPOSTA DE HONORÁRIOS

{escritorio}
{advogado} – OAB {oab}

A {cliente}

1. Objeto
{objeto}

2. Honorários
Valor total de {valor_total}, em {parcelas} parcela(s) de {valor_parcela}, a primeira com vencimento em até 5 dias após a assinatura do contrato e as demais a cada 30 dias.

3. Despesas
Custas judiciais, emolumentos e despesas do processo não estão incluídos nos honorários.

4. Validade
Esta proposta é válida por 10 dias.

{cidade}, {data}.

{advogado}
OAB {oab}"""

MODELO_CONTRATO = """CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS

CONTRATANTE: {cliente}.
CONTRATADO(A): {advogado}, inscrito(a) na OAB sob o nº {oab}, do escritório {escritorio}.

Cláusula 1ª – Objeto. {objeto}

Cláusula 2ª – Honorários. O CONTRATANTE pagará {valor_total}, em {parcelas} parcela(s) de {valor_parcela}, por Pix ou boleto, a primeira em até 5 dias após a assinatura e as demais a cada 30 dias.

Cláusula 3ª – Despesas. Custas, emolumentos e despesas do processo correm por conta do CONTRATANTE.

Cláusula 4ª – Obrigações. O CONTRATADO atuará com zelo e diligência, sem garantia de resultado, nos termos do Código de Ética e Disciplina da OAB. O CONTRATANTE fornecerá documentos e informações verdadeiros.

Cláusula 5ª – Atraso. A parcela paga após o vencimento terá multa de 2% e juros de 1% ao mês.

Cláusula 6ª – Foro. Fica eleito o foro de {cidade}.

{cidade}, {data}."""

SERVICOS_SUGERIDOS = [
    ("Consulta jurídica", "Geral", 400.0, 1, "Consulta de até 1 hora, com análise de documentos."),
    ("Ação de alimentos", "Família", 4500.0, 3, "Petição inicial e acompanhamento até a sentença."),
    ("Divórcio consensual", "Família", 3500.0, 2, "Minuta do acordo e homologação."),
    ("Reclamação trabalhista", "Trabalhista", 3000.0, 3, "Inicial, audiências e acompanhamento até a sentença."),
    ("Análise de acordo trabalhista", "Trabalhista", 800.0, 1, "Revisão de proposta de acordo rescisório."),
    ("Ação no Juizado Especial Cível", "Consumidor", 2500.0, 2, "Inicial, audiência de conciliação e instrução."),
]


# ---------------------------------------------------------------- registro de conduta

def registrar(escritorio_id, ator, acao, detalhe="", cliente_id=None, verificacoes=None):
    """Grava uma linha no registro de conduta."""
    if isinstance(verificacoes, list):
        verificacoes = " · ".join(verificacoes)
    executar(
        "INSERT INTO registro (escritorio_id, cliente_id, ator, acao, detalhe, verificacoes, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        escritorio_id, cliente_id, ator, acao, detalhe, verificacoes or "", regras.agora_iso(),
    )


def enviar_mensagem(cliente, texto, autor="bivexa", acao="Mensagem enviada ao cliente"):
    """Envia (grava na conversa) uma mensagem ao cliente, depois de conferi-la.

    Se a verificação encontrar opinião jurídica, a mensagem é BLOQUEADA e vira
    uma pendência para o advogado, em vez de sair.
    """
    aprovada, verificacoes, motivo = regras.verificar_mensagem(texto)
    if not aprovada:
        registrar(cliente["escritorio_id"], "Bivexa", "Mensagem bloqueada antes do envio",
                  f"{motivo}. Texto: \"{texto}\"", cliente["id"], verificacoes)
        criar_pendencia(cliente["escritorio_id"], "mensagem_bloqueada", None,
                        "Mensagem bloqueada pela verificação de conduta",
                        f"A Bivexa ia enviar a {cliente['nome'] or 'um cliente'} um texto com possível "
                        f"opinião jurídica ({motivo}). Nada foi enviado.",
                        cliente_id=cliente["id"], urgente=False)
        return False
    executar("INSERT INTO mensagem (cliente_id, autor, texto, criado_em) VALUES (?, ?, ?, ?)",
             cliente["id"], autor, texto, regras.agora_iso())
    registrar(cliente["escritorio_id"], "Bivexa" if autor == "bivexa" else "Advogado(a)",
              acao, texto, cliente["id"], verificacoes)
    return True


def mensagem_do_cliente(cliente, texto):
    executar("INSERT INTO mensagem (cliente_id, autor, texto, criado_em) VALUES (?, ?, ?, ?)",
             cliente["id"], "cliente", texto, regras.agora_iso())


# ---------------------------------------------------------------- pendências

def criar_pendencia(escritorio_id, tipo, ref_id, titulo, descricao, cliente_id=None, urgente=False):
    return executar(
        "INSERT INTO pendencia (escritorio_id, cliente_id, tipo, ref_id, titulo, descricao, urgente, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        escritorio_id, cliente_id, tipo, ref_id, titulo, descricao, int(urgente), regras.agora_iso(),
    )


def resolver_pendencia(pendencia_id, status):
    executar("UPDATE pendencia SET status = ?, resolvido_em = ? WHERE id = ?",
             status, regras.agora_iso(), pendencia_id)


ROTULOS_APROVAR = {
    "urgencia": "Já falei com o cliente",
    "conflito": "Seguir com o atendimento",
    "proposta": "Aprovar e enviar",
    "contrato": "Aprovar e enviar para assinatura",
    "cobranca": "Emitir a 1ª cobrança",
    "agenda": "Confirmar na agenda",
    "mensagem": "Aprovar e enviar",
    "atraso": "Enviar aviso de atraso",
    "mensagem_bloqueada": "Ciente",
}

ROTULOS_RECUSAR = {
    "urgencia": None,
    "conflito": "Recusar o caso",
    "proposta": "Revisar antes",
    "contrato": "Revisar antes",
    "cobranca": "Ainda não",
    "agenda": "Descartar",
    "mensagem": "Editar antes",
    "atraso": "Decido depois",
    "mensagem_bloqueada": None,
}


def aprovar(escritorio, pendencia):
    """Executa o que a pendência propõe, depois do "sim" do advogado."""
    tipo = pendencia["tipo"]
    cliente = um("SELECT * FROM cliente WHERE id = ?", pendencia["cliente_id"]) if pendencia["cliente_id"] else None
    eid = escritorio["id"]
    advogado = escritorio["advogado_nome"]

    if tipo == "urgencia":
        registrar(eid, "Advogado(a)", "Urgência atendida", pendencia["descricao"], pendencia["cliente_id"])

    elif tipo == "conflito":
        executar("UPDATE cliente SET conflito = conflito || ' (liberado pelo advogado)', etapa_conversa = 'contato'"
                 " WHERE id = ?", cliente["id"])
        cliente = um("SELECT * FROM cliente WHERE id = ?", cliente["id"])
        registrar(eid, "Advogado(a)", "Conflito de interesses analisado: atendimento liberado",
                  pendencia["descricao"], cliente["id"])
        enviar_mensagem(cliente, f"Obrigada pela espera. O escritório pode atender o seu caso. "
                                 "Por qual telefone ou e-mail podemos falar com você?")

    elif tipo == "proposta":
        proposta = um("SELECT * FROM proposta WHERE id = ?", pendencia["ref_id"])
        executar("UPDATE proposta SET status = 'enviada' WHERE id = ?", proposta["id"])
        executar("UPDATE cliente SET status = 'proposta enviada' WHERE id = ?", cliente["id"])
        enviar_mensagem(cliente, f"Olá, {primeiro_nome(cliente)}. Conforme conversado na consulta, segue a "
                                 f"proposta de honorários do escritório {escritorio['nome']}. Você pode lê-la e aceitá-la pelo "
                                 f"link: /proposta/{proposta['token']}",
                        acao="Proposta enviada ao cliente")

    elif tipo == "contrato":
        contrato = um("SELECT * FROM contrato WHERE id = ?", pendencia["ref_id"])
        executar("UPDATE contrato SET status = 'enviado para assinatura' WHERE id = ?", contrato["id"])
        enviar_mensagem(cliente, f"Olá, {primeiro_nome(cliente)}. O contrato de honorários está pronto para "
                                 f"a sua assinatura eletrônica: /contrato/{contrato['token']}",
                        acao="Contrato enviado para assinatura")

    elif tipo == "cobranca":
        parcela = um("SELECT * FROM parcela WHERE id = ?", pendencia["ref_id"])
        emitir_parcela(escritorio, parcela, aprovada_pelo_advogado=True)

    elif tipo == "agenda":
        andamento = um("SELECT * FROM andamento WHERE id = ?", pendencia["ref_id"])
        processo = um("SELECT * FROM processo WHERE id = ?", andamento["processo_id"])
        inicio = andamento["data_sugerida"]
        if len(inicio) == 10:
            inicio += " 23:59:00"
        executar("INSERT INTO compromisso (escritorio_id, cliente_id, tipo, titulo, inicio, confirmado, observacao)"
                 " VALUES (?, ?, ?, ?, ?, 1, ?)",
                 eid, processo["cliente_id"], andamento["tipo_data"],
                 f"{andamento['tipo_data'].capitalize()} – {cliente['nome']} ({processo['numero']})",
                 inicio, "Data conferida e confirmada pelo advogado.")
        registrar(eid, "Advogado(a)", f"{andamento['tipo_data'].capitalize()} confirmada na agenda",
                  f"{regras.data_br(inicio)} – processo {processo['numero']}", cliente["id"])

    elif tipo == "mensagem":
        andamento = um("SELECT * FROM andamento WHERE id = ?", pendencia["ref_id"])
        enviar_mensagem(cliente, andamento["mensagem_cliente"], acao="Atualização do processo enviada ao cliente")

    elif tipo == "atraso":
        parcela = um("SELECT * FROM parcela WHERE id = ?", pendencia["ref_id"])
        enviar_mensagem(cliente, f"Olá, {primeiro_nome(cliente)}. Consta em aberto a parcela "
                                 f"{parcela['numero']}/{parcela['total_parcelas']} de {regras.moeda(parcela['valor'])}, "
                                 f"vencida em {regras.data_br(parcela['vencimento'])}. Segue o link para "
                                 f"pagamento: /pagamento/{parcela['token']}",
                        acao="Aviso de parcela em atraso enviado")

    elif tipo == "mensagem_bloqueada":
        registrar(eid, "Advogado(a)", "Bloqueio de mensagem conferido", pendencia["descricao"], pendencia["cliente_id"])

    resolver_pendencia(pendencia["id"], "aprovada")


def recusar(escritorio, pendencia):
    """O advogado disse "não" ou "ainda não"."""
    tipo = pendencia["tipo"]
    cliente = um("SELECT * FROM cliente WHERE id = ?", pendencia["cliente_id"]) if pendencia["cliente_id"] else None
    eid = escritorio["id"]
    if tipo == "conflito":
        executar("UPDATE cliente SET status = 'recusado', etapa_conversa = 'encerrada' WHERE id = ?", cliente["id"])
        enviar_mensagem(cliente, "Agradecemos o contato. Infelizmente o escritório não poderá atender este caso. "
                                 "Recomendamos procurar outro(a) advogado(a) ou a Defensoria Pública.")
        registrar(eid, "Advogado(a)", "Caso recusado por conflito de interesses", pendencia["descricao"], cliente["id"])
    elif tipo in ("proposta", "contrato"):
        tabela = "proposta" if tipo == "proposta" else "contrato"
        executar(f"UPDATE {tabela} SET status = 'em revisão' WHERE id = ?", pendencia["ref_id"])
        registrar(eid, "Advogado(a)", f"{tabela.capitalize()} devolvida para revisão", "", pendencia["cliente_id"])
    else:
        registrar(eid, "Advogado(a)", "Pendência dispensada", pendencia["titulo"], pendencia["cliente_id"])
    resolver_pendencia(pendencia["id"], "recusada")


def primeiro_nome(cliente):
    return (cliente["nome"] or "").split(" ")[0] or "tudo bem"


# ---------------------------------------------------------------- atendimento

def iniciar_conversa(escritorio):
    cliente_id = executar(
        "INSERT INTO cliente (escritorio_id, token, criado_em) VALUES (?, ?, ?)",
        escritorio["id"], regras.novo_token(), regras.agora_iso(),
    )
    return um("SELECT * FROM cliente WHERE id = ?", cliente_id)


def horarios_ocupados(escritorio_id):
    linhas = varios("SELECT inicio FROM compromisso WHERE escritorio_id = ?", escritorio_id)
    return [regras.ler_data(l["inicio"]) for l in linhas if len(l["inicio"]) > 10]


def processar_mensagem(escritorio, cliente, texto):
    """O coração do atendimento: recebe a mensagem do cliente e responde.

    A conversa segue etapas: relato → nome → parte contrária → contato →
    horário → agendado. Em qualquer etapa, uma pergunta de mérito recebe a
    resposta padrão, sem opinião jurídica.
    """
    texto = texto.strip()
    if not texto:
        return
    mensagem_do_cliente(cliente, texto)
    advogado = escritorio["advogado_nome"]
    etapa = cliente["etapa_conversa"]
    eid = escritorio["id"]

    def recarregar():
        return um("SELECT * FROM cliente WHERE id = ?", cliente["id"])

    if etapa == "relato":
        t = ia.triagem(texto)
        executar("UPDATE cliente SET relato = ?, area = ?, resumo = ?, documentos_pendentes = ?, urgente = ?,"
                 " motivo_urgencia = ?, etapa_conversa = 'nome' WHERE id = ?",
                 texto, t["area"], t["resumo"], t["documentos"], int(t["urgente"]), t["motivo"], cliente["id"])
        cliente = recarregar()
        registrar(eid, "Bivexa", "Triagem do primeiro contato",
                  f"Área: {t['area']}. Urgência: {'sim – ' + t['motivo'] if t['urgente'] else 'não'}. "
                  f"Feita por: {'inteligência artificial' if t['fonte'] == 'IA' else 'regras fixas'}.",
                  cliente["id"], ["triagem registrada"])
        resposta = f"Olá! Sou a assistente virtual do escritório {escritorio['nome']}. "
        if regras.pede_opiniao(texto):
            resposta += ("Não posso orientar sobre o caso: quem avalia é a advogada ou o advogado, na consulta. ")
        if t["urgente"]:
            resposta += f"Entendi que há urgência ({t['motivo']}); vou avisar o escritório agora mesmo. "
            criar_pendencia(eid, "urgencia", cliente["id"], "Urgente: novo contato",
                            f"{t['motivo'].capitalize()}. Relato: \"{texto}\"", cliente["id"], urgente=True)
        resposta += "Para adiantar, qual é o seu nome completo?"
        enviar_mensagem(cliente, resposta, acao="Resposta ao primeiro contato")
        return

    if regras.pede_opiniao(texto) and etapa not in ("nome", "contraria", "contato", "horario"):
        enviar_mensagem(cliente, regras.RESPOSTA_SEM_OPINIAO.format(advogado=advogado),
                        acao="Pergunta de mérito encaminhada à consulta")
        registrar(eid, "Bivexa", "Pergunta de mérito registrada para a consulta", texto, cliente["id"])
        return

    if etapa == "nome":
        executar("UPDATE cliente SET nome = ?, etapa_conversa = 'contraria' WHERE id = ?", texto.title(), cliente["id"])
        cliente = recarregar()
        enviar_mensagem(cliente, f"Obrigada, {primeiro_nome(cliente)}. Qual é o nome da outra pessoa ou empresa "
                                 "envolvida no caso? Se não houver, responda \"nenhuma\".")
        return

    if etapa == "contraria":
        contraria = "" if regras.sem_acento(texto) in ("nenhuma", "nenhum", "nao", "nao ha") else texto
        partes = varios("SELECT * FROM parte WHERE escritorio_id = ?", eid)
        conflito = regras.procurar_conflito(cliente["nome"], contraria, partes)
        executar("UPDATE cliente SET parte_contraria = ?, conflito = ? WHERE id = ?", contraria, conflito, cliente["id"])
        cliente = recarregar()
        registrar(eid, "Bivexa", "Conferência de conflito de interesses",
                  conflito or f"Nenhum conflito com \"{contraria or 'sem parte contrária'}\".",
                  cliente["id"], ["lista de clientes e partes conferida"])
        if conflito:
            executar("UPDATE cliente SET etapa_conversa = 'aguardando' WHERE id = ?", cliente["id"])
            criar_pendencia(eid, "conflito", cliente["id"], "Possível conflito de interesses",
                            f"{conflito}. Novo contato: {cliente['nome']}, contra {contraria}.",
                            cliente["id"], urgente=bool(cliente["urgente"]))
            enviar_mensagem(cliente, f"Obrigada. Antes de marcar a consulta, preciso confirmar com o escritório "
                                     "se o escritório pode atender o seu caso. Retornaremos em breve por aqui.")
            return
        executar("UPDATE cliente SET etapa_conversa = 'contato' WHERE id = ?", cliente["id"])
        enviar_mensagem(cliente, "Por qual telefone ou e-mail podemos falar com você?")
        return

    if etapa == "contato":
        opcoes = regras.horarios_livres(escritorio["horarios"], escritorio["duracao_consulta"],
                                        horarios_ocupados(eid), quantidade=3)
        executar("UPDATE cliente SET contato = ?, etapa_conversa = 'horario', opcoes_horario = ? WHERE id = ?",
                 texto, json.dumps([o.strftime("%Y-%m-%d %H:%M:%S") for o in opcoes]), cliente["id"])
        cliente = recarregar()
        resposta = ""
        if cliente["urgente"]:
            resposta = f"Como o seu caso tem urgência, o escritório já foi avisado e pode falar com você antes. "
        lista = "; ".join(f"{i + 1}) {regras.data_extenso(o)}" for i, o in enumerate(opcoes))
        modo = " Pode ser por vídeo ou no escritório." if escritorio["consulta_por_video"] else ""
        resposta += f"Para a consulta, há estes horários: {lista}. Responda com o número da opção.{modo}"
        enviar_mensagem(cliente, resposta, acao="Horários de consulta oferecidos")
        return

    if etapa == "horario":
        opcoes = json.loads(cliente["opcoes_horario"] or "[]")
        escolha = next((int(c) for c in texto if c.isdigit()), 0)
        if not 1 <= escolha <= len(opcoes):
            enviar_mensagem(cliente, "Não entendi a opção. Responda com 1, 2 ou 3, por favor.")
            return
        inicio = opcoes[escolha - 1]
        if regras.ler_data(inicio) in horarios_ocupados(eid):
            executar("UPDATE cliente SET etapa_conversa = 'contato' WHERE id = ?", cliente["id"])
            enviar_mensagem(cliente, "Esse horário acabou de ser ocupado. Vou buscar outras opções.")
            return processar_mensagem(escritorio, recarregar(), cliente["contato"])
        executar("INSERT INTO compromisso (escritorio_id, cliente_id, tipo, titulo, inicio, confirmado, observacao)"
                 " VALUES (?, ?, 'consulta', ?, ?, 1, ?)",
                 eid, cliente["id"], f"Consulta – {cliente['nome']}", inicio, "Marcada pela Bivexa no atendimento.")
        executar("UPDATE cliente SET status = 'consulta marcada', etapa_conversa = 'agendado' WHERE id = ?",
                 cliente["id"])
        cliente = recarregar()
        registrar(eid, "Bivexa", "Consulta marcada", regras.data_extenso(inicio), cliente["id"], ["agenda conferida"])
        enviar_mensagem(cliente, f"Consulta confirmada: {regras.data_extenso(inicio)}, com {advogado} (OAB {escritorio['oab']}). "
                                 f"Se puder, traga: {cliente['documentos_pendentes']}. Envio um lembrete na véspera.",
                        acao="Confirmação de consulta enviada")
        return

    # Conversa já encerrada ou aguardando: só registra.
    enviar_mensagem(cliente, f"Recebido. Vou repassar a sua mensagem ao escritório.")


# ---------------------------------------------------------------- proposta e contrato

class _Seguro(dict):
    def __missing__(self, chave):
        return "{" + chave + "}"


def preencher(modelo, escritorio, cliente, objeto, valor_total, parcelas):
    valor_parcela = round(valor_total / parcelas, 2)
    dados = _Seguro(
        escritorio=escritorio["nome"], advogado=escritorio["advogado_nome"], oab=escritorio["oab"],
        cliente=cliente["nome"], objeto=objeto, valor_total=regras.moeda(valor_total),
        parcelas=parcelas, valor_parcela=regras.moeda(valor_parcela),
        cidade=escritorio["cidade"] or "São Paulo", data=regras.data_br(regras.hoje()),
    )
    return modelo.format_map(dados)


def preparar_proposta(escritorio, cliente, servico, frase, valor_total, parcelas):
    objeto, fonte = ia.descrever_servico(frase, servico["nome"], servico["area"])
    texto = preencher(escritorio["modelo_proposta"] or MODELO_PROPOSTA, escritorio, cliente,
                      objeto, valor_total, parcelas)
    proposta_id = executar(
        "INSERT INTO proposta (escritorio_id, cliente_id, servico_id, descricao_servico, valor_total, parcelas,"
        " texto, status, token, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, 'aguardando aprovação', ?, ?)",
        escritorio["id"], cliente["id"], servico["id"], objeto, valor_total, parcelas, texto,
        regras.novo_token(), regras.agora_iso(),
    )
    alerta = ""
    if valor_total < servico["valor_total"]:
        alerta = f" Atenção: valor abaixo da sua tabela ({regras.moeda(servico['valor_total'])})."
    criar_pendencia(escritorio["id"], "proposta", proposta_id, "Proposta de honorários pronta",
                    f"{servico['nome']} para {cliente['nome']}: {regras.moeda(valor_total)} em {parcelas}x.{alerta}",
                    cliente["id"])
    registrar(escritorio["id"], "Bivexa", "Proposta preparada no modelo do escritório",
              f"{servico['nome']}, {regras.moeda(valor_total)} em {parcelas}x. Objeto redigido por: "
              f"{'inteligência artificial' if fonte == 'IA' else 'regras fixas'}.",
              cliente["id"], ["valor conferido com a tabela de honorários"])
    return proposta_id


def aceitar_proposta(proposta):
    escritorio = um("SELECT * FROM escritorio WHERE id = ?", proposta["escritorio_id"])
    cliente = um("SELECT * FROM cliente WHERE id = ?", proposta["cliente_id"])
    executar("UPDATE proposta SET status = 'aceita' WHERE id = ?", proposta["id"])
    executar("UPDATE cliente SET status = 'proposta aceita' WHERE id = ?", cliente["id"])
    registrar(escritorio["id"], "Cliente", "Proposta aceita pelo cliente", "", cliente["id"])
    texto = preencher(escritorio["modelo_contrato"] or MODELO_CONTRATO, escritorio, cliente,
                      proposta["descricao_servico"], proposta["valor_total"], proposta["parcelas"])
    contrato_id = executar(
        "INSERT INTO contrato (escritorio_id, proposta_id, cliente_id, texto, status, token, criado_em)"
        " VALUES (?, ?, ?, ?, 'aguardando aprovação', ?, ?)",
        escritorio["id"], proposta["id"], cliente["id"], texto, regras.novo_token(), regras.agora_iso(),
    )
    criar_pendencia(escritorio["id"], "contrato", contrato_id, "Contrato pronto para assinatura",
                    f"{cliente['nome']} aceitou a proposta. O contrato foi preenchido no seu modelo.", cliente["id"])
    registrar(escritorio["id"], "Bivexa", "Contrato preenchido no modelo do escritório", "", cliente["id"])


def assinar_contrato(contrato, nome_assinatura):
    escritorio = um("SELECT * FROM escritorio WHERE id = ?", contrato["escritorio_id"])
    cliente = um("SELECT * FROM cliente WHERE id = ?", contrato["cliente_id"])
    proposta = um("SELECT * FROM proposta WHERE id = ?", contrato["proposta_id"])
    executar("UPDATE contrato SET status = 'assinado', assinado_por = ?, assinado_em = ? WHERE id = ?",
             nome_assinatura, regras.agora_iso(), contrato["id"])
    executar("UPDATE cliente SET status = 'contratado' WHERE id = ?", cliente["id"])
    executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'cliente', ?)",
             escritorio["id"], cliente["nome"], "incluído ao assinar contrato")
    if cliente["parte_contraria"]:
        executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'parte contrária', ?)",
                 escritorio["id"], cliente["parte_contraria"], f"contra {cliente['nome']}")
    registrar(escritorio["id"], "Cliente", "Contrato assinado eletronicamente",
              f"Assinado por {nome_assinatura}.", cliente["id"])

    total = proposta["parcelas"]
    valor = round(proposta["valor_total"] / total, 2)
    primeira = regras.hoje() + timedelta(days=5)
    primeira_id = None
    for n in range(1, total + 1):
        vencimento = primeira + timedelta(days=30 * (n - 1))
        pid = executar(
            "INSERT INTO parcela (escritorio_id, cliente_id, contrato_id, numero, total_parcelas, valor, vencimento,"
            " status, token) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            escritorio["id"], cliente["id"], contrato["id"], n, total, valor, vencimento.isoformat(),
            "aguardando aprovação" if n == 1 else "programada", regras.novo_token(),
        )
        if n == 1:
            primeira_id = pid
    criar_pendencia(escritorio["id"], "cobranca", primeira_id, "Primeira cobrança pronta",
                    f"Parcela 1/{total} de {regras.moeda(valor)} para {cliente['nome']}, vencimento "
                    f"{regras.data_br(primeira)}. As demais serão emitidas e lembradas automaticamente.",
                    cliente["id"])


def codigo_pagamento(parcela):
    """Código de pagamento de DEMONSTRAÇÃO (não é um Pix real)."""
    return f"DEMO-PIX-{parcela['id']:05d}-{parcela['token'][:6].upper()}"


def emitir_parcela(escritorio, parcela, aprovada_pelo_advogado=False):
    cliente = um("SELECT * FROM cliente WHERE id = ?", parcela["cliente_id"])
    executar("UPDATE parcela SET status = 'emitida', codigo_pagamento = ? WHERE id = ?",
             codigo_pagamento(parcela), parcela["id"])
    origem = "aprovada pelo advogado" if aprovada_pelo_advogado else "emissão automática programada"
    enviar_mensagem(cliente, f"Olá, {primeiro_nome(cliente)}. Segue a cobrança da parcela "
                             f"{parcela['numero']}/{parcela['total_parcelas']} dos honorários, de "
                             f"{regras.moeda(parcela['valor'])}, com vencimento em "
                             f"{regras.data_br(parcela['vencimento'])}: /pagamento/{parcela['token']}",
                    acao=f"Cobrança enviada ({origem})")


def pagar_parcela(parcela):
    executar("UPDATE parcela SET status = 'paga', pago_em = ? WHERE id = ?", regras.agora_iso(), parcela["id"])
    executar("UPDATE pendencia SET status = 'resolvida', resolvido_em = ? WHERE tipo = 'atraso' AND ref_id = ?"
             " AND status = 'pendente'", regras.agora_iso(), parcela["id"])
    registrar(parcela["escritorio_id"], "Cliente", "Pagamento recebido",
              f"Parcela {parcela['numero']}/{parcela['total_parcelas']} – {regras.moeda(parcela['valor'])}",
              parcela["cliente_id"])


# ---------------------------------------------------------------- rotina diária

def rotina_diaria(escritorio):
    """Roda sempre que o advogado abre o painel. É idempotente: rodar duas
    vezes no mesmo dia não duplica nada.

    1. Emite as parcelas programadas que vencem nos próximos dias, com lembrete.
    2. Lembra o cliente das parcelas emitidas que vencem em breve.
    3. Marca como atrasadas as parcelas vencidas e avisa o advogado.
    4. Lembra o cliente da consulta de amanhã.
    """
    eid = escritorio["id"]
    hoje = regras.hoje()
    janela = hoje + timedelta(days=escritorio["lembrete_dias"] or 3)

    for p in varios("SELECT * FROM parcela WHERE escritorio_id = ? AND status = 'programada' AND vencimento <= ?",
                    eid, janela.isoformat()):
        emitir_parcela(escritorio, p)
        executar("UPDATE parcela SET lembrete_enviado = 1 WHERE id = ?", p["id"])

    for p in varios("SELECT * FROM parcela WHERE escritorio_id = ? AND status = 'emitida' AND lembrete_enviado = 0"
                    " AND vencimento <= ? AND vencimento >= ?", eid, janela.isoformat(), hoje.isoformat()):
        cliente = um("SELECT * FROM cliente WHERE id = ?", p["cliente_id"])
        enviar_mensagem(cliente, f"Lembrete: a parcela {p['numero']}/{p['total_parcelas']} de "
                                 f"{regras.moeda(p['valor'])} vence em {regras.data_br(p['vencimento'])}. "
                                 f"Link para pagamento: /pagamento/{p['token']}",
                        acao="Lembrete de vencimento enviado")
        executar("UPDATE parcela SET lembrete_enviado = 1 WHERE id = ?", p["id"])

    for p in varios("SELECT * FROM parcela WHERE escritorio_id = ? AND status = 'emitida' AND vencimento < ?",
                    eid, hoje.isoformat()):
        executar("UPDATE parcela SET status = 'atrasada' WHERE id = ?", p["id"])
        cliente = um("SELECT * FROM cliente WHERE id = ?", p["cliente_id"])
        criar_pendencia(eid, "atraso", p["id"], "Parcela em atraso",
                        f"{cliente['nome']}: parcela {p['numero']}/{p['total_parcelas']} de "
                        f"{regras.moeda(p['valor'])}, vencida em {regras.data_br(p['vencimento'])}.",
                        cliente["id"])
        registrar(eid, "Bivexa", "Atraso identificado e avisado ao advogado", "", cliente["id"])

    amanha = (hoje + timedelta(days=1)).isoformat()
    for c in varios("SELECT * FROM compromisso WHERE escritorio_id = ? AND tipo = 'consulta' AND cliente_id IS NOT NULL"
                    " AND substr(inicio, 1, 10) = ?", eid, amanha):
        ja = um("SELECT id FROM registro WHERE cliente_id = ? AND acao = 'Lembrete de consulta enviado'"
                " AND detalhe LIKE ?", c["cliente_id"], f"%{regras.data_br(c['inicio'])}%")
        if not ja:
            cliente = um("SELECT * FROM cliente WHERE id = ?", c["cliente_id"])
            executar("INSERT INTO mensagem (cliente_id, autor, texto, criado_em) VALUES (?, 'bivexa', ?, ?)",
                     cliente["id"], f"Lembrete: sua consulta é amanhã, {regras.data_extenso(c['inicio'])}.",
                     regras.agora_iso())
            registrar(eid, "Bivexa", "Lembrete de consulta enviado", regras.data_br(c["inicio"]), cliente["id"],
                      ["sem opinião jurídica"])


# ---------------------------------------------------------------- processos

def registrar_publicacao(escritorio, processo, texto):
    cliente = um("SELECT * FROM cliente WHERE id = ?", processo["cliente_id"])
    leitura = ia.ler_publicacao(texto, cliente["nome"])
    andamento_id = executar(
        "INSERT INTO andamento (processo_id, texto, resumo, data_sugerida, tipo_data, mensagem_cliente, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        processo["id"], texto, leitura["resumo"], leitura["data"], leitura["tipo"], leitura["mensagem"],
        regras.agora_iso(),
    )
    registrar(escritorio["id"], "Bivexa", "Nova publicação lida",
              f"Processo {processo['numero']}. Resumo: {leitura['resumo']} "
              f"(feito por: {'inteligência artificial' if leitura['fonte'] == 'IA' else 'regras fixas'})",
              cliente["id"])
    if leitura["data"]:
        criar_pendencia(escritorio["id"], "agenda", andamento_id,
                        f"Confirmar {leitura['tipo']} na agenda",
                        f"{cliente['nome']} – {processo['numero']}: {leitura['tipo']} em "
                        f"{regras.data_br(leitura['data'])}. {leitura['explicacao']}",
                        cliente["id"], urgente=(leitura["tipo"] == "prazo"))
    criar_pendencia(escritorio["id"], "mensagem", andamento_id, "Aviso ao cliente pronto",
                    f"Rascunho para {cliente['nome']}: \"{leitura['mensagem']}\"", cliente["id"])
    return andamento_id


# ---------------------------------------------------------------- conta nova e demonstração

def preparar_escritorio_novo(escritorio_id):
    """Dá ao escritório recém-criado uma tabela de honorários e modelos editáveis."""
    for nome, area, valor, parcelas, descricao in SERVICOS_SUGERIDOS:
        executar("INSERT INTO servico (escritorio_id, nome, area, valor_total, parcelas, descricao)"
                 " VALUES (?, ?, ?, ?, ?, ?)", escritorio_id, nome, area, valor, parcelas, descricao)
    executar("UPDATE escritorio SET modelo_proposta = ?, modelo_contrato = ?, horarios = ? WHERE id = ?",
             MODELO_PROPOSTA, MODELO_CONTRATO, json.dumps(regras.HORARIOS_PADRAO), escritorio_id)
    registrar(escritorio_id, "Advogado(a)", "Conta criada", "Tabela de honorários e modelos sugeridos carregados.")


def carregar_exemplos(escritorio):
    """Cria clientes e processos de exemplo, marcados como EXEMPLO, para demonstração."""
    eid = escritorio["id"]
    agora = regras.agora_iso()
    executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'cliente', 'EXEMPLO')",
             eid, "Transportes Ipê")

    def novo_cliente(nome, contato, contraria, area, relato, status, urgente=0, motivo=""):
        cid = executar(
            "INSERT INTO cliente (escritorio_id, nome, contato, parte_contraria, area, relato, resumo,"
            " documentos_pendentes, status, urgente, motivo_urgencia, etapa_conversa, origem, token, criado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'agendado', 'exemplo', ?, ?)",
            eid, nome, contato, contraria, area, relato,
            regras.resumo_simples(relato, area, urgente, motivo), regras.documentos_sugeridos(area),
            status, urgente, motivo, regras.novo_token(), agora,
        )
        executar("INSERT INTO mensagem (cliente_id, autor, texto, criado_em) VALUES (?, 'cliente', ?, ?)", cid, relato, agora)
        return cid

    mariana = novo_cliente("Mariana Costa (EXEMPLO)", "(11) 90000-0001", "Rodrigo Costa", "Família",
                           "Quero entrar com pedido de pensão alimentícia para minha filha de 6 anos.", "consulta marcada")
    amanha = regras.hoje() + timedelta(days=1)
    executar("INSERT INTO compromisso (escritorio_id, cliente_id, tipo, titulo, inicio, confirmado, observacao)"
             " VALUES (?, ?, 'consulta', ?, ?, 1, 'EXEMPLO')",
             eid, mariana, "Consulta – Mariana Costa (EXEMPLO)", f"{amanha.isoformat()} 10:00:00")
    registrar(eid, "Bivexa", "Consulta marcada", regras.data_extenso(f"{amanha.isoformat()} 10:00:00"), mariana)

    carlos = novo_cliente("Carlos Souza (EXEMPLO)", "carlos@exemplo.com", "Companhia Aérea Exemplo", "Consumidor",
                          "Meu voo foi cancelado e perdi a conexão. A companhia não me reembolsou.", "contratado")
    executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, 'cliente', 'EXEMPLO')",
             eid, "Carlos Souza (EXEMPLO)")
    pid = executar("INSERT INTO processo (escritorio_id, cliente_id, numero, tribunal, descricao, criado_em)"
                   " VALUES (?, ?, ?, ?, ?, ?)", eid, carlos, "1004321-55.2026.8.26.0002", "TJSP – Juizado Especial Cível",
                   "Indenização por cancelamento de voo (EXEMPLO)", agora)
    vencida = (regras.hoje() - timedelta(days=4)).isoformat()
    for n, (venc, status) in enumerate([(vencida, "emitida"), ((regras.hoje() + timedelta(days=26)).isoformat(), "programada")], 1):
        executar("INSERT INTO parcela (escritorio_id, cliente_id, numero, total_parcelas, valor, vencimento, status,"
                 " codigo_pagamento, token) VALUES (?, ?, ?, 2, 1250, ?, ?, ?, ?)",
                 eid, carlos, n, venc, status, "DEMO-PIX-EXEMPLO", regras.novo_token())
    return pid
