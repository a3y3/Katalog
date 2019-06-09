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


@app.route('/')
def index():
    return render_template('index.html')


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
def create_catalog():
    return render_template('catalogs/new.html')


@app.route('/catalogs/<int:catalog_id>')
def show_catalog(catalog_id):
    session = DBSession()
    items = session.query(Item).filter_by(catalog_id=catalog_id).all()
    session.close()
    return render_template('catalogs/show.html', items=catalog_id)


if __name__ == '__main__':
    app.secret_key = "soham"
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
