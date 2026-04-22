import os, json, requests
from datetime import timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/immo.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

RAPIDAPI_KEY  = os.environ.get('RAPIDAPI_KEY', '')
RAPIDAPI_HOST = "zoopla6.p.rapidapi.com"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'immo-secret-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt    = JWTManager(app)

# ─── MODELS ───

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    prenom        = db.Column(db.String(50),  nullable=False)
    nom           = db.Column(db.String(50),  nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    def to_dict(self):
        return {'id': self.id, 'prenom': self.prenom, 'nom': self.nom, 'email': self.email}

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
            'rooms': self.rooms, 'surface': self.surface, 'description': self.description
        }

# ─── ZOOPLA API ───

def fetch_zoopla(city, listing_type):
    """Appelle Zoopla6 RapidAPI et retourne une liste d'appartements formatés."""
    try:
        if listing_type == 'rent':
            zoopla_url = f"https://www.zoopla.co.uk/to-rent/property/{city.lower()}/?q={city}&results_sort=newest_listings&search_source=to-rent"
        else:
            zoopla_url = f"https://www.zoopla.co.uk/for-sale/property/{city.lower()}/?q={city}&results_sort=newest_listings&search_source=for-sale"

        resp = requests.get(
            "https://zoopla6.p.rapidapi.com/properties_list.php",
            params={"url": zoopla_url},
            headers={
                "x-rapidapi-key":  RAPIDAPI_KEY,
                "x-rapidapi-host": RAPIDAPI_HOST,
                "Content-Type":    "application/json"
            },
            timeout=10
        )

        if resp.status_code != 200:
            print(f"Zoopla error: {resp.status_code}")
            return []

        data = resp.json()

        # Extraire les propriétés selon la structure Zoopla6
        props = []
        if isinstance(data, list):
            props = data
        elif isinstance(data, dict):
            props = data.get('properties', data.get('listings', data.get('results', [])))

        results = []
        for i, p in enumerate(props[:20]):  # max 20 annonces
            try:
                # Coordonnées
                lat = float(p.get('latitude',  p.get('lat', 51.5074)))
                lon = float(p.get('longitude', p.get('lng', -0.1278)))

                # Prix
                price_raw = p.get('price', p.get('rental_price', '0'))
                if isinstance(price_raw, str):
                    price = float(''.join(filter(str.isdigit, price_raw)) or '0')
                else:
                    price = float(price_raw or 0)

                # Images
                imgs = p.get('images', p.get('image_urls', []))
                if isinstance(imgs, str):
                    imgs = [imgs]
                if not imgs:
                    thumb = p.get('thumbnail_url', p.get('image_url', ''))
                    imgs = [thumb] if thumb else [
                        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800"
                    ]

                # Adresse
                addr = p.get('displayable_address',
                       p.get('address',
                       p.get('street_name', f"{city} Property")))

                # Rooms
                rooms = int(p.get('num_bedrooms', p.get('bedrooms', 1)) or 1)

                # Agent / propriétaire
                agent = p.get('agent_name',
                        p.get('letting_agent',
                        p.get('agent', 'Agent Immobilier')))
                phone = p.get('agent_phone',
                        p.get('phone', '+44 20 0000 0000'))

                results.append({
                    'id':          i + 1000,
                    'title':       p.get('title', p.get('property_type', 'Propriété')) + f" - {addr[:40]}",
                    'type':        listing_type,
                    'price':       price,
                    'city':        city,
                    'address':     addr,
                    'latitude':    lat,
                    'longitude':   lon,
                    'owner_name':  agent,
                    'phone':       phone,
                    'images':      imgs[:5],
                    'rooms':       rooms,
                    'surface':     float(p.get('floor_area', p.get('size', rooms * 20)) or rooms * 20),
                    'description': p.get('description', p.get('short_description', 'Voir les détails sur Zoopla.'))[:300]
                })
            except Exception as e:
                print(f"Parse error on property {i}: {e}")
                continue

        print(f"Zoopla: {len(results)} propriétés récupérées pour {city}")
        return results

    except Exception as e:
        print(f"Zoopla fetch error: {e}")
        return []

# ─── INIT DB ───

def seed_data():
    try:
        if Apartment.query.count() > 0:
            return
        # Données de secours si Zoopla ne répond pas
        samples = [
            Apartment(title="Flat in Central London", type="rent", price=2500,
                city="London", address="Baker Street, London NW1",
                latitude=51.5227, longitude=-0.1571,
                owner_name="London Estates", phone="+44 20 7946 0958",
                images=json.dumps(["https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800"]),
                rooms=2, surface=65, description="Beautiful flat in Central London."),
            Apartment(title="Studio near Tower Bridge", type="rent", price=1800,
                city="London", address="Tower Bridge Road, London SE1",
                latitude=51.5055, longitude=-0.0754,
                owner_name="Thames Properties", phone="+44 20 7946 0123",
                images=json.dumps(["https://images.unsplash.com/photo-1554995207-c18c203602cb?w=800"]),
                rooms=1, surface=35, description="Modern studio near Tower Bridge."),
            Apartment(title="House for Sale - Notting Hill", type="buy", price=950000,
                city="London", address="Portobello Road, London W11",
                latitude=51.5151, longitude=-0.2028,
                owner_name="West London Realty", phone="+44 20 7946 0456",
                images=json.dumps(["https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800"]),
                rooms=4, surface=140, description="Stunning house in Notting Hill."),
        ]
        for s in samples:
            db.session.add(s)
        db.session.commit()
    except Exception as e:
        print(f"Seed error: {e}")
        db.session.rollback()

try:
    with app.app_context():
        db.create_all()
        seed_data()
        print("==> Demarrage OK")
except Exception as e:
    print(f"==> Init error: {e}")

# ─── ROUTES ───

@app.route('/')
def index():
    return jsonify({'message': 'ImmoLocate API OK'}), 200

@app.route('/api/health')
def health():
    try:
        db.create_all()
        return jsonify({'status': 'ok', 'users': User.query.count(), 'apartments': Apartment.query.count(), 'zoopla': bool(RAPIDAPI_KEY)})
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    try:
        db.create_all()
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        db.create_all()
        data = request.get_json()
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'error': 'Donnees manquantes'}), 400
        user = User.query.filter_by(email=data['email']).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
        token = create_access_token(identity=str(user.id))
        return jsonify({'token': token, 'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apartments', methods=['GET'])
def get_apartments():
    try:
        db.create_all()
        city     = request.args.get('city', 'London')
        apt_type = request.args.get('type', '')

        # Si clé RapidAPI disponible → données Zoopla en temps réel
        if RAPIDAPI_KEY:
            if apt_type in ('rent', 'buy'):
                results = fetch_zoopla(city, apt_type)
            else:
                rent = fetch_zoopla(city, 'rent')
                buy  = fetch_zoopla(city, 'buy')
                results = rent + buy
            if results:
                return jsonify(results)

        # Fallback → données locales SQLite
        query = Apartment.query
        if city:
            query = query.filter(Apartment.city.ilike(f'%{city}%'))
        if apt_type in ('rent', 'buy'):
            query = query.filter_by(type=apt_type)
        return jsonify([a.to_dict() for a in query.all()])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apartments/<int:apt_id>', methods=['GET'])
def get_apartment(apt_id):
    return jsonify(Apartment.query.get_or_404(apt_id).to_dict())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
