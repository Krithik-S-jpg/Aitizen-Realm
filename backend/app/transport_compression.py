"""Keep Godot HTTP responses unencoded across browser and native transports."""


class SimulationTransport:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] == 'http' and scope.get('method') == 'GET' and (path.startswith('/api/v1/world') or path.startswith('/account/game-data/')):
            # Browser fetch can decode gzip before Godot receives the body while
            # retaining Content-Encoding. A second decode then fails in Godot.
            # Do not gzip these endpoints; ask intermediaries not to transform
            # them either. Preserve authentication and existing cache directives.
            async def send_identity(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    for index, (key, value) in enumerate(headers):
                        if key.lower() == b'cache-control':
                            if b'no-transform' not in value.lower():
                                headers[index] = (key, value + b', no-transform')
                            break
                    else:
                        headers.append((b'cache-control', b'no-transform'))
                    message = {**message, 'headers': headers}
                await send(message)
            return await self.app(scope, receive, send_identity)
        return await self.app(scope, receive, send)
