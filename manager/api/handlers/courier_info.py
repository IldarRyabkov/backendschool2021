from flask import jsonify
from sqlalchemy.sql import func

from .base import BaseView
from manager.db.schema import db, Courier, Order
from manager.api.schema import (info_response_schema,
                                validate_request, CourierIdSchema)


class CourierInfo(BaseView):
    URL_PATH = "/couriers/<int:courier_id>"
    endpoint = "get_courier"
    methods = ['GET']

    @staticmethod
    def get_rating(courier_id):
        avg_times = db.session.query(func.avg(Order.lead_time))\
            .filter(Order.completed_by(courier_id))\
            .group_by(Order.region).all()
        t = min([avg_time[0] for avg_time in avg_times])
        rating = (60*60 - min(t, 60*60))/(60*60) * 5
        rating = round(rating, 2)
        return rating

    @validate_request(CourierIdSchema)
    def get(self, courier_id):
        # Получение данных о курьере
        courier = Courier.query.filter_by(id=courier_id).first()
        rating = self.get_rating(courier_id) if courier.earnings > 0 else None

        # Успешный ответ
        result = info_response_schema(courier, rating)
        return jsonify(result), 200
