from flask import Flask, render_template, request, redirect, url_for, \
    session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, Item, Catalog
from google.oauth2 import id_token
from google.auth.transport import requests

import random
import string
import json

app = Flask(__name__, template_folder='../views',
            static_folder='../views/static')

engine = create_engine('postgres:///catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


# =========CSRF=============
def create_state():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase)
        for x in range(32))
    session['state'] = state
    return state


def valid_state():
    received_state = request.form['state']
    if received_state != session['state']:
        print("CSRF mismatch", received_state, "!=", session['state'])
        return False
    return True


# =========Index=============
@app.route('/')
def index():
    return render_template('index.html')


# =========Catalogs=============
@app.route('/catalogs/', methods=["GET", "POST"])
def catalogs():
    if request.method == "GET":
        db_session = DBSession()
        catalogs = db_session.query(Catalog).all()
        db_session.close()
        return render_template('catalogs/catalogs.html', catalogs=catalogs)
    elif request.method == "POST":
        db_session = DBSession()
        name = request.form['name']
        catalog = Catalog(name=name)
        db_session.add(catalog)
        db_session.commit()
        db_session.close()
        return redirect(url_for('catalogs'))


@app.route('/catalogs/new/')
def new_catalog():
    return render_template('catalogs/new.html')


@app.route('/catalogs/<int:catalog_id>')
def show_catalog(catalog_id):
    db_session = DBSession()
    items = db_session.query(Item).filter_by(catalog_id=catalog_id).all()
    db_session.close()
    return render_template('catalogs/show.html', items=items,
                           catalog_id=catalog_id)


# =========Items=============
@app.route('/items', methods=['GET', 'POST'])
def items():
    print('idinfo' in session)
    if request.method == "GET":
        db_session = DBSession()
        items = db_session.query(Item).all()
        db_session.close()
        return render_template('items/items.html', items=items)
    elif request.method == "POST":
        db_session = DBSession()
        name = request.form['name']
        description = request.form['description']
        catalog_id = request.form['catalog_id']
        item = Item(name=name, description=description, catalog_id=catalog_id)
        db_session.add(item)
        db_session.commit()
        db_session.close()
        return redirect(url_for('items'))


@app.route('/items/new/')
def new_item():
    db_session = DBSession()
    catalogs = db_session.query(Catalog).all()
    db_session.close()
    return render_template('items/new.html', catalogs=catalogs)


@app.route('/items/<int:item_id>')
def show_item(item_id):
    db_session = DBSession()
    item = db_session.query(Item).filter_by(item_id=item_id).one()
    db_session.close()
    return render_template('items/show.html', item=item)


# =========Login=============
@app.route('/login', methods=["GET", "POST", "DELETE"])
def login():
    if request.method == "GET":
        state = create_state()
        session['state'] = state
        return render_template('login/new.html', state=state)

    if request.method == "POST":
        if not valid_state():
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}

        token = request.form['token']
        client_id = \
            json.loads(open('../secrets/app_secrets.json', 'r').read())['web'][
                'google']["client_id"]
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(),
                                                  client_id)
            session['idinfo'] = idinfo
            if idinfo['iss'] not in ['accounts.google.com',
                                     'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
        except ValueError:
            print("Raised error")
            session['idinfo'] = None
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}

    elif request.method == "DELETE":
        session['idinfo'] = None
        return json.dumps({'success': True}), 200, {
                'ContentType': 'application/json'}


if __name__ == '__main__':
    app.debug = True
    secret_key = \
        json.loads(open('../secrets/app_secrets.json', 'r').read())['app'][
            'secret']
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port=5000)
