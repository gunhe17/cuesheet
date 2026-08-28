from os import PathLike

from fastapi import FastAPI


class Frontend:
    def __init__(
        self,
        path: str,
        directory: str | PathLike[str],
    ):
        self._path = path
        self._directory = directory

    def register(self, app: FastAPI):
        app.frontend(self._path, directory=self._directory)
