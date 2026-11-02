"""Ponto de entrada da Bivexa AI.

Para rodar no seu computador:  uv run python app.py
Depois, abra http://127.0.0.1:5000 no navegador.
"""

import os

from bivexa import criar_app

app = criar_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
