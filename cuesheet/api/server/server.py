from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from cuesheet.api.server.exception import ExceptionHandler
from cuesheet.api.server.frontend import Frontend
from cuesheet.api.server.lifecycle import Lifecycle
from cuesheet.api.server.middleware import Middleware
from cuesheet.api.server.router import Router


class Server:
    def __init__(self, name: str):
        self._name = name

        self._middlewares: list[Middleware] = []
        self._routers: list[Router] = []
        self._lifecycles: list[Lifecycle] = []
        self._exception_handlers: list[ExceptionHandler] = []
        self._frontends: list[Frontend] = []

    def middleware(self, middleware: Middleware):
        self._middlewares.append(middleware)

    def router(self, router: Router):
        self._routers.append(router)

    def lifecycle(self, lifecycle: Lifecycle):
        self._lifecycles.append(lifecycle)

    def exception_handler(self, exception_handler: ExceptionHandler):
        self._exception_handlers.append(exception_handler)

    def frontend(self, frontend: Frontend):
        self._frontends.append(frontend)

    def app(self):
        lifespan = self._combined_lifespan() if self._lifecycles else None
        app = FastAPI(lifespan=lifespan)

        for middleware in self._middlewares:
            middleware.register(app)

        for router in self._routers:
            router.register(app)

        for exception_handler in self._exception_handlers:
            exception_handler.register(app)

        for frontend in self._frontends:
            frontend.register(app)

        return app

    def _combined_lifespan(self):
        lifespans = [lifecycle.lifespan() for lifecycle in self._lifecycles]

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            async with AsyncExitStack() as stack:
                for lifespan in lifespans:
                    await stack.enter_async_context(lifespan(app))
                yield

        return _lifespan


# #
# factory

def cuesheet_api():
    return Server(name="cuesheet-api")
