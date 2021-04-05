"""
Модуль содержит схемы для валидации данных в запросах и ответах.

Схемы валидации запросов используются в бою для валидации данных отправленных
клиентами.
"""
from marshmallow import Schema, ValidationError, validates, validates_schema, pre_load
from marshmallow.fields import Nested, Int, Str, List, Float
from marshmallow.validate import Range
from flask import request, jsonify
from re import fullmatch
from datetime import datetime

from manager.db.schema import Courier, Order


INTERVAL_PATTERN = '\d\d:\d\d-\d\d:\d\d'
DATETIME_PATTERN = '\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d\d\d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


def validate_interval(interval):
    if not fullmatch(INTERVAL_PATTERN, interval):
        raise ValidationError("Not a valid time format.")

    start_time, end_time = interval.split('-')
    start_time = datetime.strptime(start_time, '%H:%M')
    end_time = datetime.strptime(end_time, '%H:%M')
    if start_time >= end_time:
        raise ValidationError("Start-time must be less than end-time.")


class PatchCourierSchema(Schema):
    """Схема для валидации запроса на изменение данных курьера."""
    courier_id = Int(validate=Range(min=1), strict=True, required=True)
    courier_type = Str()
    regions = List(Int(validate=Range(min=1), strict=True))
    working_hours = List(Str(validate=validate_interval))

    @validates('courier_type')
    def validate_courier_type(self, courier_type: str):
        if courier_type not in ("foot", "car", "bike"):
            raise ValidationError("Courier type is incorrect!")

    @validates('regions')
    def validate_courier_regions(self, regions: list):
        if len(regions) != len(set(regions)):
            raise ValidationError("Not all regions are unique!")

    @validates('courier_id')
    def validate_courier_id(self, courier_id: int):
        if not Courier.get(courier_id):
            raise ValidationError("Courier with given id doesn't exist!")


class CourierSchema(PatchCourierSchema):
    """Схема для валидации данных курьера в запросе на добавление курьеров."""
    courier_type = Str(required=True)
    regions = List(Int(validate=Range(min=1), strict=True), required=True)
    working_hours = List(Str(validate=validate_interval), required=True)

    @validates('courier_id')
    def validate_courier_id(self, courier_id: int):
        if Courier.get(courier_id):
            raise ValidationError("Courier with given id already exists!")


class CouriersSchema(Schema):
    """Схема для валидации запроса на добавление новых курьеров. """
    data = List(Nested(CourierSchema()), required=True)

    @pre_load
    def validate_input(self, input_data, **kwargs):
        """Проверяет, что гарантии на входные данные не нарушены."""
        if not isinstance(input_data, dict):
            ValidationError("Input data must be a dictionary.")

        if "data" not in input_data:
            raise ValidationError("Input data must have a 'data' key.")

        if not isinstance(input_data["data"], list):
            raise ValidationError("Value of the 'data' key must be a list.")

        if any(not isinstance(courier, dict) or "courier_id" not in courier
               for courier in input_data["data"]):
            raise ValidationError("Couriers input data is invalid.")

        courier_ids = [courier["courier_id"] for courier in input_data["data"]]
        if len(courier_ids) != len(set(courier_ids)):
            raise ValidationError("Some of given couriers have same id!")

        return input_data

    def handle_error(self, exc, data, **kwargs):
        """Возвращает сообщение с описанием всех некорректных полей запроса.
        Полагается, что ГАРАНТИРОВАННО поле "data" присутствует в запросе,
        поле courier_id присутствует в каждом элементе в "data",
        и все ID курьеров уникальны в пределах запроса.
        """
        if "_schema" in exc.messages:
            # Гарантии на входные данные нарушены.
            # В этом случае просто возвращаются все ошибки, пойманные схемой.
            raise exc

        error_message = {"validation_error": {"couriers": []}}
        for msg_index in exc.messages["data"]:
            courier_data = exc.messages["data"][msg_index]
            courier_id = data["data"][msg_index]["courier_id"]
            courier_data.update({"id": courier_id})
            error_message["validation_error"]["couriers"].append(courier_data)
        raise ValidationError(error_message)


class OrderSchema(Schema):
    """Схема для валидации данных курьера в запросе на добавление курьеров."""
    order_id = Int(validate=Range(min=1), strict=True, required=True)
    weight = Float(validate=Range(min=0.01, max=50), required=True)
    region = Int(validate=Range(min=1), strict=True, required=True)
    delivery_hours = List(Str(validate=validate_interval), required=True)

    @validates('order_id')
    def validate_order_id(self, order_id: int):
        if Order.get(order_id):
            raise ValidationError("Order with given id already exists!")


