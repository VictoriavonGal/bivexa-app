"""Testes automáticos da Bivexa: percorrem o caminho de um cliente inteiro,
do cadastro do escritório ao pagamento da primeira parcela.

Para rodar:  uv run pytest
"""

import re

import pytest

from bivexa import criar_app, regras
from bivexa.banco import um, varios


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)  # testa o plano de reserva
    return criar_app({"BANCO": str(tmp_path / "teste.db"), "TESTING": True, "SECRET_KEY": "teste"})


def token(cliente):
    cliente.get("/")
    with cliente.session_transaction() as s:
        return s["csrf"]


def post(cliente, url, **dados):
    dados["csrf"] = token(cliente)
    return cliente.post(url, data=dados, follow_redirects=True)


def criar_escritorio(app, email="ana@exemplo.com", nome="Lima Advocacia"):
    c = app.test_client()
    r = post(c, "/cadastro", nome=nome, advogado="Dra. Ana Lima", oab="SP 999.999", email=email,
             senha="senhaforte1", senha2="senhaforte1", cidade="São Paulo", uf="SP", aceite="on")
    assert "Primeiros passos" in r.get_data(as_text=True)
    post(c, "/painel/primeiros-passos?passo=1", telefone="11 3000-0000", cidade="São Paulo", uf="SP", areas="Família")
    post(c, "/painel/primeiros-passos?passo=2", dias=["0", "1", "2", "3", "4"], inicio="09:00", fim="18:00",
         almoco_inicio="12:00", almoco_fim="13:00", duracao="60", lembrete_dias="3", video="on")
    r = post(c, "/painel/primeiros-passos?passo=3")
    assert "Precisa de você" in r.get_data(as_text=True)  # chegou à tela Hoje
    with app.app_context():
        escritorio = um("SELECT * FROM escritorio WHERE email = ?", email)
    return c, escritorio


def conversar(app, slug, mensagens):
    visitante = app.test_client()
    for m in mensagens:
        r = post(visitante, f"/atendimento/{slug}", texto=m)
        assert r.status_code == 200
    return visitante, r.get_data(as_text=True)


def test_cadastro_rejeita_senha_curta(app):
    c = app.test_client()
    r = post(c, "/cadastro", nome="X", advogado="Y", oab="1", email="a@b.com", senha="123", senha2="123", aceite="on")
    assert "pelo menos 8 caracteres" in r.get_data(as_text=True)


def test_formulario_sem_token_e_recusado(app):
    c = app.test_client()
    assert c.post("/cadastro", data={"nome": "X"}).status_code == 400


