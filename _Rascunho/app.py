import os
import json
from datetime import datetime, date
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# 1) CONFIGURAÇÃO
# =========================
load_dotenv()

APP_USER = os.getenv("APP_USER", "consultor")
APP_PASS = os.getenv("APP_PASS", "troque_essa_senha")
SECRET_KEY = os.getenv("SECRET_KEY", "troque_esta_chave_em_producao")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Banco local (arquivo oftalmoprev.db na pasta do projeto)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///oftalmoprev.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

PASS_HASH = generate_password_hash(APP_PASS)

# =========================
# 2) PROTOCOLOS (SEU CONTEÚDO)
# =========================
PROTOCOLOS_MASTER = {
    "Miopia > -1.00": {"score": 3, "exames": ["Mapeamento de Retina – AO", "Retinografia Simples – AO"], "just": "Rastreio de fragilidade periférica e degenerações latentes.", "biblio": "AAO PPP Comprehensive Evaluation", "link": "https://www.aao.org/education/preferred-practice-pattern/comprehensive-adult-medical-eye-evaluation-ppp"},
    "Lesão em retina": {"score": 5, "exames": ["Mapeamento de Retina – AO", "OCT de Mácula – AO"], "just": "Monitoramento de integridade retiniana e camadas neurais.", "biblio": "CBO Diretrizes Retina", "link": "https://www.cbo.com.br/novo/medico/pdf/Diretrizes_CBO_AMB_CFM.pdf"},
    "Astigmatismo > -1.50": {"score": 2, "exames": ["Ceratoscopia / Topografia – AO", "Paquimetria de Córnea – AO"], "just": "Avaliação de curvatura e espessura para descarte de ectasias.", "biblio": "Global Consensus on Keratoconus", "link": "https://pubmed.ncbi.nlm.nih.gov/25901970/"},
    "Suspeita de ceratocone": {"score": 4, "exames": ["Ceratoscopia / Topografia – AO", "Paquimetria de Córnea – AO"], "just": "Investigação estrutural corneana baseada em padrões de curvatura.", "biblio": "AAO Corneal PPP", "link": "https://www.aao.org/education/preferred-practice-pattern/corneal-ectasia-ppp"},
    "Hipermetropia > +2.50": {"score": 2, "exames": ["Gonioscopia – AO"], "just": "Rastreio preventivo de ângulo estreito em hipermétropes.", "biblio": "AAO POAG PPP", "link": "https://www.aao.org/education/preferred-practice-pattern/primary-open-angle-glaucoma-ppp"},
    "Câmara anterior rasa": {"score": 4, "exames": ["Gonioscopia – AO"], "just": "Risco elevado de fechamento angular primário.", "biblio": "CBO Consenso Glaucoma", "link": "https://www.cbo.com.br/novo/medico/pdf/Diretrizes_CBO_AMB_CFM.pdf"},
    "PIO > 19mmHg": {"score": 5, "exames": ["Paquimetria – AO", "Campimetria – AO", "OCT de Nervo Óptico – AO"], "just": "Investigação de HT Ocular e risco OHTS.", "biblio": "OHTS Study / AAO POAG", "link": "https://www.aao.org/education/preferred-practice-pattern/primary-open-angle-glaucoma-ppp"},
    "Escavação > 0.5": {"score": 4, "exames": ["OCT de Nervo Óptico – AO", "Campimetria – AO"], "just": "Avaliação estrutural e funcional do nervo óptico.", "biblio": "AAO POAG PPP", "link": "https://www.aao.org/education/preferred-practice-pattern/primary-open-angle-glaucoma-ppp"},
    "Suspeita de glaucoma": {"score": 4, "exames": ["OCT de Nervo Óptico – AO", "Paquimetria – AO", "Campimetria – AO"], "just": "Rastreio multimodal para detecção precoce.", "biblio": "CBO / ICO Guidelines", "link": "https://www.cbo.com.br/novo/medico/pdf/Diretrizes_CBO_AMB_CFM.pdf"},
    "Glaucoma confirmado": {"score": 5, "exames": ["Curva Tensional Diária ou TSH – AO", "Campimetria – AO", "Gonioscopia – AO"], "just": "Monitoramento de progressão e estabilidade tensional.", "biblio": "SOE Guidelines", "link": "https://www.soe.org/guidelines/"},
    "Diabetes": {"score": 5, "exames": ["OCT de Mácula – AO", "Retinografia Colorida – AO"], "just": "Rastreio de retinopatia diabética (ETDRS).", "biblio": "AAO Diabetic Retinopathy", "link": "https://www.aao.org/education/preferred-practice-pattern/diabetic-retinopathy-ppp"},
    "Hipertensão": {"score": 3, "exames": ["Mapeamento de Retina – AO", "Retinografia Colorida – AO"], "just": "Avaliação de alterações microvasculares sistêmicas.", "biblio": "Diretrizes SBC/CBO", "link": "https://www.cbo.com.br/novo/medico/pdf/Diretrizes_CBO_AMB_CFM.pdf"},
    "Cirurgia ocular >1 ano": {"score": 2, "exames": ["Microscopia Especular – AO", "Mapeamento de Retina"], "just": "Monitoramento endotelial e integridade pós-cirúrgica.", "biblio": "AAO Corneal Endothelial", "link": "https://www.aao.org/education/preferred-practice-pattern/corneal-endothelial-ppp"},
    "Trauma ocular": {"score": 4, "exames": ["USG Ocular – AO", "Gonioscopia – AO", "Mapeamento de Retina"], "just": "Avaliação de danos estruturais e risco de recessão angular.", "biblio": "Ocular Trauma Score", "link": "https://pubmed.ncbi.nlm.nih.gov/12028607/"},
    "Suspeita de uveíte": {"score": 4, "exames": ["OCT de Mácula – AO", "USG Ocular – AO"], "just": "Pesquisa de focos inflamatórios e complicações maculares.", "biblio": "IUSG Guidelines", "link": "https://www.iusg.net/"},
    "Olho seco": {"score": 2, "exames": ["Teste de Shirmmer – AO", "Ceratoscopia – AO"], "just": "Avaliação de superfície ocular e filme lacrimal.", "biblio": "TFOS DEWS II", "link": "https://www.tfosdewsneureport.org/"}
}

