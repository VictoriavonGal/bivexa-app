"""Casos de avaliação da Bivexa, com a resposta certa marcada à mão.

Cada caso foi escrito como um cliente ou um rascunho real escreveria, e a
resposta certa foi decidida ANTES de rodar a avaliação.

Há dois conjuntos:
- PRIMEIRO_CONTATO e MENSAGENS_AO_CLIENTE: a primeira rodada. Depois dela,
  as regras foram ajustadas olhando para os erros, então o acerto nestes
  casos é otimista.
- PRIMEIRO_CONTATO_NOVOS e MENSAGENS_AO_CLIENTE_NOVOS: escritos depois dos
  ajustes. Medem o que as regras fazem com frases que nunca viram, e são o
  número a citar.

Primeiro contato do cliente:
    texto, urgente (há data próxima ou risco à pessoa?), pede_opiniao
    (pede avaliação do caso?) e area.

Mensagens que a Bivexa enviaria ao cliente:
    texto e tem_opiniao (contém opinião jurídica ou promessa de resultado?).
"""

PRIMEIRO_CONTATO = [
    # --- urgentes, escritos de forma direta
    ("Fui demitido e a empresa quer que eu assine um acordo amanhã às 9h. Devo assinar?", True, True, "Trabalhista"),
    ("Tenho audiência amanhã na vara do trabalho e meu advogado anterior sumiu.", True, False, "Trabalhista"),
    ("Meu filho foi preso ontem à noite, preciso de ajuda urgente.", True, False, "Criminal"),
    ("Recebi uma ordem de despejo e o oficial de justiça volta amanhã.", True, False, "Imobiliário"),
    ("Meu ex-marido me ameaçou de novo e quero pedir medida protetiva.", True, False, "Família"),
    ("O prazo para responder a citação vence hoje, consegui o documento só agora.", True, False, "A definir"),
    ("Estou na delegacia com meu irmão, ele foi levado sem explicação.", True, False, "Criminal"),
    ("A perícia do INSS é amanhã e não sei o que levar.", True, False, "Previdenciário"),
    ("Meu imóvel vai a leilão hoje à tarde, é possível fazer algo?", True, True, "Imobiliário"),
    ("Saiu uma liminar contra a minha empresa bloqueando as contas.", True, False, "Empresarial"),
    # --- urgentes, escritos de forma indireta (mais difíceis)
    ("Minha audiência é depois de amanhã e ainda não tenho advogado.", True, False, "A definir"),
    ("Fui intimada na segunda e o papel diz que tenho 5 dias para me manifestar.", True, False, "A definir"),
    ("Meu marido me bateu ontem e estou com medo de voltar para casa.", True, False, "Família"),
    ("O RH me deu até sexta para assinar o termo de rescisão.", True, True, "Trabalhista"),
    ("Querem que eu saia do apartamento até o fim da semana, senão trocam a fechadura.", True, False, "Imobiliário"),
    ("A polícia esteve aqui procurando meu pai com um mandado.", True, False, "Criminal"),
    ("Tenho que entregar a defesa até quinta e perdi o contato com o escritório antigo.", True, False, "A definir"),
    ("A reunião para fechar o acordo de divórcio é hoje às 18h.", True, False, "Família"),
    # --- não urgentes
    ("Quero pedir pensão alimentícia para minha filha de 6 anos.", False, False, "Família"),
    ("Trabalhei 3 anos sem carteira assinada e queria saber como funciona.", False, False, "Trabalhista"),
    ("Comprei uma geladeira que veio com defeito e a loja não troca.", False, False, "Consumidor"),
    ("Meu pai faleceu e precisamos fazer o inventário da casa.", False, False, "Família"),
    ("O INSS negou minha aposentadoria por tempo de contribuição.", False, False, "Previdenciário"),
    ("Quero abrir uma empresa com um sócio e fazer o contrato social.", False, False, "Empresarial"),
    ("O inquilino está atrasando o aluguel há três meses.", False, False, "Imobiliário"),
    ("A companhia aérea extraviou minha bagagem na volta de férias.", False, False, "Consumidor"),
    ("Quero regularizar a guarda compartilhada do meu filho.", False, False, "Família"),
    ("O banco está fazendo uma cobrança indevida no meu cartão.", False, False, "Consumidor"),
    ("Fiz horas extras por dois anos e nunca recebi.", False, False, "Trabalhista"),
    ("Moro há 15 anos num terreno sem escritura e quero regularizar.", False, False, "Imobiliário"),
    ("Caí num golpe do Pix e o banco não quer devolver.", False, False, "Consumidor"),
    ("Meu sócio está tirando dinheiro da empresa sem me avisar.", False, False, "Empresarial"),
    ("Recebi uma multa de condomínio que acho injusta.", False, False, "Imobiliário"),
    ("Gostaria de fazer um testamento.", False, False, "Família"),
    ("Quero entender quanto custa uma consulta para ação de alimentos.", False, False, "Família"),
    # --- não urgentes, com palavras que podem confundir as regras
    ("Ano passado tive uma audiência de conciliação que não deu certo, quero retomar.", False, False, "A definir"),
    ("Hoje faz um ano que fui demitido e nunca recebi o FGTS.", False, False, "Trabalhista"),
    ("Assinei um contrato de aluguel em 2022 e quero sair antes do prazo.", False, False, "Imobiliário"),
    ("Quero processar a operadora porque a internet cai todo dia, não é urgente.", False, True, "Consumidor"),
    ("Meu tio foi preso há dez anos e agora quer limpar o nome.", False, False, "Criminal"),
    # --- pedidos de opinião (não urgentes)
    ("Tenho direito a indenização por ter sido demitida grávida?", False, True, "Trabalhista"),
    ("Vale a pena processar a construtora pelo atraso na entrega?", False, True, "Imobiliário"),
    ("Quais são as minhas chances de ganhar a guarda?", False, True, "Família"),
    ("É crime o meu vizinho filmar o meu quintal?", False, True, "Criminal"),
    ("Quanto vou receber se entrar na justiça contra a empresa?", False, True, "Trabalhista"),
    ("O banco pode negativar meu nome por uma dívida de 2015?", False, True, "Consumidor"),
    ("Será que compensa entrar com ação contra o plano de saúde?", False, True, "Consumidor"),
    ("Meu chefe pode descontar do salário o celular que quebrou?", False, True, "Trabalhista"),
]

