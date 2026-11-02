"""Páginas que o CLIENTE do escritório vê (sem login).

No produto real, a conversa aconteceria pelo WhatsApp do escritório. Nesta
versão de demonstração, a página /atendimento/<escritório> faz esse papel.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from . import servicos
from .banco import um, varios

publico = Blueprint("publico", __name__)


def escritorio_por_slug(slug):
    e = um("SELECT * FROM escritorio WHERE slug = ? AND configurado = 1", slug)
    if e is None:
        abort(404)
    return e


@publico.route("/atendimento/<slug>", methods=["GET", "POST"])
def atendimento(slug):
    e = escritorio_por_slug(slug)
    chave = f"conversa_{e['id']}"
    cliente = None
    if session.get(chave):
        cliente = um("SELECT * FROM cliente WHERE token = ? AND escritorio_id = ?", session[chave], e["id"])

    if request.method == "POST":
        if request.form.get("acao") == "recomecar":
            session.pop(chave, None)
            return redirect(url_for("publico.atendimento", slug=slug))
        texto = request.form.get("texto", "")[:2000]
        if texto.strip():
            if cliente is None:
                cliente = servicos.iniciar_conversa(e)
                session[chave] = cliente["token"]
            servicos.processar_mensagem(e, cliente, texto)
        return redirect(url_for("publico.atendimento", slug=slug) + "#fim")

    mensagens = varios("SELECT * FROM mensagem WHERE cliente_id = ? ORDER BY id", cliente["id"]) if cliente else []
    return render_template("publico/atendimento.html", e=e, mensagens=mensagens, cliente=cliente)


@publico.route("/conversa/<token>")
def conversa(token):
    """Reabre a conversa de um cliente (link que o escritório pode reenviar)."""
    cliente = um("SELECT * FROM cliente WHERE token = ?", token)
    if cliente is None:
        abort(404)
    e = um("SELECT * FROM escritorio WHERE id = ?", cliente["escritorio_id"])
    session[f"conversa_{e['id']}"] = cliente["token"]
    return redirect(url_for("publico.atendimento", slug=e["slug"]) + "#fim")


@publico.route("/proposta/<token>", methods=["GET", "POST"])
def proposta(token):
    p = um("SELECT * FROM proposta WHERE token = ?", token)
    if p is None or p["status"] not in ("enviada", "aceita"):
        abort(404)
    e = um("SELECT * FROM escritorio WHERE id = ?", p["escritorio_id"])
    c = um("SELECT * FROM cliente WHERE id = ?", p["cliente_id"])
    if request.method == "POST" and p["status"] == "enviada":
        if not request.form.get("ciente"):
            flash("Marque que leu a proposta para aceitá-la.", "erro")
            return redirect(request.url)
        servicos.aceitar_proposta(p)
        flash("Proposta aceita. O contrato será enviado em seguida, depois da conferência do escritório.", "ok")
        return redirect(request.url)
    return render_template("publico/documento.html", tipo="proposta", doc=p, e=e, c=c)


@publico.route("/contrato/<token>", methods=["GET", "POST"])
def contrato(token):
    k = um("SELECT * FROM contrato WHERE token = ?", token)
    if k is None or k["status"] not in ("enviado para assinatura", "assinado"):
        abort(404)
    e = um("SELECT * FROM escritorio WHERE id = ?", k["escritorio_id"])
    c = um("SELECT * FROM cliente WHERE id = ?", k["cliente_id"])
    if request.method == "POST" and k["status"] == "enviado para assinatura":
        nome = request.form.get("assinatura", "").strip()
        if not request.form.get("ciente") or len(nome) < 5:
            flash("Digite o seu nome completo e marque que leu o contrato.", "erro")
            return redirect(request.url)
        servicos.assinar_contrato(k, nome)
        flash("Contrato assinado. Você receberá a cobrança da primeira parcela por aqui.", "ok")
        return redirect(request.url)
    return render_template("publico/documento.html", tipo="contrato", doc=k, e=e, c=c)


@publico.route("/pagamento/<token>", methods=["GET", "POST"])
def pagamento(token):
    p = um("SELECT * FROM parcela WHERE token = ?", token)
    if p is None or p["status"] not in ("emitida", "atrasada", "paga"):
        abort(404)
    e = um("SELECT * FROM escritorio WHERE id = ?", p["escritorio_id"])
    c = um("SELECT * FROM cliente WHERE id = ?", p["cliente_id"])
    if request.method == "POST" and p["status"] in ("emitida", "atrasada"):
        servicos.pagar_parcela(p)
        flash("Pagamento registrado (simulação).", "ok")
        return redirect(request.url)
    return render_template("publico/pagamento.html", p=p, e=e, c=c)