def test_fluxo_completo_do_primeiro_contato_ao_pagamento(app):
    adv, e = criar_escritorio(app)

    # 1. Primeiro contato pelo link de atendimento
    visitante, html = conversar(app, e["slug"], [
        "Boa noite, quero pedir pensão alimentícia para minha filha. Tenho direito?",
        "mariana costa",
        "Rodrigo Costa",
        "(11) 90000-0001",
        "1",
    ])
    assert "Consulta confirmada" in html
    assert "não posso orientar" in html.lower() or "Não posso orientar" in html

    with app.app_context():
        cli = um("SELECT * FROM cliente WHERE escritorio_id = ? AND nome = 'Mariana Costa'", e["id"])
        assert cli["status"] == "consulta marcada"
        assert cli["area"] == "Família"
        assert um("SELECT COUNT(*) n FROM compromisso WHERE cliente_id = ?", cli["id"])["n"] == 1
        # Nenhuma mensagem enviada contém opinião jurídica
        for m in varios("SELECT texto FROM mensagem WHERE cliente_id = ? AND autor = 'bivexa'", cli["id"]):
            assert regras.verificar_mensagem(m["texto"])[0]

    # 2. Proposta: preparada, aprovada e enviada
    with app.app_context():
        servico = um("SELECT * FROM servico WHERE escritorio_id = ? AND nome = 'Ação de alimentos'", e["id"])
    post(adv, f"/painel/clientes/{cli['id']}/proposta", servico_id=str(servico["id"]),
         frase="alimentos para a filha, inicial e acompanhamento", valor="", parcelas="")
    with app.app_context():
        pend = um("SELECT * FROM pendencia WHERE tipo = 'proposta' AND status = 'pendente'")
        proposta = um("SELECT * FROM proposta WHERE cliente_id = ?", cli["id"])
        assert proposta["status"] == "aguardando aprovação"
    # Antes do "sim", o cliente não consegue abrir a proposta
    assert visitante.get(f"/proposta/{proposta['token']}").status_code == 404
    post(adv, f"/painel/aprovacoes/{pend['id']}/aprovar")

    # 3. Cliente aceita; contrato é aprovado; cliente assina
    post(visitante, f"/proposta/{proposta['token']}", ciente="on")
    with app.app_context():
        pend = um("SELECT * FROM pendencia WHERE tipo = 'contrato' AND status = 'pendente'")
        contrato = um("SELECT * FROM contrato WHERE cliente_id = ?", cli["id"])
    post(adv, f"/painel/aprovacoes/{pend['id']}/aprovar")
    post(visitante, f"/contrato/{contrato['token']}", assinatura="Mariana Costa", ciente="on")

    # 4. Primeira cobrança passa pelo advogado; cliente paga
    with app.app_context():
        assert um("SELECT status FROM cliente WHERE id = ?", cli["id"])["status"] == "contratado"
        parcelas = varios("SELECT * FROM parcela WHERE cliente_id = ? ORDER BY numero", cli["id"])
        assert [p["status"] for p in parcelas] == ["aguardando aprovação", "programada", "programada"]
        pend = um("SELECT * FROM pendencia WHERE tipo = 'cobranca' AND status = 'pendente'")
    post(adv, f"/painel/aprovacoes/{pend['id']}/aprovar")
    with app.app_context():
        primeira = um("SELECT * FROM parcela WHERE id = ?", parcelas[0]["id"])
        assert primeira["status"] == "emitida" and primeira["codigo_pagamento"].startswith("DEMO-PIX")
    post(visitante, f"/pagamento/{primeira['token']}")
    with app.app_context():
        assert um("SELECT status FROM parcela WHERE id = ?", primeira["id"])["status"] == "paga"
        # Contratante e parte contrária entram na lista de conflitos
        nomes = {p["nome"] for p in varios("SELECT nome FROM parte WHERE escritorio_id = ?", e["id"])}
        assert {"Mariana Costa", "Rodrigo Costa"} <= nomes
        # Tudo ficou no registro de conduta
        acoes = {r["acao"] for r in varios("SELECT acao FROM registro WHERE cliente_id = ?", cli["id"])}
        assert {"Triagem do primeiro contato", "Conferência de conflito de interesses", "Consulta marcada",
                "Proposta enviada ao cliente", "Contrato assinado eletronicamente", "Pagamento recebido"} <= acoes

    # 5. Processo: publicação lida, data e aviso esperam o "sim"
    r = post(adv, "/painel/processos", cliente_id=str(cli["id"]), numero="1000001-11.2026.8.26.0100",
             tribunal="TJSP – 2ª Vara de Família", descricao="Alimentos", autorizado="on")
    pid = int(re.search(r"/painel/processos/(\d+)", r.request.path).group(1))
    post(adv, f"/painel/processos/{pid}", texto="Fica designada audiência de conciliação para 20/12/2026, às 14h. Intimem-se.")
    with app.app_context():
        agenda = um("SELECT * FROM pendencia WHERE tipo = 'agenda' AND status = 'pendente'")
        aviso = um("SELECT * FROM pendencia WHERE tipo = 'mensagem' AND status = 'pendente'")
        assert agenda and aviso
    post(adv, f"/painel/aprovacoes/{agenda['id']}/aprovar")
    post(adv, f"/painel/aprovacoes/{aviso['id']}/aprovar")
    with app.app_context():
        aud = um("SELECT * FROM compromisso WHERE tipo = 'audiência'")
        assert aud["inicio"] == "2026-12-20 14:00:00"


def test_urgencia_e_conflito(app):
    adv, e = criar_escritorio(app)
    post(adv, "/painel/configuracoes/conflitos", nome="Transportes Ipê", papel="cliente")
    _, html = conversar(app, e["slug"], [
        "Fui demitido na sexta e a empresa quer que eu assine um acordo amanhã às 9h.",
        "João Pereira",
        "Transportes Ipê",
    ])
    assert "urgência" in html
    assert "preciso confirmar" in html
    with app.app_context():
        tipos = {p["tipo"]: p for p in varios("SELECT * FROM pendencia WHERE escritorio_id = ?", e["id"])}
        assert tipos["urgencia"]["urgente"] == 1
        assert "conflito" in tipos
        joao = um("SELECT * FROM cliente WHERE nome = 'João Pereira'")
        assert joao["etapa_conversa"] == "aguardando"


def test_mensagem_com_opiniao_juridica_e_bloqueada(app):
    adv, e = criar_escritorio(app)
    with app.app_context():
        from bivexa import servicos
        cli = servicos.iniciar_conversa(e)
        enviada = servicos.enviar_mensagem(cli, "Fique tranquilo, você tem direito e vai ganhar.")
        assert enviada is False
        assert um("SELECT COUNT(*) n FROM mensagem WHERE cliente_id = ?", cli["id"])["n"] == 0
        assert um("SELECT * FROM pendencia WHERE tipo = 'mensagem_bloqueada'") is not None