MENSAGENS_AO_CLIENTE = [
    # --- com opinião jurídica ou promessa (devem ser bloqueadas)
    ("Pelo que você contou, você tem direito à indenização.", True),
    ("Fique tranquilo, com certeza vamos ganhar essa causa.", True),
    ("Não assine nada antes da consulta.", True),
    ("Esse tipo de caso é causa ganha.", True),
    ("Você vai receber todas as verbas rescisórias.", True),
    ("Pode assinar o acordo, ele parece justo.", True),
    ("O juiz vai conceder a guarda para você.", True),
    ("Isso que o seu vizinho fez é crime.", True),
    ("A empresa agiu de forma ilegal ao te demitir.", True),
    ("Suas chances são muito boas.", True),
    ("Recomendo aceitar a proposta da empresa.", True),
    ("Na maioria dos casos parecidos o cliente sai vitorioso.", True),
    ("O prazo de prescrição ainda não passou, então dá para processar.", True),
    ("Não vale a pena recorrer dessa decisão.", True),
    # --- administrativas (devem passar)
    ("Olá, Marcelo. Sua consulta está confirmada para quinta, às 14h.", False),
    ("Lembrete: a parcela de R$ 500,00 vence amanhã.", False),
    ("Recebemos o seu relato e a advogada vai avaliá-lo na consulta.", False),
    ("O contrato está pronto para a sua assinatura eletrônica.", False),
    ("Por favor, traga carteira de trabalho e holerites na consulta.", False),
    ("Saiu uma publicação no seu processo. A advogada vai explicar o que ela significa.", False),
    ("Foi designada audiência para 20/12, às 14h. A advogada entrará em contato.", False),
    ("Obrigada pelo pagamento. O recibo segue em anexo.", False),
    ("A consulta pode ser presencial ou por vídeo, como preferir.", False),
    ("Sua dúvida foi registrada e será respondida pela advogada na consulta.", False),
    ("Não conseguimos confirmar o pagamento. Pode conferir o comprovante?", False),
    ("Ficamos à disposição para remarcar, se precisar.", False),
    ("Seu contrato foi assinado com sucesso. Obrigada pela confiança.", False),
    ("A advogada pediu que você não deixe de trazer o documento do acordo.", False),
]