EXAMES_GERAIS = [
    "OCT de Mácula – AO", "OCT de Nervo Óptico – AO", "Retinografia Colorida – AO", "Gonioscopia – AO",
    "Campimetria – AO", "Curva Tensional Diária ou TSH – AO", "USG Ocular – AO", "Mapeamento de Retina – AO",
    "Paquimetria de Córnea – AO", "Ceratoscopia / Topografia – AO", "Microscopia Especular de Córnea – AO",
    "Teste de Shirmmer – AO"
]

QUEIXAS_LISTA = [
    "Dificuldade visual para longe", "Visão embaçada / flutuação", "Fotofobia / Lacremejamento",
    "Pós-operatório oftalmológico", "Dificuldade visual para perto", "Dor ocular / pressão ocular",
    "Trauma ocular recente"
]

HISTORICO_LISTA = [
    "Uso de óculos ou lentes", "Glaucoma / hipertensão ocular", "Retinopatia / DMRI / uveíte",
    "Uso de corticoides / imunossupressores", "Acompanhamento periódico", "Doenças sistêmicas (DM, HAS)"
]

def calcular_idade(dn_str: str) -> int:
    dn = datetime.strptime(dn_str, "%Y-%m-%d").date()
    hoje = date.today()
    return hoje.year - dn.year - ((hoje.month, hoje.day) < (dn.month, dn.day))

# =========================
# 3) BANCO (MODELOS)
# =========================
class Paciente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    dn = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    telefone = db.Column(db.String(30))
    endereco = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Atendimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("paciente.id"), nullable=False)
    consultor = db.Column(db.String(80), nullable=False)

    queixas = db.Column(db.Text)      # json list
    historico = db.Column(db.Text)    # json list
    achados = db.Column(db.Text)      # json list

    score = db.Column(db.Integer, default=0)
    exames = db.Column(db.Text)       # json list
    justificativa = db.Column(db.Text)
    bibliografia = db.Column(db.Text) # json list

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paciente = db.relationship("Paciente", backref="atendimentos")

# =========================
# 4) LOGIN (ÚNICO)
# =========================
class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == APP_USER:
        return User(user_id)
    return None

