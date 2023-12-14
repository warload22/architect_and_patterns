import os
import abc
import sqlite3
from copy import deepcopy
from jsonpickle import dumps
from settings import BASE_DIR, DB_PATH
from db.unit_of_work import UnitOfWork


class Observer(metaclass=abc.ABCMeta):

    def __init__(self, user):
        self.subject = None
        self.user = user

    @abc.abstractmethod
    def update(self, param, old, new):
        pass


class EmailObserver(Observer):

    def update(self, param, old, new):
        print(f'EMAIL (to {self.user.username}) >>> Course {self.subject.name}, {param} is changed from {old} to {new}')


class SMSObserver(Observer):

    def update(self, param, old, new):
        print(f'SMS (to {self.user.username}) >>> Course {self.subject.name}, {param} is changed from {old} to {new}')


class Subject:

    def __init__(self):
        self.observers = []

    def attach(self, observer):
        observer.subject = self
        self.observers.append(observer)

    def detach(self, observer):
        observer.subject = None
        self.observers.remove(observer)

    def notify(self, state, old, new):
        for observer in self.observers:
            observer.update(state, old, new)


class DomainObject:

    def mark_new(self):
        UnitOfWork.get_current().register_new(self)

    def mark_dirty(self):
        UnitOfWork.get_current().register_dirty(self)

    def mark_removed(self):
        UnitOfWork.get_current().register_removed(self)


class Category(DomainObject):

    def __init__(self, name: str, category=None):
        self.name = name
        self.courses = []
        self.subcategories = []
        self.category = category

    @property
    def courses_count(self):
        return len(self.courses)

    @property
    def get_category(self):
        return self.category.name if self.category else '-'

    @property
    def get_category_id(self):
        return self.category.id if self.category else -1


class Course(Subject, DomainObject):

    def __init__(self, name: str, category):
        self.name = name
        self.category = category
        self.users = {'students': [], 'teachers': [], 'admins': []}
        super().__init__()

    def __str__(self):
        return self.name

    @property
    def category_name(self):
        return self.category.name

    @property
    def category_id(self):
        return self.category.id

    def clone(self):
        return deepcopy(self)

    def add_observer(self, user, method: str = 'email'):
        if method.lower() == 'sms':
            observer = SMSObserver(user)
        else:
            observer = EmailObserver(user)
        self.attach(observer)

    @property
    def student_count(self):
        return len(self.users['students'])


class OfflineCourse(Course):

    __slots__ = ('address', )

    def __init__(self, address: str, *args):
        super().__init__(*args)
        self.address = address
        self.type_ = 'offline'


class OnlineCourse(Course):

    __slots__ = ('platform', )

    def __init__(self, platform: str, *args):
        super().__init__(*args)
        self.platform = platform
        self.type_ = 'online'


class CourseFactory:

    types = {
        'offline': OfflineCourse,
        'online': OnlineCourse
    }

    types_slots = {
        'offline': OfflineCourse.__slots__,
        'online': OnlineCourse.__slots__
    }

    @classmethod
    def create(cls, type_: str, *args, **kwargs):
        return cls.types[type_](*args, **kwargs)


class User(DomainObject):

    def __init__(self, type_: str, username: str):
        self.username = username
        self.type_ = type_
        self.courses = []

    @property
    def course_count(self):
        return len(self.courses)


class Student(User):
    pass


class Teacher(User):
    pass


class Admin(User):
    pass


class UserFactory:

    types = {
        'student': Student,
        'teacher': Teacher,
        'admin': Admin
    }

    @classmethod
    def create(cls, type_: str, *args, **kwargs):
        return cls.types[type_](type_, *args, **kwargs)


class Engine:

    @staticmethod
    def create_category(name: str, parent_category=None):
        return Category(name, parent_category)

    @staticmethod
    def create_course(type_: str, *args, **kwargs):
        return CourseFactory.create(type_, *args, **kwargs)

    @staticmethod
    def create_user(type_: str, username: str):
        return UserFactory.create(type_, username)

    @staticmethod
    def create_course_user(course_id: int, user_id: int):
        return CourseUser(course_id, user_id)

    @staticmethod
    def get_courses_types():
        return CourseFactory.types.keys()

    @staticmethod
    def get_users_types():
        return UserFactory.types.keys()

    @staticmethod
    def get_courses_slots():
        return CourseFactory.types_slots


