import re

from fastapi import HTTPException
from core.translations import t


_REMOTE_HOST_RE = re.compile(
    r"^(?:[A-Za-z0-9][A-Za-z0-9._-]*@)?[A-Za-z0-9][A-Za-z0-9._-]*$"
)
_SSH_PORT_RE = re.compile(r"^\d{1,5}$")


def validate_remote_host(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if not _REMOTE_HOST_RE.match(v):
        raise HTTPException(
            400,
            t("validators.invalid_remote_host"),
        )
    return v


def validate_ssh_port(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if not _SSH_PORT_RE.fullmatch(str(v)):
        raise HTTPException(400, t("validators.invalid_ssh_port"))
    port = int(v)
    if port < 1 or port > 65535:
        raise HTTPException(400, t("validators.invalid_ssh_port"))
    return str(port)
