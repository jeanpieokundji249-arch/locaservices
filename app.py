import os
from flask import Flask, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cle_secrete_hyper_securisee_a_changer"

# Configuration des frais de plateforme (ex: 15% de commission)
TAUX_COMMISSION = 0.15 

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def fichier_autorise(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- MODÈLES DE LA BASE DE DONNÉES ---

class Utilisateur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(120), nullable=False)

class Annonce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(100), nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    prix_par_jour = db.Column(db.Float, nullable=False)
    proprietaire = db.Column(db.String(80), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)
    est_sponsorisee = db.Column(db.Boolean, default=False) # Option sponsorisée payante

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annonce_id = db.Column(db.Integer, db.ForeignKey('annonce.id'), nullable=False)
    client = db.Column(db.String(80), nullable=False)
    date_debut = db.Column(db.String(20), nullable=False)
    date_fin = db.Column(db.String(20), nullable=False)
    prix_total = db.Column(db.Float, nullable=False)
    frais_plateforme = db.Column(db.Float, nullable=False) # Votre gain / commission
    gain_proprietaire = db.Column(db.Float, nullable=False) # Part revenant au propriétaire
    statut = db.Column(db.String(40), default="En attente de confirmation")

with app.app_context():
    db.create_all()

# CSS Pro avec badges VIP / Sponsorisé
CSS_STYLE = '''
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body { background-color: #f4f6f9; color: #333; }
    header { background-color: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.08); padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
    .logo { color: #1e3a8a; font-size: 24px; font-weight: bold; text-decoration: none; }
    nav a { text-decoration: none; padding: 8px 16px; border-radius: 6px; font-weight: 500; font-size: 14px; margin-left: 10px; }
    .btn-primary { background-color: #2563eb; color: white; }
    .btn-secondary { background-color: #10b981; color: white; }
    .btn-danger { background-color: #ef4444; color: white; }
    .btn-outline { border: 1px solid #cbd5e1; color: #475569; }
    .container { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
    .search-bar { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.04); display: flex; gap: 15px; margin-bottom: 30px; }
    .search-bar input, .search-bar select { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; flex: 1; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 25px; }
    .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); position: relative; }
    .card-sponsored { border: 2px solid #f59e0b; }
    .badge-sponsored { position: absolute; top: 10px; right: 10px; background: #f59e0b; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .card-img { width: 100%; height: 180px; object-fit: cover; background-color: #e2e8f0; }
    .card-body { padding: 18px; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #e2e8f0; color: #475569; margin-bottom: 8px; }
    .form-card { max-width: 450px; margin: 60px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }
    .form-group { margin-bottom: 15px; }
    .form-group label { display: block; margin-bottom: 5px; font-size: 14px; font-weight: 600; color: #475569; }
    .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; }
</style>
'''