class CategoryMapper:

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.table_name = 'categories'

    def construct(self, id_, name):
        category = Category(name)
        category.id = id_
        category.courses = self.get_courses_ids(id_)
        category.subcategories = self.get_subcategories_ids(id_)
        return category

    def all(self):
        statement = f"SELECT * FROM {self.table_name}"
        self.cursor.execute(statement)
        result = []
        primaries = []
        categories = {}
        for cat in self.cursor.fetchall():
            id_, name, category_id = cat
            category = self.construct(id_, name)
            if not category_id:
                primaries.append(id_)
            categories[id_] = category
        self._sort_algo(primaries, result, categories)
        return result

    def _sort_algo(self, ids, result, categories, parent=None):
        for id_ in ids:
            category = categories[id_]
            category.category = parent
            result.append(category)
            self._sort_algo(category.subcategories, result, categories, category)

    def find_by_id(self, id_):
        statement = f"SELECT name, category_id FROM {self.table_name} WHERE id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchone()

        if result:
            name, category_id = result
            category = self.construct(id_, name)
            if category_id:
                category.category = self.find_by_id(category_id)
            return category
        raise Exception(f'record with id={id_} not found')

    def find_by_ids(self, ids):
        statement = f"SELECT id, name, category_id FROM {self.table_name} WHERE id IN ({', '.join(ids)})"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()

        categories = []
        for cat in result:
            id_, name, category_id = cat
            category = self.construct(id_, name)
            if category_id:
                category.category = self.find_by_id(category_id)
            categories.append(category)
        return categories

    def get_courses_ids(self, id_):
        statement = f"SELECT id FROM courses WHERE category_id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()
        return list(map(lambda x: x[0], result))

    def get_subcategories_ids(self, id_):
        statement = f"SELECT id FROM categories WHERE category_id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()
        return list(map(lambda x: x[0], result))

    def insert(self, obj):
        category_id = "NULL" if obj.category is None else obj.category.id
        statement = f"INSERT INTO {self.table_name} (name, category_id) " \
                    f"VALUES ('{obj.name}', {category_id})"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def update(self, obj):
        category_id = f"{obj.category.id}" if obj.category else "NULL"
        print(category_id)
        statement = f"UPDATE {self.table_name} " \
                    f"SET name='{obj.name}', category_id={category_id} " \
                    f"WHERE id={obj.id}"
        print(statement)
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def delete(self, obj):
        self.cursor.execute('PRAGMA foreign_keys = on')
        statement = f"DELETE FROM {self.table_name} WHERE id={obj.id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)


class CourseMapper:

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.table_name = 'courses'

    def construct(self, id_, name, category, type_, address, platform):
        other_params = {'address': address, 'platform': platform}
        slots = CourseFactory.types_slots[type_]
        params = []
        for slot in slots:
            params.append(other_params[slot])
        course = CourseFactory.create(type_, *params, name, category)
        course.id = id_
        course.users = self.get_users_ids(id_)
        return course

    def all(self):
        statement = f"SELECT * FROM {self.table_name}"
        self.cursor.execute(statement)
        result = []
        categories = {}
        for course in self.cursor.fetchall():
            id_, name, category_id, type_, address, platform = course
            try:
                category = categories[category_id]
            except KeyError:
                category = CategoryMapper(self.connection).find_by_id(category_id)
                categories[category_id] = category
            course = self.construct(id_, name, category, type_, address, platform)
            result.append(course)
        return result

    def find_by_id(self, id_):
        statement = f"SELECT name, category_id, type, address, platform FROM {self.table_name} WHERE id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchone()

        if result:
            name, category_id, type_, address, platform = result
            category = CategoryMapper(self.connection).find_by_id(category_id)
            course = self.construct(id_, name, category, type_, address, platform)
            return course
        raise Exception(f'record with id={id_} not found')

    def find_by_ids(self, ids):
        statement = f"SELECT id, name, category_id, type, address, platform FROM {self.table_name} " \
                    f"WHERE id IN ({', '.join(ids)})"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()

        courses = []
        for course in result:
            id_, name, category_id, type_, address, platform = course
            category = CategoryMapper(self.connection).find_by_id(category_id)
            course = self.construct(id_, name, category, type_, address, platform)
            courses.append(course)
        return courses

    def get_users_ids(self, id_):
        statement = f"SELECT user_id, type FROM course_user JOIN users ON id=user_id WHERE course_id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()
        users = {'students': [], 'teachers': [], 'admins': []}
        for user in result:
            users[f'{user[1]}s'].append(user[0])
        return users

    def insert(self, obj):
        slots = obj.__slots__
        statement = f"INSERT INTO {self.table_name} (name, type, category_id, {' ,'.join([*slots])}) " \
                    f"VALUES ('{obj.name}',  '{obj.type_}', {obj.category.id}, '" + \
                    ", '".join([getattr(obj, slot) for slot in slots]) + "')"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def update(self, obj):
        slots = obj.__slots__
        statement = f"UPDATE {self.table_name} SET name='{obj.name}', type='{obj.type_}', category_id={obj.category.id}, " + \
                    ", ".join([slot + "='" + str(getattr(obj, slot) + "'") for slot in slots]) + \
                    f" WHERE id={obj.id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def delete(self, obj):
        self.cursor.execute('PRAGMA foreign_keys = on')
        statement = f"DELETE FROM {self.table_name} WHERE id={obj.id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)


