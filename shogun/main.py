from typing import List, Type
import re
from shogun.url import Url
from shogun.view import View
from shogun.request import Request
from shogun.response import Response
from shogun.exceptions import UrlNotFound, MethodNotAllowed
from shogun.middleware import BaseMiddleware


class Shogun:

    __slots__ = ('urls', 'settings', 'middlewares')

    def __init__(self, urls: List[Url], settings: dict, middlewares: List[Type[BaseMiddleware]]):
        self.urls = urls
        self.settings = settings
        self.middlewares = middlewares

    def __call__(self, environ: dict, start_response):
        view = self.get_view(environ)
        request = self.get_request(environ)
        self.apply_middlewares_to_request(request)
        response = self.get_response(environ, view, request)
        self.apply_middlewares_to_response(response)
        start_response(str(response.status_code), list(response.headers.items()))
        return iter([response.body])

    @staticmethod
    def prepare_url(url: str) -> str:
        if url[-1] == '/':
            url = url[:-1]
        if url and url[0] == '/':
            url = url[1:]
        return url

    def find_view(self, raw_url: str) -> Type[View]:
        url = self.prepare_url(raw_url)
        for u in self.urls:
            if re.match(u.url, url):
                return u.view
        raise UrlNotFound

    def get_view(self, environ: dict) -> View:
        raw_url = environ['PATH_INFO']
        return self.find_view(raw_url)()

    def get_request(self, environ: dict) -> Request:
        return Request(environ, self.settings)

    @staticmethod
    def get_response(environ: dict, view: View, request: Request) -> Response:
        method = environ['REQUEST_METHOD'].lower()
        if not hasattr(view, method):
            raise MethodNotAllowed
        return getattr(view, method)(request)

    def apply_middlewares_to_request(self, request: Request):
        for i in self.middlewares:
            i().to_request(request)

    def apply_middlewares_to_response(self, response: Response):
        for i in self.middlewares:
            i().to_response(response)
