from flask import request, jsonify
from sqlalchemy import exc
from datetime import datetime


from manager.db.schema import db, Courier, Order
from manager.api.schema import (DATETIME_FORMAT, complete_response_schema,
                                CompleteSchema, validate_request)
from .base import BaseView


class Complete(BaseView):
    URL_PATH = "/orders/complete"
    endpoint = "complete_orders"
    methods = ['POST']

    @validate_request(CompleteSchema)
    def post(self):
        # Завершение заказа
        courier = Courier.get(request.json["courier_id"])
        complete_time = datetime.strptime(request.json["complete_time"],
                                          DATETIME_FORMAT).timestamp()
        order = Order.query.filter(Order.assigned_to(request.json["courier_id"]),
                                   Order.id == request.json["order_id"]).first()

        order.complete(courier.start_time, complete_time)
        courier.start_time = complete_time
        orders = Order.query.filter(Order.assigned_to(courier.id)).all()
        if not orders:
            courier.earnings += courier.salary
            courier.current_weight = 0

        # Транзакция
        try:
            db.session.commit()
        except exc.IntegrityError:
            msg = "Something went wrong..."
            return msg, 400

        # Успешный ответ
        result = complete_response_schema(request.json)
        return jsonify(result), 200
