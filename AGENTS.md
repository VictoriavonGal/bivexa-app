# Instruções para assistentes de código (Claude Code, Codex e outros)

## O produto

Bivexa AI: assistente administrativa para o advogado autônomo e o escritório boutique. Atende o cliente novo, marca consultas, prepara proposta e contrato, cobra honorários e acompanha processos. O advogado aprova tudo o que sai em nome dele.

## Regras do grupo

- Responda e escreva comentários em **português do Brasil**.
- O código deve continuar legível para estudantes de Direito: funções curtas, nomes em português, um comentário explicando o "porquê" quando não for óbvio.
- Rode `uv run --group dev pytest` antes de cada commit. Nenhum commit com teste falhando.
- Mensagens de commit em português, no imperativo: "Inclui lembrete de consulta".

## Regras do produto (não quebrar)

1. **Nada sai em nome do advogado sem aprovação**, exceto confirmação de horário e lembretes. Novas mensagens ao cliente passam por `servicos.enviar_mensagem`, que confere a conduta e grava o registro.
2. **A Bivexa nunca dá opinião jurídica.** Qualquer texto novo destinado ao cliente precisa passar em `regras.verificar_mensagem`.
3. **Toda ação relevante vai para o registro de conduta** (`servicos.registrar`).
4. **Toda consulta ao banco filtra por `escritorio_id`.** Use a função `meu()` em `painel.py` para buscar itens do escritório logado.
5. **A IA é opcional.** Toda função de `ia.py` precisa ter plano de reserva com regras fixas.
6. **Não ajuste as regras olhando para os casos novos de `avaliacao/casos.py`.** Eles medem o que as regras fazem com frases que nunca viram. Se mudar uma regra, rode `uv run python -m avaliacao.avaliar` e registre a mudança no commit; para medir de novo, escreva casos novos.

## Como rodar

```bash
uv run python app.py              # app em http://127.0.0.1:5000
uv run --group dev pytest         # testes
uv run python -m avaliacao.avaliar  # quanto as regras acertam (grava avaliacao/RESULTADOS.md)
```