@app.route("/")
def accueil():
    est_connecte = "utilisateur" in session
    nom_client = session.get("utilisateur", "")

    recherche = request.args.get("q", "").strip()
    categorie_filtre = request.args.get("categorie", "").strip()

    query = Annonce.query.order_by(Annonce.est_sponsorisee.desc(), Annonce.id.desc())

    if recherche:
        query = query.filter(Annonce.titre.ilike(f"%{recherche}%"))
    if categorie_filtre:
        query = query.filter_by(categorie=categorie_filtre)

    annonces = query.all()

    html = f'''
    <!DOCTYPE html>
    <html lang="fr"><head><meta charset="UTF-8"><title>LocaServices - Matériel & Équipements</title>{CSS_STYLE}</head>
    <body>
        <header>
            <a href="/" class="logo">📦 LocaServices</a>
            <nav>
    '''

    if est_connecte:
        html += f'<span>Connecté : <strong>{nom_client}</strong></span> <a href="/dashboard" class="btn-primary">Mon Espace</a> <a href="/deconnexion" class="btn-danger">Déconnexion</a>'
    else:
        html += '<a href="/connexion" class="btn-primary">Connexion</a> <a href="/inscription" class="btn-secondary">Inscription</a>'

    html += f'''
            </nav>
        </header>

        <div class="container">
            <form class="search-bar" method="GET" action="/">
                <input type="text" name="q" placeholder="Rechercher un équipement..." value="{recherche}">
                <select name="categorie">
                    <option value="">Toutes les catégories</option>
                    <option value="Outillage" {"selected" if categorie_filtre == "Outillage" else ""}>Outillage</option>
                    <option value="Audiovisuel" {"selected" if categorie_filtre == "Audiovisuel" else ""}>Audiovisuel</option>
                    <option value="Événementiel" {"selected" if categorie_filtre == "Événementiel" else ""}>Événementiel</option>
                    <option value="Informatique" {"selected" if categorie_filtre == "Informatique" else ""}>Informatique</option>
                </select>
                <button type="submit" class="btn-primary" style="border:none; cursor:pointer;">Rechercher</button>
            </form>

            <h2>Matériel disponible</h2><br>
            <div class="grid">
    '''

    for item in annonces:
        img_src = f"/uploads/{item.image_filename}" if item.image_filename else "https://via.placeholder.com/300x180?text=Pas+d'image"
        card_class = "card card-sponsored" if item.est_sponsorisee else "card"
        
        html += f'''
        <div class="{card_class}">
            {'<span class="badge-sponsored">★ EN VEDETTE</span>' if item.est_sponsorisee else ''}
            <img src="{img_src}" class="card-img" alt="{item.titre}">
            <div class="card-body">
                <span class="badge">{item.categorie}</span>
                <h3 style="font-size: 18px; margin-bottom: 8px;">{item.titre}</h3>
                <p style="color: #2563eb; font-weight: bold; font-size: 20px; margin-bottom: 10px;">{item.prix_par_jour} $ <span style="font-size:12px; color:#64748b;">/ jour</span></p>
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 15px;">Par : {item.proprietaire}</p>
                <a href="/reserver/{item.id}" class="btn-secondary" style="display:block; text-align:center; text-decoration:none;">Louer maintenant</a>
            </div>
        </div>
        '''

    html += '</div></div></body></html>'
    return html

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/reserver/<int:annonce_id>", methods=["GET", "POST"])
def reserver(annonce_id):
    if "utilisateur" not in session:
        return redirect(url_for("connexion"))

    annonce = Annonce.query.get_or_404(annonce_id)

    if annonce.proprietaire == session["utilisateur"]:
        return '<script>alert("Impossible de réserver votre propre matériel !"); window.location.href="/";</script>'

    if request.method == "POST":
        date_debut_str = request.form.get("date_debut")
        date_fin_str = request.form.get("date_fin")

        d1 = datetime.strptime(date_debut_str, "%Y-%m-%d")
        d2 = datetime.strptime(date_fin_str, "%Y-%m-%d")
        nb_jours = (d2 - d1).days
        if nb_jours <= 0:
            nb_jours = 1

        total = nb_jours * annonce.prix_par_jour
        frais = round(total * TAUX_COMMISSION, 2)
        gain_proprio = round(total - frais, 2)

        nouvelle_reservation = Reservation(
            annonce_id=annonce.id,
            client=session["utilisateur"],
            date_debut=date_debut_str,
            date_fin=date_fin_str,
            prix_total=total,
            frais_plateforme=frais,
            gain_proprietaire=gain_proprio,
            statut="En attente de confirmation"
        )
        db.session.add(nouvelle_reservation)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return f'''
    <!DOCTYPE html><html><head>{CSS_STYLE}</head>
    <body>
        <div class="form-card">
            <h2>Réserver : {annonce.titre}</h2><br>
            <p style="margin-bottom: 15px; color: #64748b;">Tarif : <strong>{annonce.prix_par_jour} $ / jour</strong></p>
            <form method="POST">
                <div class="form-group"><label>Date de début</label><input type="date" name="date_debut" required></div>
                <div class="form-group"><label>Date de fin</label><input type="date" name="date_fin" required></div>
                <button type="submit" class="btn-secondary" style="width:100%; border:none; padding:12px; cursor:pointer;">Envoyer la demande</button>
            </form>
            <br><a href="/" style="color:#64748b;">← Annuler</a>
        </div>
    </body></html>
    '''

@app.route("/action_reservation/<int:reservation_id>/<string:action>")
def action_reservation(reservation_id, action):
    if "utilisateur" not in session:
        return redirect(url_for("connexion"))

    res = Reservation.query.get_or_404(reservation_id)
    annonce = Annonce.query.get(res.annonce_id)

    if annonce.proprietaire == session["utilisateur"]:
        if action == "accepter":
            res.statut = "Acceptée (En attente de paiement)"
        elif action == "refuser":
            res.statut = "Refusée"
        db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/payer/<int:reservation_id>", methods=["GET", "POST"])
