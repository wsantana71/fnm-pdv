from flask import Flask, render_template, request, redirect, url_for, session, flash

from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

import requests

import barcode

from barcode.writer import ImageWriter
app = Flask(__name__)

app.secret_key = "fnm_producoes"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///banco.db"

db = SQLAlchemy(app)



# ================= USUARIOS =================

class Usuario(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario = db.Column(
        db.String(100)
    )

    senha = db.Column(
        db.String(100)
    )
class Produto(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    codigo = db.Column(
        db.String(100)
    )

    nome = db.Column(
        db.String(200)
    )

    preco = db.Column(
        db.Float
    )

    custo = db.Column(
        db.Float,
        default=0
    )

    estoque = db.Column(
        db.Integer
    )

    categoria = db.Column(
        db.String(100)
    )

    imagem = db.Column(
        db.String(500)
    )

    estoque_minimo = db.Column(
        db.Integer
    )
# ================= LOGIN =================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]

        senha = request.form["senha"]

        user = Usuario.query.filter_by(

            usuario=usuario,

            senha=senha

        ).first()

        if user:

            session["usuario"] = usuario

            return redirect("/")

        flash("Usuário ou senha inválidos")

    return render_template(
        "login.html"
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
# ================= VENDAS =================

class Venda(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    produto = db.Column(
        db.String(100)
    )

    quantidade = db.Column(
        db.Integer
    )

    valor = db.Column(
        db.Float
    )

    horario = db.Column(
        db.String(100)
    )

    pagamento = db.Column(
        db.String(50)
    )
# ================= CLIENTES =================

class Cliente(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(200)
    )

    telefone = db.Column(
        db.String(50)
    )

    cpf = db.Column(
        db.String(50)
    )

# ================= VARIAVEIS =================

total_caixa = 0

carrinho = {}

ultima_venda = []

# ================= DASHBOARD =================
@app.route("/")
def index():

    if "usuario" not in session:

        return redirect("/login")

    produtos = Produto.query.all()

    vendas = Venda.query.all()

    total_produtos = len(produtos)

    total_vendas = len(vendas)

    total = 0

    for venda in vendas:

        total = round(
    total + venda.valor,
    2
)

    ranking = {}

    for venda in vendas:

        if venda.produto not in ranking:

            ranking[venda.produto] = 0

        ranking[venda.produto] += venda.quantidade

    produto_top = "Nenhum"

    if ranking:

        produto_top = max(

            ranking,

            key=ranking.get

        )

    estoque_baixo = [

        produto for produto in produtos

        if produto.estoque <= produto.estoque_minimo

    ]

    vendas_semana = [

        0,0,0,0,0,0,0

    ]

    for venda in vendas:

        try:

            data = datetime.strptime(

                venda.horario,

                "%d/%m/%Y %H:%M"

            )

            dia = data.weekday()

            vendas_semana[dia] += venda.valor

        except:

            pass

    return render_template(

        "dashboard.html",

        total=total,

        total_produtos=total_produtos,

        total_vendas=total_vendas,

        produto_top=produto_top,

        estoque_baixo=estoque_baixo,

        vendas_semana=vendas_semana

    )

# ================= CAIXA =================

@app.route("/caixa")
def caixa():

    produtos = Produto.query.all()

    total_carrinho = 0

    for item in carrinho.values():

        total_carrinho += (
            item["preco"] *
            item["quantidade"]
        )

    return render_template(

        "caixa.html",

        produtos=produtos,

        carrinho=carrinho,

        total=total_caixa,

        total_carrinho=total_carrinho

    )

# ================= PRODUTOS =================

@app.route("/produtos")
def produtos():

    busca = request.args.get("busca")

    if busca:

        produtos = Produto.query.filter(
            Produto.nome.contains(busca) |
            Produto.codigo.contains(busca)
        ).all()

    else:

        produtos = Produto.query.all()

    return render_template(

        "produtos.html",

        produtos=produtos

    )

# ================= CADASTRAR =================

@app.route("/cadastrar", methods=["POST"])
def cadastrar():

    produto = Produto(

        codigo=request.form["codigo"],

        nome=request.form["nome"],

        custo=float(
            request.form["custo"]
        ),

        preco=float(
            request.form["preco"]
        ),

        estoque=int(
            request.form["estoque"]
        ),

        categoria=request.form.get(
            "categoria"
        ),

        imagem=request.form.get(
            "imagem"
        ),

        estoque_minimo=int(
            request.form.get(
                "estoque_minimo"
            ) or 0
        )

    )

    db.session.add(produto)

    db.session.commit()

    return redirect("/produtos")

# ================= EDITAR =================

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    produto = Produto.query.get(id)

    if request.method == "POST":

        produto.codigo = request.form.get(
            "codigo"
        )

        produto.nome = request.form.get(
            "nome"
        )

        produto.preco = float(
            request.form.get("preco")
        )

        produto.estoque = int(
            request.form.get("estoque")
        )

        produto.categoria = request.form.get(
            "categoria"
        )

        produto.estoque_minimo = int(
            request.form.get(
                "estoque_minimo"
            ) or 0
        )

        db.session.commit()

        return redirect("/produtos")

    return render_template(

        "editar.html",

        produto=produto

    )

# ================= EXCLUIR =================

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):

    produto = Produto.query.get(id)

    if produto:

        db.session.delete(produto)

        db.session.commit()

    return redirect("/produtos")

# ================= SCANNER =================

@app.route("/scanner", methods=["POST"])
def scanner():

    codigo = request.form.get("codigo")

    produto = Produto.query.filter_by(
        codigo=codigo
    ).first()

    if produto and produto.estoque > 0:

        if produto.id not in carrinho:

            carrinho[produto.id] = {

                "id": produto.id,

                "nome": produto.nome,

                "preco": produto.preco,

                "quantidade": 1

            }

        else:

            carrinho[produto.id][
                "quantidade"
            ] += 1

    return redirect("/caixa")

# ================= VENDER =================

@app.route("/vender/<int:id>", methods=["POST"])
def vender(id):

    produto = Produto.query.get(id)

    if produto and produto.estoque > 0:

        if id not in carrinho:

            carrinho[id] = {

                "id": produto.id,

                "nome": produto.nome,

                "preco": produto.preco,

                "quantidade": 1

            }

        else:

            carrinho[id][
                "quantidade"
            ] += 1

    return redirect("/caixa")

# ================= REMOVER =================

@app.route("/remover/<int:id>", methods=["POST"])
def remover(id):

    if id in carrinho:

        carrinho[id]["quantidade"] -= 1

        if carrinho[id]["quantidade"] <= 0:

            del carrinho[id]

    return redirect("/caixa")

# ================= FINALIZAR =================

@app.route("/finalizar", methods=["POST"])
def finalizar():

    pagamento = request.form.get(
        "pagamento"
    )

    global total_caixa
    global ultima_venda

    ultima_venda = []

    total_venda = 0

    for id, item in carrinho.items():

        produto = Produto.query.get(id)

        if produto:

            produto.estoque -= item[
                "quantidade"
            ]

            valor_total = (
                item["preco"] *
                item["quantidade"]
            )

            total_caixa += valor_total

            total_venda += valor_total

            venda = Venda(

                produto=item["nome"],

                quantidade=item[
                    "quantidade"
                ],

                valor=valor_total,

                horario=datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                ),

                pagamento=pagamento,


            )

            db.session.add(venda)

            ultima_venda.append({

                "produto": item["nome"],

                "quantidade": item[
                    "quantidade"
                ],

                "valor": valor_total

            })

    db.session.commit()

    carrinho.clear()

    return render_template(

        "cupom.html",

        venda=ultima_venda,

        total=total_venda,

        horario=datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        ),

        pagamento=pagamento

    )

# ================= RELATORIOS =================

@app.route("/relatorios")
def relatorios():

    vendas = Venda.query.all()

    filtro_pagamento = request.args.get(
        "pagamento"
    )

    data_inicial = request.args.get(
        "data_inicial"
    )

    data_final = request.args.get(
        "data_final"
    )

    if filtro_pagamento:

        vendas = [

            venda for venda in vendas

            if venda.pagamento ==
            filtro_pagamento

        ]

    if data_inicial and data_final:

        vendas_filtradas = []

        for venda in vendas:

            data_venda = venda.horario.split(
                " "
            )[0]

            dia, mes, ano = data_venda.split("/")

            data_formatada = (
                f"{ano}-{mes}-{dia}"
            )

            if (

                data_inicial
                <= data_formatada
                <= data_final

            ):

                vendas_filtradas.append(
                    venda
                )

        vendas = vendas_filtradas

    total_geral = 0

    total_pix = 0

    total_dinheiro = 0

    total_credito = 0

    total_debito = 0

    for venda in vendas:

        total_geral += venda.valor

        if venda.pagamento == "Pix":

            total_pix += venda.valor

        elif venda.pagamento == "Dinheiro":

            total_dinheiro += venda.valor

        elif venda.pagamento == "Crédito":

            total_credito += venda.valor

        elif venda.pagamento == "Débito":

            total_debito += venda.valor

    ranking = {}

    for venda in vendas:

        if venda.produto not in ranking:

            ranking[venda.produto] = 0

        ranking[venda.produto] += venda.quantidade

    ranking = sorted(

        ranking.items(),

        key=lambda x: x[1],

        reverse=True

    )

    return render_template(

        "relatorios.html",

        vendas=vendas,

        total_geral=total_geral,

        total_pix=total_pix,

        total_dinheiro=total_dinheiro,

        total_credito=total_credito,

        total_debito=total_debito,

        ranking=ranking

    )

# ================= API PRODUTO =================

@app.route("/buscar_produto/<codigo>")
def buscar_produto(codigo):

    try:

        headers = {

            "X-Cosmos-Token":
            "KHn6dQyS3Fl3GcgUlzvErQ"

        }

        url = (
            f"https://api.cosmos.bluesoft.com.br/gtins/{codigo}"
        )

        resposta = requests.get(

            url,

            headers=headers

        )

        dados = resposta.json()

        return {

            "descricao": dados.get(
                "description",
                ""
            ),

            "categoria": dados.get(
                "category",
                {}
            ).get(
                "description",
                ""
            ),

            "imagem": dados.get(
                "thumbnail",
                ""
            )

        }

    except Exception as erro:

        print(erro)

        return {

            "descricao": "",

            "categoria": "",

            "imagem": ""

        }
# ================= CLIENTES =================

@app.route("/clientes")
def clientes():

    busca = request.args.get(
        "busca"
    )

    if busca:

        clientes = Cliente.query.filter(

            Cliente.nome.contains(busca) |

            Cliente.telefone.contains(busca)

        ).all()

    else:

        clientes = Cliente.query.all()

    return render_template(

        "clientes.html",

        clientes=clientes

    )

# ================= CADASTRAR CLIENTE =================

@app.route(
    "/cadastrar_cliente",
    methods=["POST"]
)
def cadastrar_cliente():

    cliente = Cliente(

        nome=request.form.get("nome"),

        telefone=request.form.get(
            "telefone"
        ),

        cpf=request.form.get("cpf")

    )

    db.session.add(cliente)

    db.session.commit()

    return redirect("/clientes")
# ================= BANCO =================

with app.app_context():

    db.create_all()

    if not Usuario.query.filter_by(
        usuario="admin"
    ).first():

        admin = Usuario(

            usuario="admin",

            senha="123"
        )

        db.session.add(admin)

        db.session.commit()

# ================= START =================
# ================= ESTOQUE =================

@app.route("/estoque")
def estoque():

    busca = request.args.get(
        "busca"
    )

    if busca:

        produtos = Produto.query.filter(

            Produto.nome.contains(busca) |

            Produto.codigo.contains(busca)

        ).all()

    else:

        produtos = Produto.query.all()

    return render_template(

        "estoque.html",

        produtos=produtos

    )
# ================= ENTRADA ESTOQUE =================

@app.route(
    "/entrada_estoque/<int:id>",
    methods=["POST"]
)
def entrada_estoque(id):

    produto = Produto.query.get(id)

    quantidade = int(

        request.form.get(
            "quantidade"
        )

    )

    produto.estoque += quantidade

    db.session.commit()

    return redirect("/estoque")

# ================= SAIDA ESTOQUE =================

@app.route(
    "/saida_estoque/<int:id>",
    methods=["POST"]
)
def saida_estoque(id):

    produto = Produto.query.get(id)

    quantidade = int(

        request.form.get(
            "quantidade"
        )

    )

    if produto.estoque >= quantidade:

        produto.estoque -= quantidade

        db.session.commit()

    return redirect("/estoque")
# ================= ETIQUETAS =================

@app.route("/etiquetas")
def etiquetas():

    produtos = Produto.query.all()

    return render_template(

        "etiquetas.html",

        produtos=produtos

    )
# ================= ETIQUETAS SELECIONADAS =================

@app.route(
    "/imprimir_etiquetas",
    methods=["POST"]
)
def imprimir_etiquetas():

    selecionados = request.form.getlist(
        "produtos"
    )

    produtos = Produto.query.filter(

        Produto.id.in_(
            selecionados
        )

    ).all()

    return render_template(

        "imprimir_etiquetas.html",

        produtos=produtos

    )

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False

    )
