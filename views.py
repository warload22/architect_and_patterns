from shogun.view import View
from shogun.request import Request
from shogun.response import Response
from shogun.template_engine import build_template
from shogun.log_writers import ConsoleWriter, FileWriter
from models import MapperRegistry, Engine, Logger, JSONSerializer
from db.unit_of_work import UnitOfWork


UnitOfWork().new_current()
UnitOfWork.get_current().set_registry(MapperRegistry)
engine = Engine()
course_logger = Logger('course logger', FileWriter)
category_logger = Logger('category logger', ConsoleWriter)
user_logger = Logger('user logger', FileWriter)


class Index(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        body = build_template(request, {'categories': MapperRegistry.get_mapper_by_name('category').all(),
                                        'courses': MapperRegistry.get_mapper_by_name('course').all(),
                                        'students': MapperRegistry.get_mapper_by_name('user').find_by_type('student'),
                                        'teachers': MapperRegistry.get_mapper_by_name('user').find_by_type('teacher'),
                                        'admins': MapperRegistry.get_mapper_by_name('user').find_by_type('admin'),
                                        'base_url': request.base_url,
                                        'session_id': request.session_id}, 'index.html')
        return Response(request, body=body)


class CategoryCreate(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        body = build_template(request, {'categories': MapperRegistry.get_mapper_by_name('category').all(),
                                        'base_url': request.base_url, 'session_id': request.session_id},
                              'create_category.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        name = request.POST.get('name')[0]
        parent_category_id = int(request.POST.get('parent_category_id')[0])
        category = MapperRegistry.get_mapper_by_name('category').find_by_id(parent_category_id) if parent_category_id >= 0 else None
        new_category = engine.create_category(name, category)
        new_category.mark_new()
        UnitOfWork.get_current().commit()
        category_logger.log(f'{name} is created')
        body = build_template(request, {'type': 'category', 'name': name, 'action': 'created',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CategoryEdit(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        category = MapperRegistry.get_mapper_by_name('category').find_by_id(int(request.GET.get('category_id')[0]))
        categories = MapperRegistry.get_mapper_by_name('category').all()
        categories = [cat for cat in categories if cat.id not in category.subcategories and cat.id != category.id]
        body = build_template(request, {'category': category,
                                        'categories': categories,
                                        'base_url': request.base_url, 'session_id': request.session_id},
                              'edit_category.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        name = request.POST.get('name')[0]
        category_id = int(request.POST.get('category_id')[0])
        parent_category_id = int(request.POST.get('parent_category_id')[0])
        category = MapperRegistry.get_mapper_by_name('category').\
            find_by_id(parent_category_id) if parent_category_id >= 0 else None
        new_category = engine.create_category(name, category)
        new_category.id = category_id
        new_category.mark_dirty()
        UnitOfWork.get_current().commit()
        category_logger.log(f'{name} is edited')
        body = build_template(request, {'type': 'category', 'name': name, 'action': 'edited',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CategoryDelete(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        category = MapperRegistry.get_mapper_by_name('category').find_by_id(int(request.GET.get('category_id')[0]))
        category.mark_removed()
        UnitOfWork.get_current().commit()
        category_logger.log(f'{category.name} is deleted')
        body = build_template(request, {'type': 'category', 'name': category.name, 'action': 'deleted',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CourseCreate(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        body = build_template(request, {'categories': MapperRegistry.get_mapper_by_name('category').all(),
                                        'types': engine.get_courses_types(),
                                        'base_url': request.base_url, 'session_id': request.session_id},
                              'create_course.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        type_ = request.POST.get('type')[0]
        name = request.POST.get('name')[0]
        slots = engine.get_courses_slots()[type_]
        params = []
        for slot in slots:
            try:
                params.append(request.POST.get(slot)[0])
            except (IndexError, TypeError):
                params.append('')
        category = MapperRegistry.get_mapper_by_name('category').find_by_id(int(request.POST.get('category_id')[0]))
        course = engine.create_course(type_, *params, name, category)
        course.mark_new()
        UnitOfWork.get_current().commit()
        course_logger.log(f'{name} (category: {category.name}, type: {type_}) is created')
        body = build_template(request, {'type': 'course', 'name': name, 'action': 'created',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CourseEdit(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        course = MapperRegistry.get_mapper_by_name('course').find_by_id(int(request.GET.get('course_id')[0]))
        body = build_template(request, {'course': course,
                                        'categories': MapperRegistry.get_mapper_by_name('category').all(),
                                        'types': engine.get_courses_types(), 'base_url': request.base_url,
                                        'session_id': request.session_id}, 'edit_course.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        id_ = int(request.POST.get('course_id')[0])
        name = request.POST.get('name')[0]
        type_ = request.POST.get('type')[0]
        slots = engine.get_courses_slots()[type_]
        params = []
        for slot in slots:
            try:
                params.append(request.POST.get(slot)[0])
            except (IndexError, TypeError):
                params.append('')
        category = MapperRegistry.get_mapper_by_name('category').find_by_id(int(request.POST.get('category_id')[0]))
        course = engine.create_course(type_, *params, name, category)
        course.id = id_
        course.mark_dirty()
        UnitOfWork.get_current().commit()
        course_logger.log(f'{name} is edited')
        body = build_template(request, {'type': 'course', 'name': name, 'action': 'edited',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CourseCopy(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        course = MapperRegistry.get_mapper_by_name('course').find_by_id(int(request.GET.get('course_id')[0]))
        body = build_template(request, {'course': course, 'base_url': request.base_url,
                                        'session_id': request.session_id}, 'copy_course.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        course_id = int(request.GET.get('course_id')[0])
        name = request.POST.get('name')[0]
        original = MapperRegistry.get_mapper_by_name('course').find_by_id(course_id)
        copy = original.clone()
        copy.name = name
        copy.mark_new()
        UnitOfWork.get_current().commit()
        course_logger.log(f'{name} is copied from {original.name}')
        body = build_template(request, {'type': 'course', 'name': name, 'action': f'copied from {original}',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class CourseDelete(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        course = MapperRegistry.get_mapper_by_name('course').find_by_id(int(request.GET.get('course_id')[0]))
        course.mark_removed()
        UnitOfWork.get_current().commit()
        course_logger.log(f'{course.name} is deleted')
        body = build_template(request, {'type': 'course', 'name': course.name, 'action': 'deleted',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class UserCreate(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        body = build_template(request, {'types': engine.get_users_types(), 'base_url': request.base_url,
                                        'session_id': request.session_id}, 'create_user.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        type_ = request.POST.get('type')[0]
        username = request.POST.get('username')[0]
        user = engine.create_user(type_, username)
        user.mark_new()
        UnitOfWork.get_current().commit()
        user_logger.log(f'{username} (type: {type_}) is created')
        body = build_template(request, {'type': 'user', 'name': username, 'action': 'created',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class UserEdit(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        user = MapperRegistry.get_mapper_by_name('user').find_by_id(int(request.GET.get('user_id')[0]))
        body = build_template(request, {'user': user, 'types': engine.get_users_types(), 'base_url': request.base_url,
                                        'session_id': request.session_id}, 'edit_user.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        user_id = int(request.POST.get('user_id')[0])
        type_ = request.POST.get('type')[0]
        username = request.POST.get('username')[0]
        user = engine.create_user(type_, username)
        user.id = user_id
        user.mark_dirty()
        UnitOfWork.get_current().commit()
        user_logger.log(f'{username} (type: {type_}) is edited')
        body = build_template(request, {'type': 'user', 'name': username, 'action': 'edited',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class UserDelete(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        user = MapperRegistry.get_mapper_by_name('user').find_by_id(int(request.GET.get('user_id')[0]))
        user.mark_removed()
        UnitOfWork.get_current().commit()
        user_logger.log(f'{user.username} is deleted')
        body = build_template(request, {'type': 'user', 'name': user.username, 'action': 'deleted',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class UserCourses(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        user = MapperRegistry.get_mapper_by_name('user').find_by_id(int(request.GET.get('user_id')[0]))
        courses = [i for i in MapperRegistry.get_mapper_by_name('course').all() if i.id not in user.courses]
        body = build_template(request, {'user': user, 'courses': courses, 'base_url': request.base_url,
                                        'session_id': request.session_id}, 'user_course.html')
        return Response(request, body=body)

    def post(self, request: Request, *args, **kwargs) -> Response:
        course_id = int(request.POST.get('course_id')[0])
        user_id = int(request.POST.get('user_id')[0])
        user = MapperRegistry.get_mapper_by_name('user').find_by_id(user_id)
        course = MapperRegistry.get_mapper_by_name('course').find_by_id(course_id)
        course_user = engine.create_course_user(course_id, user_id)
        course_user.mark_new()
        UnitOfWork.get_current().commit()
        course.add_observer(user, request.POST.get('notification_method')[0])
        user_logger.log(f'{user.username} is added to course {course.name}')
        body = build_template(request, {'type': 'user', 'name': user.username,
                                        'action': f'added to course {course.name}',
                                        'base_url': request.base_url}, 'ok_page.html')
        return Response(request, body=body)


class APICourses(View):

    def get(self, request: Request, *args, **kwargs) -> Response:
        body = JSONSerializer(MapperRegistry.get_mapper_by_name('course').all()).get_json()
        return Response(request, body=body)