def payer(reservation_id):
    if "utilisateur" not in session:
        return redirect(url_for("connexion"))

    res = Reservation.query.get_or_404(reservation_id)
    annonce = Annonce.query.get(res.annonce_id)

    if request.method == "POST":
        mode_paiement = request.form.get("mode_paiement")
        res.statut = f"Payé ({mode_paiement})"
        db.session.commit()
        return redirect(url_for("dashboard"))

    return f'''
    <!DOCTYPE html><html><head>{CSS_STYLE}</head>
    <body>
        <div class="form-card" style="text-align: center;">
            <h2 style="color:#10b981;">Paiement Sécurisé</h2><br>
            <p>Article : <strong>{annonce.titre}</strong></p>
            <p style="color:#64748b; font-size:14px; margin-top:5px;">Du {res.date_debut} au {res.date_fin}</p>
            <h1 style="color:#2563eb; margin: 15px 0;">{res.prix_total} $</h1>
            <form method="POST">
                <div class="form-group" style="text-align:left;">
                    <label>Mode de règlement</label>
                    <select name="mode_paiement">
                        <option value="Mobile Money">Mobile Money (M-Pesa / Orange / Airtel)</option>
                        <option value="Carte Bancaire">Carte Bancaire (Visa / Mastercard)</option>
                    </select>
                </div>
                <button type="submit" class="btn-secondary" style="width:100%; border:none; padding:12px; cursor:pointer;">Valider le paiement</button>
            </form>
        </div>
    </body></html>
    '''

@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    erreur = ""
    if request.method == "POST":
        identifiant = request.form.get("username")
        mot_de_passe = request.form.get("password")

        existant = Utilisateur.query.filter_by(nom_utilisateur=identifiant).first()
        if existant:
            erreur = "Ce nom d'utilisateur est déjà pris."
        else:
            nouveau = Utilisateur(nom_utilisateur=identifiant, mot_de_passe=mot_de_passe)
            db.session.add(nouveau)
            db.session.commit()
            session["utilisateur"] = identifiant
            return redirect(url_for("dashboard"))

    return f'''
    <!DOCTYPE html><html><head>{CSS_STYLE}</head>
    <body>
        <div class="form-card">
            <h2>Créer un compte</h2><br>
            {'<p style="color:red;">' + erreur + '</p>' if erreur else ''}
            <form method="POST">
                <div class="form-group"><label>Nom d'utilisateur</label><input type="text" name="username" required></div>
                <div class="form-group"><label>Mot de passe</label><input type="password" name="password" required></div>
                <button type="submit" class="btn-secondary" style="width:100%; border:none; padding:12px; cursor:pointer;">S'inscrire</button>
            </form>
            <br><p><a href="/connexion">Déjà un compte ? Se connecter</a></p>
        </div>
    </body></html>
    '''

@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    erreur = ""
    if request.method == "POST":
        identifiant = request.form.get("username")
        mot_de_passe = request.form.get("password")

        compte = Utilisateur.query.filter_by(nom_utilisateur=identifiant, mot_de_passe=mot_de_passe).first()
        if compte:
            session["utilisateur"] = compte.nom_utilisateur
            return redirect(url_for("dashboard"))
        else:
            erreur = "Identifiant ou mot de passe incorrect."

    return f'''
    <!DOCTYPE html><html><head>{CSS_STYLE}</head>
    <body>
        <div class="form-card">
            <h2>Connexion</h2><br>
            {'<p style="color:red;">' + erreur + '</p>' if erreur else ''}
            <form method="POST">
                <div class="form-group"><label>Nom d'utilisateur</label><input type="text" name="username" required></div>
                <div class="form-group"><label>Mot de passe</label><input type="password" name="password" required></div>
                <button type="submit" class="btn-primary" style="width:100%; border:none; padding:12px; cursor:pointer;">Se connecter</button>
            </form>
            <br><p><a href="/inscription">Pas encore de compte ? S'inscrire</a></p>
        </div>
    </body></html>
    '''