# =========================
# 5) ROTAS
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")

        if u == APP_USER and check_password_hash(PASS_HASH, p):
            login_user(User(u))
            return redirect(url_for("menu"))

        flash("Usuário ou senha inválidos.")
        return render_template("login.html", title="Login")

    return render_template("login.html", title="Login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ MENU COM BUSCA (nome/telefone)
@app.route("/")
@login_required
def menu():
    q = request.args.get("q", "").strip()
    pacientes = None

    if q:
        like_nome = f"%{q.upper()}%"
        like_tel = f"%{q}%"
        pacientes = (Paciente.query
                     .filter((Paciente.nome.like(like_nome)) | (Paciente.telefone.like(like_tel)))
                     .order_by(Paciente.created_at.desc())
                     .limit(50)
                     .all())

    return render_template("menu.html", title="Menu", q=q, pacientes=pacientes)

@app.route("/paciente/novo", methods=["GET", "POST"])
@login_required
def novo_paciente():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip().upper()
        dn = request.form.get("dn", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()

        if not nome or not dn:
            flash("Preencha nome e nascimento.")
            return render_template("paciente_novo.html", title="Novo paciente")

        paciente = Paciente(nome=nome, dn=dn, telefone=telefone, endereco=endereco)
        db.session.add(paciente)
        db.session.commit()

        return redirect(url_for("protocolo", paciente_id=paciente.id))

    return render_template("paciente_novo.html", title="Novo paciente")

@app.route("/protocolo/<int:paciente_id>", methods=["GET", "POST"])
@login_required
def protocolo(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    idade = calcular_idade(paciente.dn)

    # contexto padrão
    queixas_sel, historico_sel, achados_sel = [], [], []
    exames_p, links_bib, biblio_txt = [], [], []
    just = ""
    score = 0
    atendimento_id = None

    if request.method == "POST":
        queixas_sel = request.form.getlist("queixas_sel")
        historico_sel = request.form.getlist("historico_sel")
        achados_sel = request.form.getlist("achados_sel")

        ex_set, bib_set, just_list = set(), set(), []
        link_list = []

        score_calc = 2 if idade > 60 else 0

        for a in achados_sel:
            if a in PROTOCOLOS_MASTER:
                p = PROTOCOLOS_MASTER[a]
                ex_set.update(p["exames"])
                bib_set.add(p["biblio"])
                just_list.append(p["just"])
                link_list.append({"nome": p["biblio"], "link": p["link"]})
                score_calc += p["score"]

        exames_p = sorted(list(ex_set))
        biblio_txt = sorted(list(bib_set))
        links_bib = link_list
        just = " ".join(just_list).strip()
        score = min(score_calc, 10)

        atendimento = Atendimento(
            paciente_id=paciente.id,
            consultor=current_user.id,
            queixas=json.dumps(queixas_sel, ensure_ascii=False),
            historico=json.dumps(historico_sel, ensure_ascii=False),
            achados=json.dumps(achados_sel, ensure_ascii=False),
            score=score,
            exames=json.dumps(exames_p, ensure_ascii=False),
            justificativa=just,
            bibliografia=json.dumps(biblio_txt, ensure_ascii=False),
        )
        db.session.add(atendimento)
        db.session.commit()
        atendimento_id = atendimento.id

    return render_template(
        "protocolo.html",
        title="Protocolo",
        paciente=paciente,
        idade=idade,
        QUEIXAS_LISTA=QUEIXAS_LISTA,
        HISTORICO_LISTA=HISTORICO_LISTA,
        gatilhos=sorted(PROTOCOLOS_MASTER.keys()),
        queixas_sel=queixas_sel,
        historico_sel=historico_sel,
        achados_sel=achados_sel,
        exames_p=exames_p,
        links_bib=links_bib,
        biblio_txt=biblio_txt,
        just=just,
        score=score,
        atendimento_id=atendimento_id
    )

@app.route("/imprimir/<int:atendimento_id>")
@login_required
def imprimir(atendimento_id):
    atendimento = Atendimento.query.get_or_404(atendimento_id)
    paciente = atendimento.paciente

    exames_p = json.loads(atendimento.exames or "[]")
    biblio_txt = json.loads(atendimento.bibliografia or "[]")
    exames_outros = [e for e in EXAMES_GERAIS if e not in exames_p]

    dn_fmt = datetime.strptime(paciente.dn, "%Y-%m-%d").strftime("%d/%m/%Y")

    return render_template(
        "imprimir.html",
        atendimento=atendimento,
        paciente=paciente,
        exames_p=exames_p,
        exames_outros=exames_outros,
        biblio_txt=biblio_txt,
        dn_fmt=dn_fmt
    )

# =========================
# 6) START
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)
