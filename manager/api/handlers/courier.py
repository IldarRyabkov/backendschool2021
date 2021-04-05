from flask import request, jsonify
from sqlalchemy import and_
from sqlalchemy import exc

from .base import BaseView
from manager.api.schema import (patch_response_schema,
                                PatchCourierSchema, validate_request)
from manager.db.schema import (db, Order, Region, WorkingHours,
                               DeliveryHours, Courier)


class PatchCourier(BaseView):
    URL_PATH = "/couriers/<int:courier_id>"
    endpoint = "patch_courier"
    methods = ['PATCH']

    @staticmethod
    def patch_courier_type(courier, courier_type):
        """Обновляет тип курьера, снимает с курьера заказы,
        которые он уже не сможет развести после обновления типа,
        и делает их доступными для выдачи другим курьерам.
        """
        courier.type = courier_type

        # Снимаем с курьера заказы, пока он не перстанет быть перегруженным
        assigned_orders_sorted = db.session.query(Order) \
            .filter(Order.assigned_to(courier.id))\
            .order_by(Order.weight.desc())
        for order in assigned_orders_sorted:
            if not courier.overloaded:
                break
            courier.current_weight -= order.weight
            order.courier_id = None
            order.status = "free"

    @staticmethod
    def patch_regions(courier, regions):
        """Обновляет районы курьера, снимает с курьера заказы,
        которые он уже не сможет развести после обновления районов,
        и делает их доступными для выдачи другим курьерам.
        """
        # Удаление старых районов, добавление новых
        db.session.query(Region).filter_by(courier_id=courier.id).delete()
        for region in regions:
            db.session.add(Region(courier.id, region))

        # Снятие с курьера неактуальных заказов
        invalid_orders = db.session.query(Order) \
            .filter(Order.outside_courier_regions(courier.id, regions),
                    Order.assigned_to(courier.id)).all()
        for order in invalid_orders:
            order.courier_id = None
            order.status = "free"

    @staticmethod
    def patch_working_hours(courier, working_hours):
        """Обновляет график работы курьера, снимает с курьера заказы,
        которые он уже не сможет развести после обновления графика,
        и делает их доступными для выдачи другим курьерам.
        """
        # Удаление старого графика, добавление нового
        db.session.query(WorkingHours).filter_by(courier_id=courier.id).delete()
        for wh in working_hours:
            start, end = wh.split('-')
            interval = WorkingHours(courier.id, start, end)
            db.session.add(interval)

        # Снятие с курьера неактуальных заказов
        working_hours = WorkingHours.get(courier.id)

        valid_orders = db.session.query(Order) \
            .join(DeliveryHours,
                  and_(DeliveryHours.order_id == Order.id,
                       DeliveryHours.intersects(working_hours)))\
            .filter(Order.assigned_to(courier.id)).all()

        orders = Order.query.filter(Order.assigned_to(courier.id))

        invalid_orders = [order for order in orders if order not in valid_orders]
        for order in invalid_orders:
            order.courier_id = None
            order.status = "free"

    @validate_request(PatchCourierSchema)
    def patch(self, courier_id):
        # Изменение данных курьера
        courier = Courier.get(courier_id)
        if "courier_type" in request.json:
            self.patch_courier_type(courier, request.json["courier_type"])
        if "regions" in request.json:
            self.patch_regions(courier, request.json["regions"])
        if "working_hours" in request.json:
            self.patch_working_hours(courier, request.json["working_hours"])

        # Транзакция
        try:
            db.session.commit()
        except exc.IntegrityError:
            msg = "Something went wrong..."
            return msg, 400

        # Успешный ответ
        result = patch_response_schema(courier)
        return jsonify(result), 200