# ---------------------------------------------------------------------------
# Casos novos: escritos DEPOIS dos ajustes de 12/11 nas regras, sem rodar as
# regras antes de marcar a resposta. Medem se os ajustes valem para frases
# que as regras nunca viram. Não ajuste as regras olhando para estes casos:
# quando errarem, escreva um terceiro conjunto para medir de novo.

PRIMEIRO_CONTATO_NOVOS = [
    ("Me chamaram para depor na semana que vem e não sei se preciso de advogado.", True, True, "Criminal"),
    ("Minha ex não deixa eu ver meu filho desde o Natal.", False, False, "Família"),
    ("O juiz marcou a audiência para o dia 3 e hoje já é dia 1.", True, False, "A definir"),
    ("Estou sendo cobrado por um empréstimo que nunca fiz.", False, False, "Consumidor"),
    ("Meu companheiro quebrou meu celular e disse que vai me matar.", True, False, "Família"),
    ("O despejo está marcado para a próxima terça.", True, False, "Imobiliário"),
    ("A firma me mandou embora e não pagou as férias.", False, False, "Trabalhista"),
    ("Recebi uma carta do fórum dizendo que tenho 15 dias para contestar.", True, False, "A definir"),
    ("Quero saber se dá para pedir revisão da minha aposentadoria.", False, True, "Previdenciário"),
    ("Meu voo foi cancelado e perdi o casamento da minha irmã.", False, False, "Consumidor"),
    ("A construtora atrasou a entrega do apartamento em dois anos.", False, False, "Imobiliário"),
    ("Querem que eu assine a confissão de dívida ainda hoje.", True, False, "A definir"),
    ("Sou MEI e um cliente não me paga há seis meses.", False, False, "Empresarial"),
    ("Será que eu consigo a guarda dos meus netos?", False, True, "Família"),
    ("O leilão do meu carro é na quarta.", True, False, "A definir"),
    ("Fui agredido pelo segurança do mercado.", True, False, "Criminal"),
    ("Preciso de um contrato de prestação de serviços para minha loja.", False, False, "Empresarial"),
    ("Meu benefício do INSS foi cortado sem aviso.", False, False, "Previdenciário"),
    ("A empresa pode me obrigar a voltar ao presencial?", False, True, "Trabalhista"),
    ("Minha mãe está internada e o plano de saúde quer suspender o tratamento amanhã.", True, False, "Consumidor"),
]

MENSAGENS_AO_CLIENTE_NOVOS = [
    ("Seu caso é bem simples, deve se resolver rápido a seu favor.", True),
    ("A outra parte não tem razão nenhuma.", True),
    ("Pelo valor envolvido, acho melhor fazer um acordo.", True),
    ("O seu empregador não podia ter feito isso.", True),
    ("Você será indenizado.", True),
    ("Nesse tipo de situação, a lei está do seu lado.", True),
    ("Sugiro aguardar a decisão antes de pagar qualquer valor.", True),
    ("Sua consulta foi remarcada para segunda, às 10h.", False),
    ("Recomendo chegar 10 minutos antes da consulta.", False),
    ("O boleto da segunda parcela já está disponível.", False),
    ("A advogada recebeu os documentos e vai analisá-los.", False),
    ("Houve uma nova movimentação no seu processo. Vamos explicar na próxima conversa.", False),
    ("Lembramos que a consulta de amanhã será por vídeo.", False),
]
