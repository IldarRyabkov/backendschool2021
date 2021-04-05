from flask.views import MethodView


class BaseView(MethodView):
    URL_PATH = ""
    endpoint = ""
    methods = []
