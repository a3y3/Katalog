# Katalog
### Overview
Katalog is an app for creating catalogs and items that belong in them. It is designed to scale, with performance in mind at each step and request. For example, the database is never queried from views, avoiding the [n+1 query problem.](https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem-in-orm-object-relational-mapping) 
Further, users who choose to register via Google OAuth can create, edit and delete catalgos and items.

Katalog is live on [Heroku.](https://lit-bayou-96982.herokuapp.com/)

### Why this app?
This app is done as part of Udacity's Full Stack Nanodegree. According to them:
> Modern web applications perform a variety of functions and provide amazing features and utilities to their users; but deep down, it’s really all just creating, reading, updating and deleting data. In this project, you’ll combine your knowledge of building dynamic websites with persistent data storage to create a web application that provides a compelling service to your users.

## How to build
### Pre-requisites
You will need:
- PostgreSQL
- Flask & SQLAlchemy
- Python3

To simplify the installation, simply look for `requirements.txt` in the project root and run `pip install -r requirements.txt`.

## Steps to build
If you want to run on localhost:
- cd to `src/`
- Run using `python3 webserver.py`.

If you want to run a production server like gunicorn: 
- cd to <b>project root</b>.
- Run using `gunicorn --chdir src webserver:app`
