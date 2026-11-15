"""Tiny simulation of stateless API replicas behind one proxy (shared database, no local state)."""
from .db import connect
from . import orders
from .errors import OmniFlowError

class ApiUnavailable(OmniFlowError): pass

class ApiInstance:
    def __init__(self, name, db_path):
        self.name, self.db_path, self.up = name, db_path, True
        self.conn = connect(db_path)
    def place_order(self, token, items, now, idem_key=None):
        if not self.up:
            raise ApiUnavailable(self.name)
        return orders.place_order(self.conn, token, items, now, idem_key)

class Proxy:
    def __init__(self, instances):
        self.instances, self.served_by = instances, []
    def place_order(self, token, items, now, idem_key=None):
        last = None
        for inst in self.instances:
            try:
                oid = inst.place_order(token, items, now, idem_key)
                self.served_by.append(inst.name)
                return oid
            except ApiUnavailable as exc:
                last = exc
        raise last
