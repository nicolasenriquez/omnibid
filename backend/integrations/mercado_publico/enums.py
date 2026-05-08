from __future__ import annotations

from enum import IntEnum


class LicitacionEstadoCode(IntEnum):
    PUBLICADA = 5
    CERRADA = 6
    DESIERTA = 7
    ADJUDICADA = 8
    REVOCADA = 18
    SUSPENDIDA = 19

