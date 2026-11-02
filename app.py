"""Ponto de entrada da Bivexa AI.

Para rodar no seu computador:  uv run python app.py
Depois, abra http://127.0.0.1:5000 no navegador.
"""

import os

from bivexa import criar_app

app = criar_app()

if __name__ == "__main__":
    # No seu computador, a administração já vem ligada com este login.
    # No Render, defina ADMIN_EMAIL e ADMIN_SENHA no painel (ver o README).
    os.environ.setdefault("ADMIN_EMAIL", "admin@bivexa.app")
    os.environ.setdefault("ADMIN_SENHA", "admin-bivexa-2026")
    print("\n  Bivexa AI rodando em http://127.0.0.1:5000")
    print(f"  Administração: http://127.0.0.1:5000/admin/entrar  "
          f"(e-mail {os.environ['ADMIN_EMAIL']}, senha {os.environ['ADMIN_SENHA']})\n")
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
