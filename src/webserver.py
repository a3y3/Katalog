from flask import Flask, render_template, request, redirect, url_for, \
    session, flash, Markup, jsonify
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
MUST_SIGN_IN = "You need to <a href=/login>sign in </a> " \
               "before you perform that action."
CATALOG_DELETED = "Catalog deleted successfully along with all the items in it."
ITEM_DELETED = "Item deleted successfully."
NOT_AUTHORIZED = "You do not have permission to view that resource(s). This " \
                 "could be because you are trying view a resource that you do" \
                 " not own."


# =========CSRF=============
def get_csrf_token():
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
    items_three = db_sesssion.query(Catalog, Item, User).join(
        Item.catalog).join(Item.user).limit(3)
    db_sesssion.close()
    return render_template('index.html', tuple=items_three)


# =========Catalogs=============
@app.route('/catalogs/', methods=["GET", "POST"])
def catalogs():
    """
    GET: Shows all the catalogs available.

    POST: Creates a new catalog.

    :return: template (if GET) and a redirect to catalogs on POST.
    """
    if request.method == "GET":
        db_session = DBSession()
        catalogs_all = db_session.query(Catalog, User).join(Catalog.user)
        db_session.close()
        return render_template('catalogs/catalogs.html', tuple=catalogs_all)

    elif request.method == "POST":
        if not is_signed_in():
            flash(Markup(MUST_SIGN_IN))
            return redirect(request.referrer)
        db_session = DBSession()
        name = request.form['name']
        email = session['idinfo']['email']
        user = db_session.query(User).filter_by(email=email).first()
        catalog = Catalog(name=name, user_id=user.id)
        db_session.add(catalog)
        db_session.commit()
        db_session.close()
        return redirect(url_for('catalogs'))


@app.route('/catalogs/JSON/')
def catalogs_json():
    db_session = DBSession()
    catalogs_all = db_session.query(Catalog).all()
    catalogs_serialized = [i.serialize for i in catalogs_all]
    db_session.close()
    return jsonify(catalogs=catalogs_serialized)


@app.route('/catalogs/new/')
def new_catalog():
    """
    Shows the form for creating a new catalog.

    :return: the appropriate template.
    """
    if not is_signed_in():
        flash(Markup(MUST_SIGN_IN))
        return redirect(request.referrer)
    return render_template('catalogs/new.html')


@app.route('/catalogs/<int:catalog_id>/', methods=['GET', 'PUT', 'DELETE'])
def id_catalog(catalog_id):
    """
    GET: Shows the items in a given catalog.

    PUT: Updates the particular catalog with the values supplied. The operation
    is guaranteed to be idempotent.

    DELETE: Deletes the particular catalog.

    :param catalog_id: the id of the catalog.

    :return: the appropriate template.
    """
    db_session = DBSession()
    catalog = db_session.query(Catalog).filter_by(id=catalog_id).one()

    if request.method == "GET":
        catalogs_all = db_session.query(Catalog, Item, User).join(
            Item.user).join(Item.catalog).filter(
            Item.catalog_id == catalog_id)
        state = get_csrf_token()
        db_session.close()
        return render_template('catalogs/show.html', tuple=catalogs_all,
                               catalog=catalog, state=state)

    elif request.method == "PUT":
        if not valid_state():
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}

        if not is_authorized_catalog(catalog_id):
            flash(NOT_AUTHORIZED)
            return redirect(request.referrer)

        new_name = request.form['name']
        catalog.name = new_name
        db_session.add(catalog)
        db_session.commit()
        db_session.close()
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}

    elif request.method == "DELETE":
        if not valid_state():
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}

        if not is_authorized_catalog(catalog_id):
            flash(NOT_AUTHORIZED)
            return redirect(request.referrer)

        db_session.delete(catalog)
        db_session.commit()
        db_session.close()
        flash(CATALOG_DELETED)
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}


@app.route('/catalogs/<int:catalog_id>/JSON/')
def id_catalog_json(catalog_id):
    db_session = DBSession()
    items_in_catalog = db_session.query(Item).filter(
        Item.catalog_id == catalog_id)
    items_serialized = [i.serialize for i in items_in_catalog]
    db_session.close()
    return jsonify(items=items_serialized)


@app.route('/catalogs/<int:catalog_id>/edit/')
def edit_catalog(catalog_id):
    """
    Displays a page that contains a form for editing a particular catalog.

    :param catalog_id: The ID of the catalog for which the edit page has to be
    displayed.

    :return: the appropriate template.
    """
    if not is_signed_in():
        flash(Markup(MUST_SIGN_IN))
        return redirect(request.referrer)

    if not is_authorized_catalog(catalog_id):
        flash(NOT_AUTHORIZED)
        return redirect(request.referrer)

    db_session = DBSession()
    catalog = db_session.query(Catalog).filter_by(id=catalog_id).one()
    state = get_csrf_token()
    session['state'] = state
    db_session.close()
    return render_template('catalogs/edit.html', catalog=catalog, state=state)


# =========Items=============
@app.route('/items/', methods=['GET', 'POST'])
def items():
    """
    GET: Shows all items
    POST: Creates a new item.
    :return: GET: the appropriate template, POST: redirect to items
    """
    if request.method == "GET":
        db_session = DBSession()
        items_all = db_session.query(Catalog, Item, User).join(
            Item.catalog).join(Item.user)
        db_session.close()
        return render_template('items/items.html', tuple=items_all)

    elif request.method == "POST":
        if not is_signed_in():
            flash(Markup(MUST_SIGN_IN))
            return redirect(request.referrer)

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


