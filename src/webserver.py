from flask import Flask, render_template, request, redirect, url_for, \
    session, flash, Markup
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

# =========Constants=============
MUST_SIGNED_IN = "You need to <a href=/login>sign in </a> " \
                 "before you perform that action."


# =========CSRF=============
def create_state():
    """
    Creates a CSRF token as a mixture of upper and lowercase symbols.
    :return: the generated token
    """
    state = ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase)
        for _ in range(32))
    session['state'] = state
    return state


def valid_state():
    """
    Checks if the received CSRF token matches the one in session.
    :return: True if the state is valid, False if there's a CSRF token mismatch.
    """
    received_state = request.form['state']
    if received_state != session['state']:
        print("CSRF mismatch", received_state, "!=", session['state'])
        return False
    return True


# =========Users=============
def create_user():
    """
    Creates a new User if one doesn't exist yet. Lookup is performed against
    User.email, an indexed column.
    :return: None
    """
    email = session['idinfo']['email']
    db_session = DBSession()
    user = db_session.query(User).filter_by(email=email).first()
    if user is None:
        user = User(email=email)
        db_session.add(user)
        db_session.commit()
    db_session.close()


# =========Index=============
@app.route('/')
def index():
    """
    Displays the index page, which lists some items on the home screen.
    :return: the appropriate template.
    """
    db_sesssion = DBSession()
    items_three = db_sesssion.query(Item).limit(3)
    db_sesssion.close()
    return render_template('index.html', items=items_three)


# =========Catalogs=============
@app.route('/catalogs/', methods=["GET", "POST"])
def catalogs():
    """
    GET: Shows all the catalogs available
    POST: Creates a new catalog
    :return: template (if GET) and a redirect to catalogs on POST.
    """
    if request.method == "GET":
        db_session = DBSession()
        catalogs_all = db_session.query(Catalog, User).join(User.catalogs)
        db_session.close()
        return render_template('catalogs/catalogs.html', tuple=catalogs_all)
    elif request.method == "POST":
        db_session = DBSession()
        name = request.form['name']
        email = session['idinfo']['email']
        user = db_session.query(User).filter_by(email=email).first()
        catalog = Catalog(name=name, user_id=user.id)
        db_session.add(catalog)
        db_session.commit()
        db_session.close()
        return redirect(url_for('catalogs'))


@app.route('/catalogs/new/')
def new_catalog():
    """
    Shows the form for creating a new catalog
    :return: the appropriate template.
    """
    if not is_signed_in():
        flash(Markup(MUST_SIGNED_IN))
        return redirect(request.referrer)
    return render_template('catalogs/new.html')


@app.route('/catalogs/<int:catalog_id>')
def show_catalog(catalog_id):
    """
    Shows the items in a given catalog.
    :param catalog_id: the id of the catalog to be displayed.
    :return: the appropriate template.
    """
    db_session = DBSession()
    items_catalog = db_session.query(Item, Catalog, User).filter_by(
        catalog_id=catalog_id).all()
    db_session.close()
    return render_template('catalogs/show.html', items=items_catalog,
                           catalog_id=catalog_id)


# =========Items=============
@app.route('/items', methods=['GET', 'POST'])
def items():
    """
    GET: Shows all items
    POST: Creates a new item.
    :return: GET: the appropriate template, POST: redirect to items
    """
    print('idinfo' in session)
    if request.method == "GET":
        db_session = DBSession()
        items_all = db_session.query(Item, Catalog, User).join(Catalog, User)
        db_session.close()
        return render_template('items/items.html', items=items_all)
    elif request.method == "POST":
        db_session = DBSession()
        name = request.form['name']
        description = request.form['description']
        catalog_id = request.form['catalog_id']
        email = session['idinfo']['email']
        user = db_session.query(User).filter_by(email=email).first()
        item = Item(name=name, description=description, catalog_id=catalog_id,
                    user_id=user.id)
        db_session.add(item)
        db_session.commit()
        db_session.close()
        return redirect(url_for('items'))


@app.route('/items/new/')
def new_item():
    """
    Shows the form for creating a new item
    :return: the appropriate template.
    """
    db_session = DBSession()
    catalogs_all = db_session.query(Catalog).all()
    db_session.close()
    return render_template('items/new.html', catalogs=catalogs_all)


@app.route('/items/<int:item_id>')
def show_item(item_id):
    """
    Shows a particular item.
    :param item_id: the id of the item to be shown.
    :return: the appropriate template.
    """
    db_session = DBSession()
    item, user = db_session.query(Item, User).join(User).filter_by(
        id=item_id).one()
    db_session.close()
    return render_template('items/show.html', item=item, user=user)


# =========Login=============
@app.route('/login', methods=["GET", "POST", "DELETE"])
def login():
    """
    Handles all the login cases.
    GET: Shows the view containing OAuth providers for logging in.
    POST: Creates a new login session, thereby signing in the user.
    DELETE: Deletes the login session, thereby signing out the user.
    :return: the appropriate template.
    """
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
        create_user()
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}

    elif request.method == "DELETE":
        session.pop("idinfo")
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}


def is_signed_in():
    return 'idinfo' in session


# =========Test Routes=============
@app.route('/debug/test')
def test():
    email = session['idinfo']['email']
    db_session = DBSession()
    user = db_session.query(User).filter_by(email=email).first()
    catalogs_all = user.catalogs
    output = ""
    for c in catalogs_all:
        output += c.name
    db_session.close()
    return output


# =========Main=============
if __name__ == '__main__':
    app.debug = True
    secret_key = \
        json.loads(open('../secrets/app_secrets.json', 'r').read())['app'][
            'secret']
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port=5000)
