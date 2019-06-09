from flask import Flask, render_template, request, redirect, url_for, \
    session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, Item, Catalog
from google.oauth2 import id_token
from google.auth.transport import requests

app = Flask(__name__, template_folder='../views',
            static_folder='../views/static')

engine = create_engine('postgres:///catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


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
        user_id = request.form['user_id']
        item = Item(name=name, description=description, catalog_id=catalog_id,
                    user_id=user_id)
        session.add(item)
        session.commit()
        session.close()
        return redirect(url_for('items'))


@app.route('/items/new/')
def new_item():
    return render_template('items/new.html')


@app.route('/items/<int:item_id>')
def show_item(item_id):
    session = DBSession()
    item = session.query(Item).filter_by(item_id=item_id).one()
    session.close()
    return render_template('items/show.html', item=item)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)