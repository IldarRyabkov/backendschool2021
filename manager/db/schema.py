from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy import or_, and_
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Courier(db.Model):
    __tablename__ = 'couriers'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)
    current_weight = db.Column(db.Integer, default=0)
    earnings = db.Column(db.Integer, default=0)
    salary = db.Column(db.Integer, default=0)
    assign_time = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.Integer, nullable=True)
    regions = db.relationship("Region", backref='couriers')
    working_hours = db.relationship("WorkingHours", backref='couriers')

    def __init__(self, id, type):
        self.id = id
        self.type = type

    @classmethod
    def get(cls, courier_id):
        return cls.query.filter_by(id=courier_id).first()

    @hybrid_property
    def get_regions(self):
        """"Возвращает список районов работы курьера."""
        regions = db.session.query(Region).filter_by(courier_id=self.id).all()
        return [r.region for r in regions]

    @hybrid_property
    def get_working_hours(self):
        """"Возвращает список интервалов работы(график) курьера."""
        working_hours = db.session.query(WorkingHours)\
            .filter_by(courier_id=self.id).all()
        return ['-'.join((i.start_time, i.end_time)) for i in working_hours]

    @hybrid_property
    def salary_coeff(self):
        """Возвращает коэффициент зарплаты курьера за текущий развоз."""
        return 2 if self.type == "foot" else 5 if self.type == "bike" else 9

    @hybrid_property
    def capacity(self):
        """Возвращает грузоподъемность курьера, в зависимости от его типа."""
        return 10 if self.type == "foot" else 15 if self.type == "bike" else 50

    @hybrid_property
    def overloaded(self):
        """Возвращает, перегружен ли курьер заказами."""
        return self.current_weight > self.capacity

    @hybrid_method
    def update_assignment_data(self, assign_time):
        """Обновляет данные курьера после назначения ему новых заказов."""
        self.start_time = assign_time
        self.assign_time = assign_time
        self.salary = self.salary_coeff * 500


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, db.ForeignKey('couriers.id'), nullable=True)
    weight = db.Column(db.Float)
    region = db.Column(db.Integer)
    status = db.Column(db.String, default="free")
    lead_time = db.Column(db.Integer, nullable=True)
    delivery_hours = db.relationship("DeliveryHours")

    def __init__(self, id, weight, region):
        self.id = id
        self.weight = weight
        self.region = region

    @classmethod
    def get(cls, order_id):
        return cls.query.filter_by(id=order_id).first()

    @hybrid_method
    def assigned_to(self, courier_id):
        """Возвращает, назначен ли заказ данному курьеру"""
        return and_(self.status == "assigned", self.courier_id == courier_id)

    @hybrid_method
    def completed_by(self, courier_id):
        """Возвращает, был ли заказ выполнен данным курьером"""
        return and_(self.status == "completed", self.courier_id == courier_id)

    @hybrid_method
    def available(self, regions):
        """Возвращает, доступен ли заказ для выдачи
        курьеру с данными районами работы"""
        return and_(self.status == "free", or_(*[self.region == r for r in regions]))

    @hybrid_property
    def free(self):
        """Делает заказ свободным для выдачи другим курьерам"""
        self.courier_id = None
        self.status = "free"

    @hybrid_method
    def assign_to(self, courier_id):
        """Назначает заказ данному курьеру"""
        self.status = "assigned"
        self.courier_id = courier_id

    @hybrid_method
    def complete(self, start_time, end_time):
        """Обновляет данные заказа после его выполнения."""
        self.status = "completed"
        self.lead_time = end_time - start_time

    @hybrid_method
    def outside_courier_regions(self, courier_id, regions):
        """Возвращает, является ли заказ недействительным для данного курьера
        после обновления его районов работы.
        """
        return and_(self.courier_id == courier_id,
                    *[self.region != r for r in regions])


class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    courier_id = db.Column(db.Integer, db.ForeignKey('couriers.id'))
    region = db.Column(db.Integer)

    def __init__(self, courier_id, region):
        self.courier_id = courier_id
        self.region = region


class WorkingHours(db.Model):
    __tablename__ = 'workinghours'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    courier_id = db.Column(db.Integer, db.ForeignKey('couriers.id'))
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)

    def __init__(self, courier_id, start_time, end_time):
        self.courier_id = courier_id
        self.start_time = start_time
        self.end_time = end_time

    @classmethod
    def get(cls, courier_id):
        return cls.query.filter_by(courier_id=courier_id).all()


class DeliveryHours(db.Model):
    __tablename__ = 'deliveryhours'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)

    def __init__(self, order_id, start_time, end_time):
        self.order_id = order_id
        self.start_time = start_time
        self.end_time = end_time

    @hybrid_method
    def intersects_interval(self, start, end):
        """Возвращает, пересекается ли время для приема
        заказа с данным интервалом."""
        return or_(and_(self.start_time <= start, start < self.end_time),
                   and_(self.start_time < end, end <= self.end_time),
                   and_(self.start_time >= start, end >= self.end_time))

    @hybrid_method
    def intersects(self, working_hours):
        """Возвращает, пересекается ли время для приема
        заказа с графиком работы курьера."""
        if not working_hours:
            return False
        return or_(*[self.intersects_interval(wh.start_time, wh.start_time)
                     for wh in working_hours])
