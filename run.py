from wsgiref.simple_server import make_server
from shogun.main import Shogun
from urls import urls
import settings
from shogun.middleware import middlewares


def get_settings():
    settings_dict = {}
    for j in [i for i in dir(settings) if i.isupper()]:
        settings_dict[j] = getattr(settings, j)
    return settings_dict


application = Shogun(urls=urls, settings=get_settings(), middlewares=middlewares)


with make_server('', 8000, application) as httpd:
    print("Запуск на порту 8000...")
    httpd.serve_forever()
