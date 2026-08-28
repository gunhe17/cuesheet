from __future__ import annotations

from cuesheet.api.core.exception import ClientError, DevelopError


# #
# base

class InfrastructureDevelopError(DevelopError):
    ...


class InfrastructureClientError(ClientError):
    ...
