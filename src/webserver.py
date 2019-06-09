from flask import Flask, render_template, request, redirect, url_for, \
    session as login_session
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
    login_session['state'] = state
    return state


# =========Index=============
@app.route('/')
def index():
    return render_template('index.html')


# =========Catalogs=============
@app.route('/catalogs/', methods=["GET", "POST"])
def catalogs():
    if request.method == "GET":
        session = DBSession()
        catalogs = session.query(Catalog).all()
        return render_template('catalogs/catalogs.html', catalogs=catalogs)
    elif request.method == "POST":
        session = DBSession()
        name = request.form['name']
        catalog = Catalog(name=name)
        session.add(catalog)
        session.commit()
        session.close()
        return redirect(url_for('catalogs'))


@app.route('/catalogs/new/')
def new_catalog():
    return render_template('catalogs/new.html')


@app.route('/catalogs/<int:catalog_id>')
def show_catalog(catalog_id):
    session = DBSession()
    items = session.query(Item).filter_by(catalog_id=catalog_id).all()
    session.close()
    return render_template('catalogs/show.html', items=items,
                           catalog_id=catalog_id)


# =========Items=============
@app.route('/items', methods=['GET', 'POST'])
def items():
    if request.method == "GET":
        session = DBSession()
        items = session.query(Item).all()
        return render_template('items/items.html', items=items)
    elif request.method == "POST":
        session = DBSession()
        name = request.form['name']
        description = request.form['description']
        catalog_id = request.form['catalog_id']
        item = Item(name=name, description=description, catalog_id=catalog_id)
        session.add(item)
        session.commit()
        session.close()
        return redirect(url_for('items'))


@app.route('/items/new/')
def new_item():
    session = DBSession()
    catalogs = session.query(Catalog).all()
    return render_template('items/new.html', catalogs=catalogs)


@app.route('/items/<int:item_id>')
def show_item(item_id):
    session = DBSession()
    item = session.query(Item).filter_by(item_id=item_id).one()
    session.close()
    return render_template('items/show.html', item=item)


# =========Login=============
@app.route('/login', methods=["GET", "POST", "DELETE"])
def login():
    if request.method == "GET":
        state = create_state()
        return render_template('login/new.html')
    if request.method == "POST":
        pass
    elif request.method == "DELETE":
        pass


if __name__ == '__main__':
    app.debug = True
    secret_key = \
    json.loads(open('../secrets/app_secrets.json', 'r').read())['app'][
        'secret']
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port=5000)
