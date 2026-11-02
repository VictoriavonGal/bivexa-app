"""Painel do advogado: tudo o que exige o olhar dele fica aqui."""

import json
from datetime import timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import regras, servicos
from . import login_obrigatorio
from .banco import executar, um, varios

painel = Blueprint("painel", __name__, url_prefix="/painel")


def meu(tabela, item_id):
    """Busca um item do escritório logado; 404 se for de outro escritório."""
    linha = um(f"SELECT * FROM {tabela} WHERE id = ? AND escritorio_id = ?", item_id, g.escritorio["id"])
    if linha is None:
        abort(404)
    return linha


def esc_id():
    return g.escritorio["id"]


# ---------------------------------------------------------------- primeiros passos

@painel.route("/primeiros-passos", methods=["GET", "POST"])
@login_obrigatorio
def primeiros_passos():
    passo = int(request.args.get("passo", 1))
    e = g.escritorio
    if request.method == "POST":
        f = request.form
        if passo == 1:
            executar("UPDATE escritorio SET telefone = ?, cidade = ?, uf = ?, areas = ? WHERE id = ?",
                     f.get("telefone", ""), f.get("cidade", "") or "São Paulo", (f.get("uf", "SP") or "SP")[:2].upper(),
                     ", ".join(f.getlist("areas")), e["id"])
            return redirect(url_for("painel.primeiros_passos", passo=2))
        if passo == 2:
            _salvar_horarios(f)
            return redirect(url_for("painel.primeiros_passos", passo=3))
        if passo == 3:
            _salvar_tabela(f)
            executar("UPDATE escritorio SET configurado = 1 WHERE id = ?", e["id"])
            servicos.registrar(e["id"], "Advogado(a)", "Configuração inicial concluída",
                               "Dados, horários e tabela de honorários definidos.")
            flash("Tudo pronto. Abaixo está o link de atendimento do seu escritório: "
                  "é ele que você divulga aos clientes.", "ok")
            return redirect(url_for("painel.hoje"))
    servicos_lista = varios("SELECT * FROM servico WHERE escritorio_id = ? ORDER BY id", e["id"])
    return render_template("painel/primeiros_passos.html", passo=passo, horarios=regras.ler_horarios(e["horarios"]),
                           servicos=servicos_lista, dias=regras.DIAS_SEMANA,
                           areas_marcadas=[a.strip() for a in (e["areas"] or "").split(",") if a.strip()],
                           areas=list(regras.AREAS.keys()))


def _salvar_horarios(f):
    horarios = {
        "dias": [int(d) for d in f.getlist("dias")] or [0, 1, 2, 3, 4],
        "inicio": f.get("inicio") or "09:00",
        "fim": f.get("fim") or "18:00",
        "almoco_inicio": f.get("almoco_inicio") or "",
        "almoco_fim": f.get("almoco_fim") or "",
    }
    executar("UPDATE escritorio SET horarios = ?, duracao_consulta = ?, consulta_por_video = ?, lembrete_dias = ?"
             " WHERE id = ?", json.dumps(horarios), int(f.get("duracao") or 60), 1 if f.get("video") else 0,
             int(f.get("lembrete_dias") or 3), esc_id())


def _salvar_tabela(f):
    for s in varios("SELECT * FROM servico WHERE escritorio_id = ?", esc_id()):
        prefixo = f"s{s['id']}_"
        if f.get(prefixo + "nome") is None:
            continue
        try:
            valor = regras.ler_valor(f.get(prefixo + "valor") or s["valor_total"])
        except ValueError:
            valor = s["valor_total"]
        executar("UPDATE servico SET nome = ?, valor_total = ?, parcelas = ?, ativo = ? WHERE id = ?",
                 f.get(prefixo + "nome") or s["nome"], valor, max(1, int(f.get(prefixo + "parcelas") or 1)),
                 1 if f.get(prefixo + "ativo") else 0, s["id"])


# ---------------------------------------------------------------- hoje

