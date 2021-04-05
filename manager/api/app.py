#!flask/bin/python
# -*- coding: utf-8 -*-
from flask import Flask


from manager.db.schema import db
from manager.api.handlers import HANDLERS
from definitions import DATABASE_PATH


def create_app(database_path=DATABASE_PATH):
    """Создает экземпляр приложения, готового к запуску. """
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % database_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Подключение на старте к базе данных
    db.init_app(app)

    #with app.app_context():
    #    db.create_all()

    # Регистрация обработчиков
    for handler in HANDLERS:
        app.add_url_rule(handler.URL_PATH,
                         view_func=handler.as_view(handler.endpoint),
                         methods=handler.methods)

    return app
