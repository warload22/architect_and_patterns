from shogun.request import Request


class Response:

    def __init__(self, request: Request, status_code: str = '200 OK', headers: dict = None, body: str = ''):
        self.status_code = status_code
        self.headers = {}
        self.body = b''
        self.set_base_headers()
        if headers:
            self.update_headers(headers)
        self.set_body(body)
        self.request = request
        self.extra = {}

    def __getattr__(self, item):
        return self.extra.get(item, '')

    def set_base_headers(self):
        self.headers = {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': '0'}

    def set_body(self, raw_body: str):
        self.body = raw_body.encode('utf-8')
        self.update_headers(
            {'Content-Length': str(len(self.body))}
        )

    def update_headers(self, headers: dict):
        self.headers.update(headers)