def test_atraso_vira_pendencia(app):
    adv, e = criar_escritorio(app)
    post(adv, "/painel/exemplos")  # o exemplo tem uma parcela vencida há 4 dias
    adv.get("/painel/")
    with app.app_context():
        assert um("SELECT COUNT(*) n FROM parcela WHERE escritorio_id = ? AND status = 'atrasada'", e["id"])["n"] == 1
        assert um("SELECT * FROM pendencia WHERE tipo = 'atraso' AND escritorio_id = ?", e["id"]) is not None
    adv.get("/painel/")  # rodar a rotina de novo não duplica
    with app.app_context():
        assert um("SELECT COUNT(*) n FROM pendencia WHERE tipo = 'atraso'")["n"] == 1


def test_um_escritorio_nao_ve_dados_do_outro(app):
    adv1, e1 = criar_escritorio(app, "um@exemplo.com", "Escritório Um")
    adv2, _ = criar_escritorio(app, "dois@exemplo.com", "Escritório Dois")
    conversar(app, e1["slug"], ["Quero me divorciar.", "Paula Reis"])
    with app.app_context():
        cli = um("SELECT * FROM cliente WHERE nome = 'Paula Reis'")
    assert adv1.get(f"/painel/clientes/{cli['id']}").status_code == 200
    assert adv2.get(f"/painel/clientes/{cli['id']}").status_code == 404


def test_todas_as_telas_abrem(app):
    adv, e = criar_escritorio(app)
    post(adv, "/painel/exemplos")
    for url in ["/painel/", "/painel/aprovacoes", "/painel/clientes", "/painel/captacao", "/painel/clientes/novo", "/painel/agenda",
                "/painel/financeiro", "/painel/processos", "/painel/registro", "/painel/configuracoes",
                "/painel/configuracoes/honorarios", "/painel/configuracoes/modelos", "/painel/configuracoes/conflitos",
                f"/atendimento/{e['slug']}"]:
        assert adv.get(url).status_code == 200, url


def test_prazo_em_dias_uteis():
    from datetime import date
    # sexta, 6/11/2026 + 5 dias úteis = sexta, 13/11/2026
    assert regras.somar_dias_uteis(date(2026, 11, 6), 5) == date(2026, 11, 13)


def test_administracao(app, monkeypatch):
    adv, e = criar_escritorio(app)
    gerente = app.test_client()
    # Sem as variáveis de ambiente, a administração fica desligada
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    assert "desligado" in gerente.get("/admin/entrar").get_data(as_text=True)
    monkeypatch.setenv("ADMIN_EMAIL", "gerente@bivexa.app")
    monkeypatch.setenv("ADMIN_SENHA", "senha-da-gerente")
    # Senha errada não entra; sem login, a visão geral redireciona
    assert "incorretos" in post(gerente, "/admin/entrar", email="gerente@bivexa.app", senha="x").get_data(as_text=True)
    assert gerente.get("/admin/").status_code == 302
    # Login certo: vê o escritório e abre o painel dele
    html = post(gerente, "/admin/entrar", email="gerente@bivexa.app", senha="senha-da-gerente").get_data(as_text=True)
    assert "Lima Advocacia" in html
    html = post(gerente, f"/admin/escritorios/{e['id']}/abrir").get_data(as_text=True)
    assert "administradora da Bivexa" in html
    with app.app_context():
        assert um("SELECT * FROM registro WHERE ator = 'Administração Bivexa'") is not None
    # Um advogado comum não acessa a administração
    assert adv.get("/admin/").status_code == 302


def test_agenda_em_calendario_e_clientes(app):
    adv, e = criar_escritorio(app)
    post(adv, "/painel/exemplos")
    for vista in ["mes", "semana", "dia"]:
        html = adv.get(f"/painel/agenda?vista={vista}").get_data(as_text=True)
        assert "Próximos compromissos" in html, vista
    # Data inválida não quebra a tela
    assert adv.get("/painel/agenda?vista=mes&data=xx").status_code == 200
    # A busca encontra pelo nome da parte contrária, sem acento
    html = adv.get("/painel/clientes?filtro=todos&q=claro").get_data(as_text=True)
    assert "Fernando Lima" in html and "Mariana Costa" not in html
    html = adv.get("/painel/captacao").get_data(as_text=True)
    assert "Contrato para assinar" in html and "Marcar consulta" in html


def test_aprovacao_mostra_a_mensagem(app):
    adv, e = criar_escritorio(app)
    post(adv, "/painel/exemplos")
    adv.get("/painel/")
    html = adv.get("/painel/aprovacoes").get_data(as_text=True)
    assert "Mensagem que será enviada" in html
    assert "ainda aparece em aberto" in html  # texto do aviso de atraso


def test_vagas_nao_colidem_com_compromisso():
    from datetime import date, datetime
    vagas = regras.vagas_do_dia("", 60, [datetime(2026, 11, 12, 14, 30)], date(2026, 11, 12))
    assert datetime(2026, 11, 12, 14, 0) not in vagas
    assert datetime(2026, 11, 12, 15, 0) in vagas
    assert regras.vagas_do_dia("", 60, [], date(2026, 11, 14)) == []  # sábado
