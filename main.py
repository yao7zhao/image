from os import environ
from oauth2client import client, crypt
from functools import wraps
from flask import Flask, request, send_file, abort
from flask import session, g
from flask.json import jsonify
from flask.ext.cors import cross_origin, CORS
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.session import Session
from sqlalchemy.sql import exists
from models import db, Categories, User, Postings
import logging

CLIENT_ID = environ['WEB_CLIENT_ID']

app = Flask(__name__)

<<<<<<< HEAD
=======
app.config['DEBUG'] = True
>>>>>>> master
app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db

db.init_app(app)

with app.app_context():
    Session(app)

#### Middleware ####
# Authorization View (only used for login)
@app.route('/api/auth/', methods=['POST'], strict_slashes=False)
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
def auth():
    token = request.form.get('id_token')
    if authorizer(token):
        # Add id_token as a server side session cookie
        session['id_token'] = token
        return '', 200
    return '', 403

# Logout View
@app.route('/api/logout/', strict_slashes=False)
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
def logout():
    # Delete the session from the database
    session.clear()
    session.modified = True
    return '', 200

# TODO: Searching here

#### Helpers ####
# The actual authorizer that does the work
def authorizer(token):
    if not token: return False
    try:
        idinfo = client.verify_id_token(token, CLIENT_ID);
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise crypt.AppIdentityError("Wrong issuer.")
        if idinfo['hd'] != 'uconn.edu':
            raise crypt.AppIdentityError("Wrong hosted domain.")
    except crypt.AppIdentityError:
        return False

    # Set some globals that might be useful for this context
    g.user = {}
    g.user['id'] = long(idinfo['sub'])

    # Database
    if not db.session.query(exists().where(User.id == long(idinfo['sub']))).scalar():
        db.session.add(User(id=long(idinfo['sub']), name=idinfo['name'], email=idinfo['email']))
        db.session.commit()
    return True

# Authorization Decorator (used when other Views are accessed)
def auth_req(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if authorizer(session.get('id_token', None)):
            return f(*args, **kwargs)
        logging.getLogger('Main').info('Unauthorized access')
        return '', 403
    return wrapper

# Takes a SQLAlchemy mapping and converts it to representational dictionary
def to_dict(row):
    res = dict()
    for c in row.__table__.columns:
        res[c.name] = getattr(row, c.name)
    return res

#### API ####
# User API:
@app.route('/api/user/', methods=['GET'], strict_slashes=False)
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
@auth_req
def get_user():
    id = request.args.get('id')
    email = request.args.get('email')
    name = request.args.get('name')

    # Query
    query = User.query
    if id: query = query.filter(User.id == id)
    if email: query = query.filter(User.email == email)
    if name: query = query.filter(User.name == name)

    # Return the JSON
    return jsonify(data=[to_dict(r) for r in query.all()])

# Postings API:
@app.route('/api/postings/', methods=['GET'], strict_slashes=False)
<<<<<<< HEAD
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
=======
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True, allow_headers=['*'])
>>>>>>> master
@auth_req
def get_postings():
    id = request.args.get('id')
    owner = request.args.get('owner')
    category = request.args.get('category')
    cost = request.args.get('cost')
    max_cost = request.args.get('max_cost')
    
    per_page = request.args.get('per_page', default=20)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 20
    page = request.args.get('page', default=1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    sort = request.args.get('sort', default='newest')

    # Query
    query = Postings.query
    if id: query = query.filter(Postings.id == id)
    if owner: query = query.filter(Postings.owner == owner)
    if category: query = query.filter(Postings.category == category)
    if cost: query = query.filter(Postings.cost == cost)
    if max_cost: query = query.filter(Postings.cost <= max_cost)

    if sort == 'newest':
        query = query.order_by(Postings.timestamp.desc())
    elif sort == 'oldest':
        query = query.order_by(Postings.timestamp.asc())
    elif sort == 'highest_cost':
        query = query.order_by(Postings.cost.desc())
    elif sort == 'lowest_cost':
        query = query.order_by(Postings.cost.asc())

    page = query.paginate(page, per_page, error_out=False)

    # Return the JSON
    return jsonify(data=[to_dict(r) for r in page.items]), 200

@app.route('/api/postings/', methods=['POST'], strict_slashes=False)
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
@auth_req
def post_postings():
    description = request.form.get('description', None)
    category = request.form.get('category', None)
    cost = request.form.get('cost', None)
    title = request.form.get('title', None)

    # Some sanity checking
    if not all([category, cost, title]):
        return '', 400

    # Else continue
    post = Postings(owner=g.user['id'], description=description, cost=cost,
        category=category, title=title)
    
    # Add entry to database and commit
    # Also prevent duplicate entries due to double clicks
    if not Postings.query(exists().where((Postings.owner==g.user['id']) &
        (Postings.description==description) & (Postings.category==category) &
        (Postings.title==title))).scalar():
        db.session.add(post)
        db.session.commit()

    return '',  200

@app.route('/api/postings/', methods=['DELETE'], strict_slashes=False)
@cross_origin(origins=environ['CORS_URLS'].split(','), supports_credentials=True)
@auth_req
def delete_postings():
    id = request.args.get('id')

    # Only the owner of this post can delete it
    query = Postings.query
    posting = query.filter(Postings.id == id).first()
    if not posting:
        return '', 400

    # Verify this person is the owner
    if not g.user['id'] == posting.owner:
        return '', 403

    # Else continue with the delete
    db.session.delete(posting)
    db.session.commit()
    return '', 200

# FOR DEBUGGING
@app.route('/login/', strict_slashes=False)
def login():
    return send_file('login.html')

if environ['DEBUG'] == 'True':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('flask_cors').level = logging.DEBUG

if __name__ == '__main__':
    app.run(debug=True)