@app.route("/dashboard")
def dashboard():
    if "utilisateur" not in session:
        return redirect(url_for("connexion"))

    utilisateur_courant = session['utilisateur']

    mes_annonces = Annonce.query.filter_by(proprietaire=utilisateur_courant).all()
    mes_reservations_client = Reservation.query.filter_by(client=utilisateur_courant).all()

    ids_mes_annonces = [a.id for a in mes_annonces]
    demandes_recues = Reservation.query.filter(Reservation.annonce_id.in_(ids_mes_annonces)).all() if ids_mes_annonces else []

    html = f'''
    <!DOCTYPE html><html><head>{CSS_STYLE}</head>
    <body>
        <header>
            <a href="/" class="logo">📦 LocaServices</a>
            <nav><a href="/" class="btn-outline" style="text-decoration:none;">Catalogue</a> <a href="/deconnexion" class="btn-danger" style="text-decoration:none;">Déconnexion</a></nav>
        </header>

        <div class="container">
            <h1>Espace Client - {utilisateur_courant}</h1><br>

            <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.04); margin-bottom: 30px;">
                <h3>Publier une nouvelle annonce</h3><br>
                <form action="/ajouter_annonce" method="POST" enctype="multipart/form-data">
                    <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                        <input type="text" name="titre" placeholder="Titre de l'annonce" required style="flex:2; padding:10px; border:1px solid #cbd5e1; border-radius:6px;">
                        <select name="categorie" required style="flex:1; padding:10px; border:1px solid #cbd5e1; border-radius:6px;">
                            <option value="Outillage">Outillage</option>
                            <option value="Audiovisuel">Audiovisuel</option>
                            <option value="Événementiel">Événementiel</option>
                            <option value="Informatique">Informatique</option>
                        </select>
                        <input type="number" step="0.01" name="prix" placeholder="Prix par jour ($)" required style="flex:1; padding:10px; border:1px solid #cbd5e1; border-radius:6px;">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="font-size: 14px; font-weight: 600; color: #475569;">Photo : </label>
                        <input type="file" name="image" accept="image/*">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label><input type="checkbox" name="sponsorise" value="1"> 🌟 Booster l'annonce (Placer en tête de liste pour 2$)</label>
                    </div>
                    <button type="submit" class="btn-primary" style="border:none; padding: 10px 20px; cursor:pointer;">Publier l'annonce</button>
                </form>
            </div>

            <h3>Demandes reçues (Propriétaire)</h3><br>
    '''

    if not demandes_recues:
        html += '<p style="color: #64748b; margin-bottom:20px;">Aucune demande reçue pour le moment.</p>'
    else:
        for d in demandes_recues:
            annonce_associee = Annonce.query.get(d.annonce_id)
            html += f'''
            <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{annonce_associee.titre}</strong> par <em>{d.client}</em><br>
                    <small>Période : {d.date_debut} au {d.date_fin} | Total : <strong>{d.prix_total} $</strong> (Votre gain net : <span style="color:#10b981;">{d.gain_proprietaire} $</span>)</small>
                </div>
                <div>
            '''
            if d.statut == "En attente de confirmation":
                html += f'''
                <a href="/action_reservation/{d.id}/accepter" class="btn-secondary" style="text-decoration:none;">Accepter</a>
                <a href="/action_reservation/{d.id}/refuser" class="btn-danger" style="text-decoration:none;">Refuser</a>
                '''
            else:
                html += f'<span class="badge">{d.statut}</span>'
            html += '</div></div>'

    html += '<br><h3>Vos locations demandées (Client)</h3><br>'

    if not mes_reservations_client:
        html += '<p style="color: #64748b;">Aucune réservation enregistrée.</p>'
    else:
        for r in mes_reservations_client:
            annonce_associee = Annonce.query.get(r.annonce_id)
            html += f'''
            <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{annonce_associee.titre}</strong> (Total : {r.prix_total} $)<br>
                    <small>Période : {r.date_debut} au {r.date_fin}</small>
                </div>
                <div>
            '''
            if r.statut == "Acceptée (En attente de paiement)":
                html += f'<a href="/payer/{r.id}" class="btn-secondary" style="text-decoration:none;">Payer la location</a>'
            else:
                html += f'<span class="badge">{r.statut}</span>'
            html += '</div></div>'

    html += '</div></body></html>'
    return html

@app.route("/ajouter_annonce", methods=["POST"])
def ajouter_annonce():
    if "utilisateur" not in session:
        return redirect(url_for("connexion"))

    titre = request.form.get("titre")
    categorie = request.form.get("categorie")
    prix = float(request.form.get("prix"))
    est_sponsorise = True if request.form.get("sponsorise") == "1" else False

    filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and fichier_autorise(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    nouvelle_annonce = Annonce(
        titre=titre,
        categorie=categorie,
        prix_par_jour=prix,
        proprietaire=session['utilisateur'],
        image_filename=filename,
        est_sponsorisee=est_sponsorise
    )
    db.session.add(nouvelle_annonce)
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/deconnexion")
def deconnexion():
    session.pop("utilisateur", None)
    return redirect(url_for("accueil"))

if __name__ == "__main__":
    app.run(debug=True)