class OrdersSchema(Schema):
    """Схема для валидации запроса на добавление новых заказов."""
    data = List(Nested(OrderSchema(), required=True))

    @pre_load
    def validate_input(self, input_data, **kwargs):
        """Проверяет, что гарантии на входные данные не нарушены."""
        if not isinstance(input_data, dict):
            ValidationError("Input data must be a dictionary.")

        if "data" not in input_data:
            raise ValidationError("Input data must have a 'data' key.")

        if not isinstance(input_data["data"], list):
            raise ValidationError("Value of the 'data' key must be a list.")

        if any(not isinstance(order, dict) or "order_id" not in order
               for order in input_data["data"]):
            raise ValidationError("Orders input data is invalid.")

        order_ids = [order["order_id"] for order in input_data["data"]]
        if len(order_ids) != len(set(order_ids)):
            raise ValidationError("Some of given orders have same id!")

        return input_data

    def handle_error(self, exc, data, **kwargs):
        """Возвращает сообщение с описанием всех некорректных полей запроса.
        Полагается, что ГАРАНТИРОВАННО поле "data" присутствует в запросе data,
        поле order_id присутствует в каждом элементе в "data",
        и все ID заказов уникальны в пределах запроса.
        """
        if "_schema" in exc.messages:
            # Гарантии на входные данные нарушены.
            # В этом случае просто возвращаются все ошибки, пойманные схемой.
            raise exc

        error_message = {"validation_error": {"orders": []}}
        for msg_index in exc.messages["data"]:
            order_data = exc.messages["data"][msg_index]
            order_id = data["data"][msg_index]["order_id"]
            order_data.update({"id": order_id})
            error_message["validation_error"]["orders"].append(order_data)
        raise ValidationError(error_message)


class CourierIdSchema(Schema):
    courier_id = Int(validate=Range(min=1), strict=True, required=True)

    @validates('courier_id')
    def validate_courier_id(self, courier_id: int):
        if not Courier.get(courier_id):
            raise ValidationError("Courier with given id doesn't exist!")


class CompleteSchema(Schema):
    order_id = Int(validate=Range(min=1), strict=True, required=True)
    courier_id = Int(validate=Range(min=1), strict=True, required=True)
    complete_time = Str(required=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        courier = Courier.get(data["courier_id"])
        if not courier:
            raise ValidationError("Courier with given id doesn't exist!")

        if not Order.get(data["order_id"]):
            raise ValidationError("Order with given id doesn't exist!")

        order = Order.query.filter(Order.assigned_to(data["courier_id"]),
                                   Order.id == data["order_id"]).first()
        if not order:
            raise ValidationError("No assigned order with given input data!")

        if not fullmatch(DATETIME_PATTERN, data["complete_time"]):
            raise ValidationError("Time is not in the correct format!")

        end_time = datetime.strptime(data["complete_time"], DATETIME_FORMAT).timestamp()
        if end_time < courier.start_time:
            raise ValidationError("Order end-time can't be less than start-time!")


def patch_response_schema(courier):
    return {"courier_id": courier.id,
            "courier_type": courier.type,
            "regions": courier.get_regions,
            "working_hours": courier.get_working_hours}


def orders_response_schema(data):
    return {"orders": [{"id": d["order_id"]} for d in data]}


def couriers_response_schema(data):
    return {"couriers": [{"id": d["courier_id"]} for d in data]}


def assign_response_schema(assign_time, orders):
    result = {"orders": [{"id": order.id} for order in orders]}
    if orders:
        assign_time = datetime.fromtimestamp(assign_time)
        result["assign_time"] = assign_time.strftime(DATETIME_FORMAT)[:-3]
    return result


def complete_response_schema(data):
    return {"order_id": data["order_id"]}


def info_response_schema(courier, rating):
    result = {"courier_id": courier.id,
              "courier_type": courier.type,
              "regions": courier.get_regions,
              "working_hours": courier.get_working_hours,
              "earnings": courier.earnings
              }
    if rating is not None:
        result["rating"] = rating
    return result


def validate_request(request_schema):
    """Декоратор для валидации входных данных по заданной схеме."""
    def decorator(original):
        def wrapper(*args, **kwargs):
            data = request.json if request.json else dict()
            if isinstance(data, dict):
                data.update(kwargs)
            try:
                request_schema().load(data)
            except ValidationError as err:
                return jsonify(err.messages), 400

            return original(*args, **kwargs)

        return wrapper

    return decorator
