from flask import request, jsonify
from sqlalchemy import exc

from .base import BaseView
from manager.db.schema import db, Courier, Region, WorkingHours
from manager.api.schema import (couriers_response_schema,
                                validate_request, CouriersSchema)


class Couriers(BaseView):
    URL_PATH = "/couriers"
    endpoint = "post_couriers"
    methods = ['POST']

    @validate_request(CouriersSchema)
    def post(self):
        # Добавление курьеров в базу данных
        for data in request.json["data"]:
            courier = Courier(data["courier_id"], data["courier_type"])
            db.session.add(courier)

            for r in data["regions"]:
                region = Region(data["courier_id"], r)
                db.session.add(region)

            for interval in data["working_hours"]:
                start, end = interval.split('-')
                working_hours = WorkingHours(data["courier_id"], start, end)
                db.session.add(working_hours)

        # Транзакция
        try:
            #courier = Courier(id=1, type="foot")
            #db.session.add(courier)
            db.session.commit()
        except exc.IntegrityError:
            msg = "Something went wrong..."
            return msg, 400

        # Успешный ответ
        result = couriers_response_schema(request.json["data"])
        return jsonify(result), 201