@painel.route("/")
@login_obrigatorio
def hoje():
    e = g.escritorio
    servicos.rotina_diaria(e)
    pendencias = varios(
        "SELECT p.*, c.nome AS cliente_nome FROM pendencia p LEFT JOIN cliente c ON c.id = p.cliente_id"
        " WHERE p.escritorio_id = ? AND p.status = 'pendente' ORDER BY p.urgente DESC, p.id DESC", e["id"])
    agora = regras.agora().strftime("%Y-%m-%d %H:%M:%S")
    limite = (regras.agora() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    compromissos = varios(
        "SELECT k.*, c.nome AS cliente_nome, c.resumo, c.id AS cid FROM compromisso k LEFT JOIN cliente c"
        " ON c.id = k.cliente_id WHERE k.escritorio_id = ? AND k.inicio >= ? AND k.inicio <= ? ORDER BY k.inicio",
        e["id"], agora[:10], limite)
    mes = regras.hoje().strftime("%Y-%m")
    financeiro = {
        "a_receber": um("SELECT COALESCE(SUM(valor),0) v FROM parcela WHERE escritorio_id = ? AND status IN"
                        " ('emitida','programada','aguardando aprovação') AND substr(vencimento,1,7) = ?", e["id"], mes)["v"],
        "recebido": um("SELECT COALESCE(SUM(valor),0) v FROM parcela WHERE escritorio_id = ? AND status = 'paga'"
                       " AND substr(pago_em,1,7) = ?", e["id"], mes)["v"],
        "atrasado": um("SELECT COALESCE(SUM(valor),0) v FROM parcela WHERE escritorio_id = ? AND status = 'atrasada'",
                       e["id"])["v"],
    }
    novos = um("SELECT COUNT(*) n FROM cliente WHERE escritorio_id = ? AND nome != '' AND criado_em >= ?",
               e["id"], (regras.hoje() - timedelta(days=7)).isoformat())["n"]
    tem_exemplos = um("SELECT COUNT(*) n FROM cliente WHERE escritorio_id = ?", e["id"])["n"] > 0
    hoje_extenso = regras.data_extenso(regras.hoje()).capitalize()
    return render_template("painel/hoje.html", hoje_extenso=hoje_extenso, pendencias=pendencias, compromissos=compromissos,
                           financeiro=financeiro, novos=novos, tem_exemplos=tem_exemplos,
                           rotulo_sim=servicos.ROTULOS_APROVAR, rotulo_nao=servicos.ROTULOS_RECUSAR)


@painel.route("/exemplos", methods=["POST"])
@login_obrigatorio
def exemplos():
    servicos.carregar_exemplos(g.escritorio)
    flash("Exemplos carregados. Eles estão marcados como EXEMPLO.", "ok")
    return redirect(url_for("painel.hoje"))


# ---------------------------------------------------------------- aprovações

@painel.route("/aprovacoes")
@login_obrigatorio
def aprovacoes():
    pendentes = varios(
        "SELECT p.*, c.nome AS cliente_nome FROM pendencia p LEFT JOIN cliente c ON c.id = p.cliente_id"
        " WHERE p.escritorio_id = ? AND p.status = 'pendente' ORDER BY p.urgente DESC, p.id DESC", esc_id())
    resolvidas = varios(
        "SELECT p.*, c.nome AS cliente_nome FROM pendencia p LEFT JOIN cliente c ON c.id = p.cliente_id"
        " WHERE p.escritorio_id = ? AND p.status != 'pendente' ORDER BY p.resolvido_em DESC LIMIT 30", esc_id())
    return render_template("painel/aprovacoes.html", pendencias=pendentes, resolvidas=resolvidas,
                           rotulo_sim=servicos.ROTULOS_APROVAR, rotulo_nao=servicos.ROTULOS_RECUSAR)


@painel.route("/aprovacoes/<int:pid>/<acao>", methods=["POST"])
@login_obrigatorio
def decidir(pid, acao):
    pendencia = meu("pendencia", pid)
    if pendencia["status"] != "pendente":
        flash("Esta pendência já foi resolvida.", "erro")
        return redirect(request.referrer or url_for("painel.hoje"))
    if acao == "aprovar":
        servicos.aprovar(g.escritorio, pendencia)
        flash(f"Feito: {servicos.ROTULOS_APROVAR.get(pendencia['tipo'], 'aprovado').lower()}.", "ok")
    elif acao == "recusar":
        servicos.recusar(g.escritorio, pendencia)
        if pendencia["tipo"] == "proposta":
            return redirect(url_for("painel.editar_proposta", proposta_id=pendencia["ref_id"]))
        if pendencia["tipo"] == "contrato":
            return redirect(url_for("painel.editar_contrato", contrato_id=pendencia["ref_id"]))
        if pendencia["tipo"] == "mensagem":
            return redirect(url_for("painel.editar_mensagem", andamento_id=pendencia["ref_id"]))
        flash("Anotado. Nada foi enviado.", "ok")
    else:
        abort(404)
    return redirect(request.referrer or url_for("painel.hoje"))


# ---------------------------------------------------------------- clientes

ETAPAS_FUNIL = ["novo contato", "consulta marcada", "proposta enviada", "proposta aceita", "contratado"]


@painel.route("/clientes")
@login_obrigatorio
def clientes():
    todos = varios("SELECT * FROM cliente WHERE escritorio_id = ? AND nome != '' ORDER BY urgente DESC, id DESC",
                   esc_id())
    colunas = {etapa: [c for c in todos if c["status"] == etapa] for etapa in ETAPAS_FUNIL}
    outros = [c for c in todos if c["status"] not in ETAPAS_FUNIL]
    return render_template("painel/clientes.html", colunas=colunas, outros=outros, total=len(todos))


@painel.route("/clientes/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_cliente():
    """Para quem chegou por telefone, indicação ou no balcão."""
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip().title()
        if not nome:
            flash("Informe o nome do cliente.", "erro")
            return render_template("painel/cliente_novo.html", dados=f)
        relato = f.get("relato", "").strip()
        partes = varios("SELECT * FROM parte WHERE escritorio_id = ?", esc_id())
        conflito = regras.procurar_conflito(nome, f.get("parte_contraria", ""), partes)
        area = f.get("area") or regras.classificar_area(relato)
        urgente, motivo = regras.detectar_urgencia(relato)
        cid = executar(
            "INSERT INTO cliente (escritorio_id, nome, contato, parte_contraria, area, relato, resumo,"
            " documentos_pendentes, status, urgente, motivo_urgencia, conflito, etapa_conversa, origem, token, criado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'novo contato', ?, ?, ?, 'agendado', 'cadastro manual', ?, ?)",
            esc_id(), nome, f.get("contato", ""), f.get("parte_contraria", ""), area, relato,
            regras.resumo_simples(relato, area, urgente, motivo) if relato else "",
            regras.documentos_sugeridos(area), int(urgente), motivo, conflito, regras.novo_token(), regras.agora_iso())
        servicos.registrar(esc_id(), "Advogado(a)", "Cliente cadastrado manualmente",
                           f"Conflito: {conflito or 'nenhum'}.", cid, ["lista de clientes e partes conferida"])
        if conflito:
            flash(f"Atenção: {conflito}. Confira antes de seguir.", "erro")
        else:
            flash("Cliente cadastrado. Nenhum conflito de interesses encontrado.", "ok")
        return redirect(url_for("painel.cliente", cliente_id=cid))
    return render_template("painel/cliente_novo.html", dados={}, areas=list(regras.AREAS.keys()))


@painel.route("/clientes/<int:cliente_id>")
@login_obrigatorio
def cliente(cliente_id):
    c = meu("cliente", cliente_id)
    return render_template(
        "painel/cliente.html", c=c,
        mensagens=varios("SELECT * FROM mensagem WHERE cliente_id = ? ORDER BY id", c["id"]),
        compromissos=varios("SELECT * FROM compromisso WHERE cliente_id = ? ORDER BY inicio", c["id"]),
        propostas=varios("SELECT * FROM proposta WHERE cliente_id = ? ORDER BY id DESC", c["id"]),
        contratos=varios("SELECT * FROM contrato WHERE cliente_id = ? ORDER BY id DESC", c["id"]),
        parcelas=varios("SELECT * FROM parcela WHERE cliente_id = ? ORDER BY numero", c["id"]),
        processos=varios("SELECT * FROM processo WHERE cliente_id = ? ORDER BY id", c["id"]),
        registros=varios("SELECT * FROM registro WHERE cliente_id = ? ORDER BY id DESC", c["id"]),
        pendencias=varios("SELECT * FROM pendencia WHERE cliente_id = ? AND status = 'pendente'", c["id"]),
    )


@painel.route("/clientes/<int:cliente_id>/proposta", methods=["GET", "POST"])
@login_obrigatorio
def nova_proposta(cliente_id):
    c = meu("cliente", cliente_id)
    tabela = varios("SELECT * FROM servico WHERE escritorio_id = ? AND ativo = 1 ORDER BY area, nome", esc_id())
    if request.method == "POST":
        f = request.form
        servico = meu("servico", int(f.get("servico_id") or 0))
        try:
            valor = regras.ler_valor(f.get("valor") or servico["valor_total"])
            parcelas = max(1, int(f.get("parcelas") or servico["parcelas"]))
        except ValueError:
            flash("Confira o valor e o número de parcelas.", "erro")
            return redirect(request.url)
        servicos.preparar_proposta(g.escritorio, c, servico, f.get("frase", ""), valor, parcelas)
        flash("Proposta preparada. Ela está esperando o seu \"sim\" em Aprovações.", "ok")
        return redirect(url_for("painel.cliente", cliente_id=c["id"]))
    return render_template("painel/proposta_nova.html", c=c, tabela=tabela)


@painel.route("/propostas/<int:proposta_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_proposta(proposta_id):
    p = meu("proposta", proposta_id)
    c = meu("cliente", p["cliente_id"])
    if request.method == "POST":
        executar("UPDATE proposta SET texto = ?, status = 'aguardando aprovação' WHERE id = ?",
                 request.form.get("texto", p["texto"]), p["id"])
        servicos.registrar(esc_id(), "Advogado(a)", "Proposta revisada pelo advogado", "", c["id"])
        servicos.criar_pendencia(esc_id(), "proposta", p["id"], "Proposta revisada pronta",
                                 f"Versão revisada para {c['nome']}.", c["id"])
        flash("Revisão salva. Aprove em Aprovações quando quiser enviar.", "ok")
        return redirect(url_for("painel.aprovacoes"))
    return render_template("painel/editar_texto.html", titulo=f"Revisar proposta – {c['nome']}", texto=p["texto"],
                           voltar=url_for("painel.cliente", cliente_id=c["id"]))


@painel.route("/contratos/<int:contrato_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_contrato(contrato_id):
    k = meu("contrato", contrato_id)
    c = meu("cliente", k["cliente_id"])
    if request.method == "POST":
        executar("UPDATE contrato SET texto = ?, status = 'aguardando aprovação' WHERE id = ?",
                 request.form.get("texto", k["texto"]), k["id"])
        servicos.registrar(esc_id(), "Advogado(a)", "Contrato revisado pelo advogado", "", c["id"])
        servicos.criar_pendencia(esc_id(), "contrato", k["id"], "Contrato revisado pronto",
                                 f"Versão revisada para {c['nome']}.", c["id"])
        flash("Revisão salva. Aprove em Aprovações quando quiser enviar.", "ok")
        return redirect(url_for("painel.aprovacoes"))
    return render_template("painel/editar_texto.html", titulo=f"Revisar contrato – {c['nome']}", texto=k["texto"],
                           voltar=url_for("painel.cliente", cliente_id=c["id"]))


@painel.route("/andamentos/<int:andamento_id>/mensagem", methods=["GET", "POST"])
@login_obrigatorio
def editar_mensagem(andamento_id):
    a = um("SELECT a.*, p.escritorio_id, p.cliente_id FROM andamento a JOIN processo p ON p.id = a.processo_id"
           " WHERE a.id = ? AND p.escritorio_id = ?", andamento_id, esc_id())
    if a is None:
        abort(404)
    c = meu("cliente", a["cliente_id"])
    if request.method == "POST":
        executar("UPDATE andamento SET mensagem_cliente = ? WHERE id = ?", request.form.get("texto", ""), a["id"])
        servicos.criar_pendencia(esc_id(), "mensagem", a["id"], "Aviso ao cliente revisado",
                                 f"Versão revisada para {c['nome']}: \"{request.form.get('texto', '')}\"", c["id"])
        flash("Revisão salva. Aprove em Aprovações para enviar.", "ok")
        return redirect(url_for("painel.aprovacoes"))
    return render_template("painel/editar_texto.html", titulo=f"Revisar aviso – {c['nome']}",
                           texto=a["mensagem_cliente"], voltar=url_for("painel.aprovacoes"), curto=True)


# ---------------------------------------------------------------- agenda

@painel.route("/agenda", methods=["GET", "POST"])
@login_obrigatorio
def agenda():
    if request.method == "POST":
        f = request.form
        inicio = f"{f.get('data')} {f.get('hora') or '09:00'}:00"
        try:
            regras.ler_data(inicio)
        except ValueError:
            flash("Confira a data e a hora.", "erro")
            return redirect(url_for("painel.agenda"))
        cid = int(f["cliente_id"]) if f.get("cliente_id") else None
        if cid:
            meu("cliente", cid)
        executar("INSERT INTO compromisso (escritorio_id, cliente_id, tipo, titulo, inicio, confirmado, observacao)"
                 " VALUES (?, ?, ?, ?, ?, 1, ?)", esc_id(), cid, f.get("tipo", "compromisso"),
                 f.get("titulo") or f.get("tipo", "Compromisso").capitalize(), inicio, f.get("observacao", ""))
        servicos.registrar(esc_id(), "Advogado(a)", "Compromisso incluído na agenda",
                           f"{f.get('titulo')} – {regras.data_br(inicio)}", cid)
        flash("Compromisso incluído.", "ok")
        return redirect(url_for("painel.agenda"))
    itens = varios("SELECT k.*, c.nome AS cliente_nome FROM compromisso k LEFT JOIN cliente c ON c.id = k.cliente_id"
                   " WHERE k.escritorio_id = ? AND k.inicio >= ? ORDER BY k.inicio", esc_id(), regras.hoje().isoformat())
    dias = {}
    for k in itens:
        dias.setdefault(k["inicio"][:10], []).append(k)
    livres = regras.horarios_livres(g.escritorio["horarios"], g.escritorio["duracao_consulta"],
                                    servicos.horarios_ocupados(esc_id()), quantidade=5)
    clientes_lista = varios("SELECT id, nome FROM cliente WHERE escritorio_id = ? AND nome != '' ORDER BY nome", esc_id())
    return render_template("painel/agenda.html", dias=dias, livres=livres, clientes=clientes_lista,
                           horarios=regras.descrever_horarios(g.escritorio["horarios"]))


# ---------------------------------------------------------------- financeiro

@painel.route("/financeiro")
@login_obrigatorio
def financeiro():
    servicos.rotina_diaria(g.escritorio)
    filtro = request.args.get("status", "")
    sql = ("SELECT p.*, c.nome AS cliente_nome FROM parcela p JOIN cliente c ON c.id = p.cliente_id"
           " WHERE p.escritorio_id = ?")
    params = [esc_id()]
    if filtro:
        sql += " AND p.status = ?"
        params.append(filtro)
    parcelas = varios(sql + " ORDER BY p.vencimento", *params)
    totais = {s: um("SELECT COALESCE(SUM(valor),0) v, COUNT(*) n FROM parcela WHERE escritorio_id = ? AND status = ?",
                    esc_id(), s) for s in ["aguardando aprovação", "programada", "emitida", "atrasada", "paga"]}
    return render_template("painel/financeiro.html", parcelas=parcelas, totais=totais, filtro=filtro)


@painel.route("/parcelas/<int:parcela_id>/paga", methods=["POST"])
@login_obrigatorio
def marcar_paga(parcela_id):
    p = meu("parcela", parcela_id)
    if p["status"] in ("emitida", "atrasada"):
        servicos.pagar_parcela(p)
        flash("Pagamento registrado.", "ok")
    return redirect(request.referrer or url_for("painel.financeiro"))


# ---------------------------------------------------------------- processos

@painel.route("/processos", methods=["GET", "POST"])
@login_obrigatorio
def processos():
    if request.method == "POST":
        f = request.form
        c = meu("cliente", int(f.get("cliente_id") or 0))
        if not f.get("autorizado"):
            flash("Para acompanhar o processo, confirme que autoriza o acesso com a sua credencial.", "erro")
            return redirect(url_for("painel.processos"))
        pid = executar("INSERT INTO processo (escritorio_id, cliente_id, numero, tribunal, descricao, acesso_autorizado,"
                       " criado_em) VALUES (?, ?, ?, ?, ?, 1, ?)", esc_id(), c["id"], f.get("numero", "").strip(),
                       f.get("tribunal", "").strip(), f.get("descricao", ""), regras.agora_iso())
        servicos.registrar(esc_id(), "Advogado(a)", "Processo conectado para acompanhamento",
                           f"{f.get('numero')} – acesso autorizado pelo advogado, somente leitura.", c["id"])
        flash("Processo conectado. Novas publicações aparecem aqui e em Aprovações.", "ok")
        return redirect(url_for("painel.processo", processo_id=pid))
    lista = varios("SELECT p.*, c.nome AS cliente_nome, (SELECT COUNT(*) FROM andamento a WHERE a.processo_id = p.id) n"
                   " FROM processo p JOIN cliente c ON c.id = p.cliente_id WHERE p.escritorio_id = ? ORDER BY p.id DESC",
                   esc_id())
    clientes_lista = varios("SELECT id, nome FROM cliente WHERE escritorio_id = ? AND status = 'contratado' ORDER BY nome",
                            esc_id())
    return render_template("painel/processos.html", processos=lista, clientes=clientes_lista)


@painel.route("/processos/<int:processo_id>", methods=["GET", "POST"])
@login_obrigatorio
def processo(processo_id):
    p = meu("processo", processo_id)
    if request.method == "POST":
        texto = request.form.get("texto", "").strip()
        if texto:
            servicos.registrar_publicacao(g.escritorio, p, texto)
            flash("Publicação lida. O resumo está abaixo; a data e o aviso ao cliente esperam o seu \"sim\".", "ok")
        return redirect(url_for("painel.processo", processo_id=p["id"]))
    c = meu("cliente", p["cliente_id"])
    andamentos = varios("SELECT * FROM andamento WHERE processo_id = ? ORDER BY id DESC", p["id"])
    exemplo = (f"Intimação: fica designada audiência de conciliação para "
               f"{(regras.hoje() + timedelta(days=21)).strftime('%d/%m/%Y')}, às 14h, no Juizado Especial Cível. "
               "Intimem-se as partes.")
    return render_template("painel/processo.html", p=p, c=c, andamentos=andamentos, exemplo=exemplo)


# ---------------------------------------------------------------- registro de conduta

@painel.route("/registro")
@login_obrigatorio
def registro():
    linhas = varios("SELECT r.*, c.nome AS cliente_nome FROM registro r LEFT JOIN cliente c ON c.id = r.cliente_id"
                    " WHERE r.escritorio_id = ? ORDER BY r.id DESC LIMIT 300", esc_id())
    return render_template("painel/registro.html", linhas=linhas)


# ---------------------------------------------------------------- configurações

@painel.route("/configuracoes", methods=["GET", "POST"])
@login_obrigatorio
def configuracoes():
    e = g.escritorio
    if request.method == "POST":
        f = request.form
        executar("UPDATE escritorio SET nome = ?, advogado_nome = ?, oab = ?, telefone = ?, cidade = ?, uf = ?"
                 " WHERE id = ?", f.get("nome") or e["nome"], f.get("advogado") or e["advogado_nome"],
                 f.get("oab") or e["oab"], f.get("telefone", ""), f.get("cidade", ""), (f.get("uf") or "SP")[:2].upper(),
                 e["id"])
        _salvar_horarios(f)
        servicos.registrar(e["id"], "Advogado(a)", "Configurações atualizadas")
        flash("Configurações salvas.", "ok")
        return redirect(url_for("painel.configuracoes"))
    return render_template("painel/configuracoes.html", horarios=regras.ler_horarios(e["horarios"]),
                           dias=regras.DIAS_SEMANA)


@painel.route("/configuracoes/honorarios", methods=["GET", "POST"])
@login_obrigatorio
def honorarios():
    if request.method == "POST":
        f = request.form
        if f.get("acao") == "novo":
            try:
                valor = regras.ler_valor(f.get("valor") or "0")
            except ValueError:
                flash("Confira o valor.", "erro")
                return redirect(url_for("painel.honorarios"))
            executar("INSERT INTO servico (escritorio_id, nome, area, valor_total, parcelas, descricao)"
                     " VALUES (?, ?, ?, ?, ?, ?)", esc_id(), f.get("nome", "Novo serviço"), f.get("area", "Geral"),
                     valor, max(1, int(f.get("parcelas") or 1)), f.get("descricao", ""))
            flash("Serviço incluído na tabela.", "ok")
        else:
            _salvar_tabela(f)
            flash("Tabela de honorários salva.", "ok")
        servicos.registrar(esc_id(), "Advogado(a)", "Tabela de honorários atualizada")
        return redirect(url_for("painel.honorarios"))
    lista = varios("SELECT * FROM servico WHERE escritorio_id = ? ORDER BY area, nome", esc_id())
    return render_template("painel/honorarios.html", servicos=lista, areas=["Geral"] + list(regras.AREAS.keys()))


@painel.route("/configuracoes/modelos", methods=["GET", "POST"])
@login_obrigatorio
def modelos():
    if request.method == "POST":
        executar("UPDATE escritorio SET modelo_proposta = ?, modelo_contrato = ? WHERE id = ?",
                 request.form.get("modelo_proposta", ""), request.form.get("modelo_contrato", ""), esc_id())
        servicos.registrar(esc_id(), "Advogado(a)", "Modelos de proposta e contrato atualizados")
        flash("Modelos salvos.", "ok")
        return redirect(url_for("painel.modelos"))
    return render_template("painel/modelos.html")


@painel.route("/configuracoes/conflitos", methods=["GET", "POST"])
@login_obrigatorio
def conflitos():
    if request.method == "POST":
        f = request.form
        if f.get("acao") == "remover":
            parte = meu("parte", int(f.get("parte_id") or 0))
            executar("DELETE FROM parte WHERE id = ?", parte["id"])
            flash("Nome removido da lista.", "ok")
        elif f.get("nome", "").strip():
            executar("INSERT INTO parte (escritorio_id, nome, papel, observacao) VALUES (?, ?, ?, ?)",
                     esc_id(), f["nome"].strip(), f.get("papel", "cliente"), f.get("observacao", ""))
            flash("Nome incluído na lista de conflitos.", "ok")
        return redirect(url_for("painel.conflitos"))
    lista = varios("SELECT * FROM parte WHERE escritorio_id = ? ORDER BY papel, nome", esc_id())
    return render_template("painel/conflitos.html", partes=lista)
