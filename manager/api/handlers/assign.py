from flask import request, jsonify
from sqlalchemy import and_
from sqlalchemy import exc
from time import time

from .base import BaseView
from manager.db.schema import db, Courier, DeliveryHours, Order, WorkingHours
from manager.api.schema import (assign_response_schema,
                                CourierIdSchema, validate_request)


class Assign(BaseView):
    URL_PATH = "/orders/assign"
    endpoint = "assign_orders"
    methods = ['POST']

    @staticmethod
    def get_available_orders(courier):
        """Возвращает список заказов, доступных для выдачи данному курьеру."""
        working_hours = WorkingHours.get(courier.id)
        available_orders = db.session.query(Order) \
            .join(DeliveryHours,
                  and_(DeliveryHours.order_id == Order.id,
                       DeliveryHours.intersects(working_hours)))\
            .filter(Order.available(courier.get_regions))\
            .order_by(Order.weight).all()
        return available_orders

    @staticmethod
    def assign_orders(courier, available_orders):
        """Назначает курьеру максимальное количество заказов
        и возвращает список этих заказов."""
        orders = []
        for order in available_orders:
            if courier.current_weight + order.weight > courier.capacity:
                break
            order.assign_to(courier.id)
            courier.current_weight += order.weight
            orders.append(order)
        return orders

    @validate_request(CourierIdSchema)
    def post(self):
        # Назначение заказов
        courier = Courier.get(request.json["courier_id"])
        orders = Order.query.filter(Order.assigned_to(courier.id)).all()
        if orders:
            assigned_orders = orders
        else:
            available_orders = self.get_available_orders(courier)
            assigned_orders = self.assign_orders(courier, available_orders)
            if assigned_orders:
                courier.update_assignment_data(time())

        # Транзакция
        try:
            db.session.commit()
        except exc.IntegrityError:
            msg = "Something went wrong..."
            return msg, 400

        # Успешный ответ
        result = assign_response_schema(courier.assign_time, assigned_orders)
        return jsonify(result), 200
