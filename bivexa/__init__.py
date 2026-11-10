"""Bivexa AI: a assistente administrativa do escritório de advocacia.

Este arquivo monta o app (função criar_app), cuida do cadastro, do login e
da proteção dos formulários.
"""

import os
import re
import secrets
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from markupsafe import Markup, escape
from werkzeug.security import check_password_hash, generate_password_hash

from . import banco, ia, regras, servicos

EMAIL_DEMO = "demo@bivexa.app"
SENHA_DEMO = "bivexa2026"


def criar_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        BANCO=os.environ.get("BIVEXA_BANCO", os.path.join(app.instance_path, "bivexa.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    app.teardown_appcontext(banco.fechar)
    with app.app_context():
        banco.criar_tabelas()

    _filtros(app)
    _seguranca(app)
    _rotas_de_conta(app)

    from .admin import admin
    from .painel import painel
    from .publico import publico
    app.register_blueprint(admin)
    app.register_blueprint(painel)
    app.register_blueprint(publico)
    return app


# ---------------------------------------------------------------- filtros de tela

LINK = re.compile(r"(/(?:proposta|contrato|pagamento)/[A-Za-z0-9_\-]+)")


def _filtros(app):
    app.jinja_env.filters["moeda"] = regras.moeda
    app.jinja_env.filters["data"] = regras.data_br
    app.jinja_env.filters["extenso"] = regras.data_extenso

    @app.template_filter("linkar")
    def linkar(texto):
        """Transforma os caminhos /proposta/..., /contrato/... em links clicáveis."""
        seguro = str(escape(texto))
        return Markup(LINK.sub(r'<a href="\1">abrir o link</a>', seguro))

    def csrf_campo():
        return Markup(f'<input type="hidden" name="csrf" value="{escape(session.get("csrf", ""))}">')

    def pendentes_count():
        if not g.get("escritorio"):
            return 0
        return banco.um("SELECT COUNT(*) n FROM pendencia WHERE escritorio_id = ? AND status = 'pendente'",
                        g.escritorio["id"])["n"]

    app.jinja_env.globals["csrf_campo"] = csrf_campo
    app.jinja_env.globals["pendentes_count"] = pendentes_count

    @app.context_processor
    def globais():
        return {"status_ia": ia.descricao_status(), "escritorio": g.get("escritorio"),
                "csrf": session.get("csrf", ""), "eh_admin": bool(session.get("admin"))}


# ---------------------------------------------------------------- segurança

def _seguranca(app):
    @app.before_request
    def preparar():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        g.escritorio = None
        if session.get("escritorio_id"):
            g.escritorio = banco.um("SELECT * FROM escritorio WHERE id = ?", session["escritorio_id"])
            if g.escritorio is None:
                session.pop("escritorio_id", None)
        if request.method == "POST" and not app.config.get("TESTING_SEM_CSRF"):
            if request.form.get("csrf") != session.get("csrf"):
                abort(400, "Formulário expirado. Volte e tente de novo.")

    @app.errorhandler(400)
    @app.errorhandler(404)
    def erro(e):
        return render_template("erro.html", erro=e), e.code


def login_obrigatorio(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if g.escritorio is None:
            return redirect(url_for("entrar", proximo=request.path))
        if not g.escritorio["configurado"] and request.endpoint not in ("painel.primeiros_passos",):
            return redirect(url_for("painel.primeiros_passos"))
        return funcao(*args, **kwargs)
    return protegida


# ---------------------------------------------------------------- conta

def _criar_conta(nome, advogado, oab, email, senha, cidade="São Paulo", uf="SP"):
    slug = regras.criar_slug(nome)
    base, n = slug, 2
    while banco.um("SELECT id FROM escritorio WHERE slug = ?", slug):
        slug, n = f"{base}-{n}", n + 1
    escritorio_id = banco.executar(
        "INSERT INTO escritorio (nome, slug, advogado_nome, oab, email, senha_hash, cidade, uf, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        nome, slug, advogado, oab, email, generate_password_hash(senha), cidade, uf, regras.agora_iso(),
    )
    servicos.preparar_escritorio_novo(escritorio_id)
    return escritorio_id


def _rotas_de_conta(app):
    @app.route("/")
    def inicio():
        if session.get("admin") and not g.escritorio:
            return redirect(url_for("admin.inicio"))
        if g.escritorio:
            return redirect(url_for("painel.hoje"))
        return render_template("inicio.html")

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        dados = request.form
        if request.method == "POST":
            erros = []
            email = dados.get("email", "").strip().lower()
            senha = dados.get("senha", "")
            for campo, rotulo in [("nome", "nome do escritório"), ("advogado", "seu nome"), ("oab", "número da OAB")]:
                if not dados.get(campo, "").strip():
                    erros.append(f"Preencha o {rotulo}.")
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                erros.append("Informe um e-mail válido.")
            elif banco.um("SELECT id FROM escritorio WHERE email = ?", email):
                erros.append("Já existe uma conta com este e-mail. Use \"Entrar\".")
            if len(senha) < 8:
                erros.append("A senha precisa ter pelo menos 8 caracteres.")
            if senha != dados.get("senha2", ""):
                erros.append("As duas senhas não são iguais.")
            if not dados.get("aceite"):
                erros.append("Confirme que leu como os dados são tratados.")
            if erros:
                for e in erros:
                    flash(e, "erro")
                return render_template("cadastro.html", dados=dados)
            escritorio_id = _criar_conta(dados["nome"].strip(), dados["advogado"].strip(),
                                         dados["oab"].strip().upper(), email, senha,
                                         dados.get("cidade", "").strip() or "São Paulo",
                                         dados.get("uf", "SP").strip().upper()[:2] or "SP")
            session.clear()
            session["escritorio_id"] = escritorio_id
            flash("Conta criada. Agora, três passos rápidos para configurar o seu escritório.", "ok")
            return redirect(url_for("painel.primeiros_passos"))
        return render_template("cadastro.html", dados={})

    @app.route("/entrar", methods=["GET", "POST"])
    def entrar():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            conta = banco.um("SELECT * FROM escritorio WHERE email = ?", email)
            if conta and check_password_hash(conta["senha_hash"], request.form.get("senha", "")):
                session.clear()
                session["escritorio_id"] = conta["id"]
                servicos.registrar(conta["id"], "Advogado(a)", "Entrada no painel")
                destino = request.args.get("proximo", "")
                return redirect(destino if destino.startswith("/") and not destino.startswith("//")
                                else url_for("painel.hoje"))
            flash("E-mail ou senha incorretos.", "erro")
        return render_template("entrar.html")

    @app.route("/demonstracao", methods=["POST"])
    def demonstracao():
        """Entra numa conta de demonstração já configurada, com exemplos."""
        conta = banco.um("SELECT * FROM escritorio WHERE email = ?", EMAIL_DEMO)
        if conta is None:
            eid = _criar_conta("Silva Advocacia", "Dra. Helena Silva", "SP 123.456",
                               EMAIL_DEMO, SENHA_DEMO)
            banco.executar("UPDATE escritorio SET configurado = 1, areas = ?, telefone = ? WHERE id = ?",
                           "Família, Trabalhista, Consumidor", "(11) 3000-0000", eid)
            conta = banco.um("SELECT * FROM escritorio WHERE id = ?", eid)
            servicos.carregar_exemplos(conta)
        session.clear()
        session["escritorio_id"] = conta["id"]
        flash("Bem-vindo à demonstração: um escritório fictício, com clientes e casos inventados.", "ok")
        return redirect(url_for("painel.hoje"))

    @app.route("/sair", methods=["POST"])
    def sair():
        session.clear()
        flash("Você saiu da sua conta.", "ok")
        return redirect(url_for("inicio"))

    @app.route("/privacidade")
    def privacidade():
        return render_template("privacidade.html")
