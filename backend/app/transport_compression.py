"""Compress large simulation responses, leaving authentication and HTML alone."""
from starlette.middleware.gzip import GZipMiddleware


class SimulationCompression:
    def __init__(self, app):
        self.app = app
        # Level one keeps CPU cost low on the small hosted instance.
        self.compressed = GZipMiddleware(app, minimum_size=2048, compresslevel=1)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] == 'http' and scope.get('method') == 'GET' and (path.startswith('/api/v1/world') or path.startswith('/account/game-data/')):
            return await self.compressed(scope, receive, send)
        return await self.app(scope, receive, send)
