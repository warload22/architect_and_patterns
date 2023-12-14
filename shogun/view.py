from shogun.request import Request
from shogun.response import Response


class View:

    def get(self, request: Request, *args, **kwargs) -> Response:
        pass

    def post(self, request: Request, *args, **kwargs) -> Response:
        pass
