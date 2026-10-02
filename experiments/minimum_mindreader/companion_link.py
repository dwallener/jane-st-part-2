"""Stable byte vocabulary between the ASIC and a product companion MCU."""

from __future__ import annotations

from enum import IntEnum, IntFlag


class Command(IntFlag):
    DISCOVER = 1 << 0
    LEARN = 1 << 1
    PROMOTE = 1 << 2
    OWNERSHIP = 1 << 3
    ACTIVATE = 1 << 4
    REVOKE = 1 << 5
    CLEAR_FAULT = 1 << 6
    STATUS = 1 << 7


class ProductState(IntEnum):
    RESET = 0x00
    OBSERVING = 0x01
    QUIET = 0x02
    AMBIGUOUS = 0x03
    PROBE_READY = 0x04
    INTERROGATING = 0x05
    RESOLVED = 0x06
    MODEL_READY = 0x07
    EMULATING = 0x08
    COMPROMISED = 0xE0
    CONTRADICTION = 0xE1
    CONTENTION = 0xE2
    TIMEOUT = 0xE3
    REVOKED = 0xE4


def status_request(page: int, *, companion: bool = False) -> int:
    """Encode one of the two 32-page passive read banks onto ui[7:0]."""
    if not 0 <= page < 32:
        raise ValueError("status page must be in the range 0..31")
    request = int(Command.STATUS)
    request |= ((page >> 4) & 1) << 1
    request |= ((page >> 2) & 0x3) << 2
    request |= (page & 0x3) << 5
    if companion:
        request |= int(Command.DISCOVER)
    return request


def status_page(request: int) -> tuple[bool, int]:
    """Decode a passive read request into companion-bank flag and page."""
    if request & int(Command.STATUS) == 0 or request & int(Command.ACTIVATE):
        raise ValueError("byte is not a passive status request")
    page = ((request >> 1) & 1) << 4
    page |= ((request >> 2) & 0x3) << 2
    page |= (request >> 5) & 0x3
    return bool(request & int(Command.DISCOVER)), page
