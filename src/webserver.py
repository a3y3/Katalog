from flask import Flask, render_template, request, redirect, url_for, \
    session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__, template_folder='../views',
            static_folder='../views/static')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.secret_key = "soham"
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
