from .couriers import Couriers
from .courier import PatchCourier
from .orders import Orders
from .assign import Assign
from .complete import Complete
from .courier_info import CourierInfo


HANDLERS = (
    Couriers, PatchCourier, Orders, Assign, Complete, CourierInfo,
)
