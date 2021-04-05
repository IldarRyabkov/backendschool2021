from flask import request, jsonify
from sqlalchemy import exc

from .base import BaseView
from manager.api.schema import (orders_response_schema,
                                OrdersSchema, validate_request)
from manager.db.schema import db, Order, DeliveryHours


class Orders(BaseView):
    URL_PATH = "/orders"
    endpoint = "post_orders"
    methods = ['POST']

    @validate_request(OrdersSchema)
    def post(self):
        # Добавление заказов в базу данных
        for data in request.json["data"]:
            order = Order(data["order_id"], data["weight"], data["region"])
            db.session.add(order)

            for interval in data["delivery_hours"]:
                start, end = interval.split('-')
                dh = DeliveryHours(data["order_id"], start, end)
                db.session.add(dh)

        # Транзакция
        try:
            db.session.commit()
        except exc.IntegrityError:
            msg = "Something went wrong..."
            return msg, 400

        # Успешный ответ
        result = orders_response_schema(request.json["data"])
        return jsonify(result), 201