class UserMapper:

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.table_name = 'users'

    def construct(self, id_, username, type_):
        user = UserFactory.create(type_, username)
        user.id = id_
        user.courses = self.get_courses_ids(id_)
        return user

    def all(self):
        statement = f"SELECT * FROM {self.table_name}"
        self.cursor.execute(statement)
        result = []

        for user in self.cursor.fetchall():
            id_, username, type_ = user
            user = self.construct(id_, username, type_)
            result.append(user)
        return result

    def find_by_id(self, id_):
        statement = f"SELECT type, username FROM {self.table_name} WHERE id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchone()

        if result:
            type_, username = result
            user = self.construct(id_, username, type_)
            return user
        raise Exception(f'record with id={id_} not found')

    def find_by_ids(self, ids):
        statement = f"SELECT id, name, type FROM {self.table_name} WHERE id IN ({', '.join(ids)})"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()

        users = []
        for user in result:
            id_, name, type_ = user
            user = self.construct(id_, name, type_)
            users.append(user)
        return users

    def find_by_type(self, type_):
        statement = f"SELECT id, username, type FROM users WHERE type='{type_}'"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()

        users = []
        for user in result:
            id_, name, type_ = user
            user = self.construct(id_, name, type_)
            users.append(user)
        return users

    def get_courses_ids(self, id_):
        statement = f"SELECT course_id FROM course_user WHERE user_id={id_}"
        self.cursor.execute(statement)
        result = self.cursor.fetchall()
        return list(map(lambda x: x[0], result))

    def insert(self, obj):
        statement = f"INSERT INTO {self.table_name} (username, type) " \
                    f"VALUES ('{obj.username}', '{obj.type_}')"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def update(self, obj):
        statement = f"UPDATE {self.table_name} " \
                    f"SET username='{obj.username}', type='{obj.type_}' " \
                    f"WHERE id={obj.id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def delete(self, obj):
        self.cursor.execute('PRAGMA foreign_keys = on')
        statement = f"DELETE FROM {self.table_name} WHERE id={obj.id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)


class CourseUser(DomainObject):

    def __init__(self, course_id, user_id):
        self.course_id = course_id
        self.user_id = user_id


class CourseUserMapper:

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.table_name = 'course_user'

    def insert(self, obj):
        statement = f"INSERT INTO {self.table_name} (course_id, user_id) VALUES ({obj.course_id}, {obj.user_id})"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)

    def delete(self, obj):
        statement = f"DELETE FROM {self.table_name} WHERE course_id={obj.course_id} AND user_id={obj.user_id}"
        self.cursor.execute(statement)

        try:
            self.connection.commit()
        except Exception as e:
            raise Exception(e.args)


connect = sqlite3.connect(os.path.join(BASE_DIR, DB_PATH))


class MapperRegistry:

    mappers = {
        'category': (Category, CategoryMapper),
        'course': (Course, CourseMapper),
        'user': (User, UserMapper),
        'course_user': (CourseUser, CourseUserMapper)
    }

    @classmethod
    def get_mapper(cls, obj):
        for mapper in cls.mappers.values():
            if isinstance(obj, mapper[0]):
                return mapper[1](connect)

    @classmethod
    def get_mapper_by_name(cls, name):
        return cls.mappers[name][1](connect)


class JSONSerializer:

    def __init__(self, obj):
        self.obj = obj

    def get_json(self):
        return dumps(self.obj)


class SingletonByName(type):

    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs)
        cls.__instance = {}

    def __call__(cls, *args, **kwargs):
        if args:
            name = args[0]
        if kwargs:
            name = kwargs['name']

        if name in cls.__instance:
            return cls.__instance[name]
        else:
            cls.__instance[name] = super().__call__(*args, **kwargs)
            return cls.__instance[name]


class Logger(metaclass=SingletonByName):

    def __init__(self, name, writer):
        self.name = name
        self.writer = writer

    def log(self, text):
        self.writer.write(self.name, text)
