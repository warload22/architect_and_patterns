import threading


class UnitOfWork:

    current = threading.local()

    def __init__(self):
        self.new_objects = []
        self.dirty_objects = []
        self.removed_objects = []
        self.registry = None

    def set_registry(self, registry):
        self.registry = registry

    def register_new(self, obj):
        self.new_objects.append(obj)

    def register_dirty(self, obj):
        self.dirty_objects.append(obj)

    def register_removed(self, obj):
        self.removed_objects.append(obj)

    def commit(self):
        self.insert_new()
        self.update_dirty()
        self.delete_removed()

    def insert_new(self):
        for obj in self.new_objects:
            self.registry.get_mapper(obj).insert(obj)
        self.new_objects = []

    def update_dirty(self):
        for obj in self.dirty_objects:
            self.registry.get_mapper(obj).update(obj)
        self.dirty_objects = []

    def delete_removed(self):
        for obj in self.removed_objects:
            self.registry.get_mapper(obj).delete(obj)
        self.removed_objects = []

    @staticmethod
    def new_current():
        __class__.set_current(UnitOfWork())

    @classmethod
    def set_current(cls, unit_of_work):
        cls.current.unit_of_work = unit_of_work

    @classmethod
    def get_current(cls):
        return cls.current.unit_of_work
