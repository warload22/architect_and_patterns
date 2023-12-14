from shogun.url import Url
from views import *

urls = [
    Url('^$', Index),
    Url('^categories/create$', CategoryCreate),
    Url('^categories/edit$', CategoryEdit),
    Url('^categories/delete', CategoryDelete),
    Url('^courses/create$', CourseCreate),
    Url('^courses/edit$', CourseEdit),
    Url('^courses/copy', CourseCopy),
    Url('^courses/delete', CourseDelete),
    Url('^users/create$', UserCreate),
    Url('^users/edit$', UserEdit),
    Url('^users/delete', UserDelete),
    Url('^users/courses$', UserCourses),
    Url('^api/courses$', APICourses)
]
