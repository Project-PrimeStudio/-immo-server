from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
import json
import os
from datetime import timedelta

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///immo.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'immo-secret-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt    = JWTManager(app)

# ─────────────── MODELS ───────────────

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    prenom        = db.Column(db.String(50),  nullable=False)
    nom           = db.Column(db.String(50),  nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'prenom': self.prenom,
                'nom': self.nom, 'email': self.email}

class Apartment(db.Model):
    __tablename__ = 'apartments'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    type        = db.Column(db.String(20),  nullable=False)
    price       = db.Column(db.Float,       nullable=False)
    city        = db.Column(db.String(100), nullable=False)
    address     = db.Column(db.String(200), nullable=False)
    latitude    = db.Column(db.Float,       nullable=False)
    longitude   = db.Column(db.Float,       nullable=False)
    owner_name  = db.Column(db.String(100), nullable=False)
    phone       = db.Column(db.String(20),  nullable=False)
    images      = db.Column(db.Text,        nullable=False)
    rooms       = db.Column(db.Integer,     nullable=False)
    surface     = db.Column(db.Float,       nullable=False)
    description = db.Column(db.Text,        nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'type': self.type,
            'price': self.price, 'city': self.city, 'address': self.address,
            'latitude': self.latitude, 'longitude': self.longitude,
            'owner_name': self.owner_name, 'phone': self.phone,
            'images': json.loads(self.images),
            'rooms': self.rooms, 'surface': self.surface,
            'description': self.description
        }

# ─────────────── INIT DB ───────────────
# Utilise before_request pour garantir que les tables existent
# meme apres un redemarrage Render qui efface le SQLite

_db_ready = False

@app.before_request
def init_db():
    global _db_ready
    if not _db_ready:
        db.create_all()
        seed_data()
        _db_ready = True

def seed_data():
    if Apartment.query.count() > 0:
        return
    samples = [
        Apartment(
            title="Bel appartement 3 pieces renove - Rivoli",
            type="rent", price=1800, city="Paris",
            address="15 Rue de Rivoli, 75001 Paris",
            latitude=48.8566, longitude=2.3522,
            owner_name="Jean Dupont", phone="+33612345678",
            images=json.dumps([
                "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
                "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800",
            ]),
            rooms=3, surface=75,
            description="Magnifique appartement au coeur de Paris, entierement renove et lumineux."
        ),
        Apartment(
            title="Studio moderne - Le Marais",
            type="rent", price=950, city="Paris",
            address="8 Rue des Archives, 75004 Paris",
            latitude=48.8578, longitude=2.3560,
            owner_name="Marie Laurent", phone="+33698765432",
            images=json.dumps([
                "https://images.unsplash.com/photo-1554995207-c18c203602cb?w=800",
                "https://images.unsplash.com/photo-1507089947368-19c1da9775ae?w=800",
            ]),
            rooms=1, surface=32,
            description="Studio moderne dans le quartier du Marais, cuisine ouverte, salle de bain refaite."
        ),
        Apartment(
            title="Grand T4 avec terrasse - Montmartre",
            type="buy", price=650000, city="Paris",
            address="22 Rue Lepic, 75018 Paris",
            latitude=48.8850, longitude=2.3340,
            owner_name="Pierre Martin", phone="+33645678901",
            images=json.dumps([
                "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800",
                "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800",
            ]),
            rooms=4, surface=110,
            description="Superbe appartement avec terrasse de 20m2 vue imprenable sur Paris."
        ),
        Apartment(
            title="F2 lumineux proche Part-Dieu",
            type="rent", price=780, city="Lyon",
            address="10 Rue Garibaldi, 69003 Lyon",
            latitude=45.7640, longitude=4.8357,
            owner_name="Sophie Bernard", phone="+33623456789",
            images=json.dumps([
                "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=800",
                "https://images.unsplash.com/photo-1560185007-5f0bb1866cab?w=800",
            ]),
            rooms=2, surface=48,
            description="Appartement F2 tres lumineux proche de la gare Part-Dieu. Balcon vue degagee."
        ),
        Apartment(
            title="Villa vue mer avec piscine",
            type="buy", price=890000, city="Marseille",
            address="5 Boulevard de la Corniche, 13007 Marseille",
            latitude=43.2780, longitude=5.3600,
            owner_name="Luc Moreau", phone="+33634567890",
            images=json.dumps([
                "https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800",
                "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
            ]),
            rooms=6, surface=200,
            description="Villa avec vue mer et piscine privee sur la Corniche. Jardin paysage."
        ),
        Apartment(
            title="T3 centre-ville - Nice",
            type="rent", price=1200, city="Nice",
            address="3 Avenue Jean Medecin, 06000 Nice",
            latitude=43.7102, longitude=7.2620,
            owner_name="Isabelle Petit", phone="+33678901234",
            images=json.dumps([
                "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
                "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800",
            ]),
            rooms=3, surface=65,
            description="T3 lumineux en plein centre de Nice, 5 minutes de la Promenade des Anglais."
        ),
    ]
    for apt in samples:
        db.session.add(apt)
    db.session.commit()
    print("Donnees inserees avec succes")

# ─────────────── ROUTES ───────────────

@app.route('/')
def index():
    return jsonify({'message': 'ImmoLocate API en ligne'}), 200

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'users': User.query.count(),
        'apartments': Apartment.query.count()
    })

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['prenom', 'nom', 'email', 'password']):
        return jsonify({'error': 'Donnees manquantes'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Cet email est deja utilise'}), 409
    hashed = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(prenom=data['prenom'], nom=data['nom'],
                email=data['email'], password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Donnees manquantes'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200

@app.route('/api/apartments', methods=['GET'])
def get_apartments():
    city     = request.args.get('city', '')
    apt_type = request.args.get('type', '')
    query    = Apartment.query
    if city:
        query = query.filter(Apartment.city.ilike(f'%{city}%'))
    if apt_type in ('rent', 'buy'):
        query = query.filter_by(type=apt_type)
    return jsonify([a.to_dict() for a in query.all()])

@app.route('/api/apartments/<int:apt_id>', methods=['GET'])
def get_apartment(apt_id):
    return jsonify(Apartment.query.get_or_404(apt_id).to_dict())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
