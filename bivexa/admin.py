"""Administração da plataforma Bivexa (a equipe que mantém o produto).

A administradora não é advogada e não precisa de OAB. Ela entra com o e-mail
e a senha definidos nas variáveis de ambiente ADMIN_EMAIL e ADMIN_SENHA, vê
todos os escritórios cadastrados e pode abrir o painel de cada um.

Toda vez que a administradora abre o painel de um escritório, isso fica no
registro de conduta daquele escritório.
"""

import os
import secrets
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from . import servicos
from .banco import um, varios

admin = Blueprint("admin", __name__, url_prefix="/admin")


def credenciais():
    return os.environ.get("ADMIN_EMAIL", "").strip().lower(), os.environ.get("ADMIN_SENHA", "")


def admin_obrigatorio(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.entrar"))
        return funcao(*args, **kwargs)
    return protegida


@admin.route("/entrar", methods=["GET", "POST"])
def entrar():
    email_certo, senha_certa = credenciais()
    if not email_certo or not senha_certa:
        return render_template("admin/entrar.html", desligado=True)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        # compare_digest compara sem revelar, pelo tempo de resposta, onde a senha errou
        if secrets.compare_digest(email, email_certo) and secrets.compare_digest(senha, senha_certa):
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin.inicio"))
        flash("E-mail ou senha da administração incorretos.", "erro")
    return render_template("admin/entrar.html", desligado=False)


@admin.route("/")
@admin_obrigatorio
def inicio():
    def total(sql):
        return um(sql)["n"]

    numeros = {
        "escritorios": total("SELECT COUNT(*) n FROM escritorio"),
        "clientes": total("SELECT COUNT(*) n FROM cliente WHERE nome != ''"),
        "conversas": total("SELECT COUNT(DISTINCT cliente_id) n FROM mensagem"),
        "consultas": total("SELECT COUNT(*) n FROM compromisso WHERE tipo = 'consulta'"),
        "propostas": total("SELECT COUNT(*) n FROM proposta"),
        "contratos": total("SELECT COUNT(*) n FROM contrato WHERE status = 'assinado'"),
        "pendentes": total("SELECT COUNT(*) n FROM pendencia WHERE status = 'pendente'"),
        "bloqueios": total("SELECT COUNT(*) n FROM registro WHERE acao = 'Mensagem bloqueada antes do envio'"),
    }
    contratado = um("SELECT COALESCE(SUM(valor),0) v FROM parcela")["v"]
    recebido = um("SELECT COALESCE(SUM(valor),0) v FROM parcela WHERE status = 'paga'")["v"]
    escritorios = varios(
        "SELECT e.*,"
        " (SELECT COUNT(*) FROM cliente c WHERE c.escritorio_id = e.id AND c.nome != '') AS n_clientes,"
        " (SELECT COUNT(*) FROM pendencia p WHERE p.escritorio_id = e.id AND p.status = 'pendente') AS n_pendentes,"
        " (SELECT MAX(r.criado_em) FROM registro r WHERE r.escritorio_id = e.id) AS ultima_atividade"
        " FROM escritorio e ORDER BY e.id DESC")
    return render_template("admin/inicio.html", numeros=numeros, contratado=contratado, recebido=recebido,
                           escritorios=escritorios)


@admin.route("/escritorios/<int:escritorio_id>/abrir", methods=["POST"])
@admin_obrigatorio
def abrir_escritorio(escritorio_id):
    e = um("SELECT * FROM escritorio WHERE id = ?", escritorio_id)
    if e is None:
        abort(404)
    session["escritorio_id"] = e["id"]
    servicos.registrar(e["id"], "Administração Bivexa", "Painel aberto pela administração da plataforma")
    return redirect(url_for("painel.hoje"))


@admin.route("/voltar", methods=["POST"])
@admin_obrigatorio
def voltar():
    session.pop("escritorio_id", None)
    return redirect(url_for("admin.inicio"))