@app.route('/items/JSON/')
def items_json():
    """
    JSON endpoint for all the items in the database.

    :return: JSON string containing items' serialized values (@see models.py)
    """
    db_session = DBSession()
    items_all = db_session.query(Item).all()
    items_serialized = [i.serialize for i in items_all]
    db_session.close()
    return jsonify(items=items_serialized)


@app.route('/items/new/')
def new_item():
    """
    Shows the form for creating a new item
    :return: the appropriate template.
    """
    if not is_signed_in():
        flash(Markup(MUST_SIGN_IN))
        return redirect(request.referrer)

    db_session = DBSession()
    catalogs_all = db_session.query(Catalog).all()
    db_session.close()
    return render_template('items/new.html', catalogs=catalogs_all)


@app.route('/items/<int:item_id>/', methods=['GET', 'PUT', 'DELETE'])
def id_item(item_id):
    """
    GET: Shows a particular item.

    PUT: Updates the particular item with the values supplied. The operation
    is guaranteed to be idempotent.

    DELETE: Deletes the particular item.

    :param item_id: the id of the item to be shown.

    :return: the appropriate template.
    """
    db_session = DBSession()
    item = db_session.query(Item).filter_by(id=item_id).one()

    if request.method == "GET":
        item_tuple = db_session.query(Catalog, Item, User).join(Item.catalog) \
            .join(Item.user).filter(Item.id == item_id).one()
        db_session.close()
        return render_template('items/show.html', catalog=item_tuple[0],
                               item=item_tuple[1],
                               user=item_tuple[2])

    elif request.method == "PUT":
        if not valid_state():
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}

        if not is_authorized_item(item_id):
            flash(NOT_AUTHORIZED)
            return redirect(request.referrer)

        new_name = request.form['name']
        new_desc = request.form['description']
        new_catalog_id = request.form['catalog_id']
        item.name = new_name
        item.description = new_desc
        item.catalog_id = new_catalog_id
        db_session.add(item)
        db_session.commit()
        db_session.close()
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}

    elif request.method == "DELETE":
        if not valid_state():
            return json.dumps({'success': False}), 401, {
                'ContentType': 'application/json'}

        if not is_authorized_item(item_id):
            flash(NOT_AUTHORIZED)
            return redirect(request.referrer)

        db_session.delete(item)
        db_session.commit()
        db_session.close()
        flash(ITEM_DELETED)
        return json.dumps({'success': True}), 200, {
            'ContentType': 'application/json'}


@app.route('/items/<int:item_id>/JSON/')
def id_item_json(item_id):
    """
    JSON endpoint for a particular item.

    :param item_id: The ID of the particular item.

    :return: JSON string containing item's serialized value (@see models.py)
    """
    db_session = DBSession()
    item = db_session.query(Item).filter(Item.id == item_id).one()
    item_serialized = [item.serialize]
    db_session.close()
    return jsonify(item=item_serialized)


@app.route('/items/<int:item_id>/edit/')
def edit_item(item_id):
    """
    Displays a page that contains a form for editing a particular item.

    :param item_id: The ID of the item for which the edit page has to be
    displayed.

    :return: the appropriate template.
    """
    if not is_signed_in():
        flash(Markup(MUST_SIGN_IN))
        return redirect(request.referrer)

    if not is_authorized_item(item_id):
        flash(NOT_AUTHORIZED)
        return redirect(request.referrer)

    db_session = DBSession()
    item = db_session.query(Item).filter_by(id=item_id).one()
    catalogs_all = db_session.query(Catalog).all()
    state = get_csrf_token()
    session['state'] = state
    db_session.close()
    return render_template('items/edit.html', item=item, state=state,
                           catalogs=catalogs_all)


# =========Login=============
@app.route('/login/', methods=["GET", "POST", "DELETE"])
def login():
    """
    Handles all the login cases.
    GET: Shows the view containing OAuth providers for logging in.
    POST: Creates a new login session, thereby signing in the user.
    DELETE: Deletes the login session, thereby signing out the user.
    :return: the appropriate template.
    """
    if request.method == "GET":
        state = get_csrf_token()
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
            session.pop('idinfo')
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
    """
    "idinfo" represents the state of the current user, as supplied by Google
    OAuth. If this exists in th session, it MUST mean that the user is signed
    in. Note that it is important to DELETE idinfo from session on logout, and
    not setting it to None.

    :return: True if the user is signed in, False otherwise.
    """
    return 'idinfo' in session


def is_authorized_catalog(catalog_id):
    """
    Checks if the current user is authorized to use privileged actions on a
    particular catalog.

    :param catalog_id: the id of the catalog on which the action is to be
    performed.

    :return: True if the current user if authorized to use privileged actions
    on the particular catalog, False otherwise.
    """
    email = session['idinfo']['email']
    db_session = DBSession()
    user = db_session.query(User).filter_by(email=email).one()
    catalog = db_session.query(Catalog).filter_by(id=catalog_id).one()
    user_catalogs = user.catalogs
    db_session.close()
    return catalog in user_catalogs


def is_authorized_item(item_id):
    """
    Checks if the current user is authorized to use privileged actions on a
    particular item.

    :param item_id: the id of the item on which the action is to be
    performed.

    :return: True if the current user if authorized to use privileged actions
    on the particular item, False otherwise.
    """
    email = session['idinfo']['email']
    db_session = DBSession()
    user = db_session.query(User).filter_by(email=email).one()
    item = db_session.query(Item).filter_by(id=item_id).one()
    user_items = user.items
    db_session.close()
    return item in user_items


# =========Main=============
if __name__ == '__main__':
    app.debug = True
    secret_key = \
        json.loads(open('../secrets/app_secrets.json', 'r').read())['app'][
            'secret']
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port=5000)
