"""Client -> server commands.

Every field is already JSON-primitive (str / int / bool / dict / None)
-- no ``kfchess.model`` types leak into this module -- so a command
dataclass round-trips through ``dataclasses.fields``/``json.dumps`` with
no custom encoder (see ``protocol.serialization``).

Board squares travel as ``{"row": int, "col": int}`` rather than
algebraic notation ("e2"): the board size isn't hardcoded (see
CLAUDE.md's additional design notes), and row/col is exactly what
``Position`` already is, with no assumption of an 8-wide board or
letter files.

A jump is not a separate command: exactly like ``ClickController``
(see ``kfchess/input/click_controller.py``), clicking a selected
piece's own square again is what turns a ``MoveCommand`` into a jump --
the command router tells them apart the same way ClickController does,
by ``from_ == to``. There is no ``JumpCommand``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional

# "from" is a Python keyword, so the field is named from_ and tagged
# with the wire key it actually serializes to.
_FROM_KEY = {"json_key": "from"}


@dataclass(frozen=True)
class Command:
    """Marker base class for all client -> server commands. Every
    subclass sets ``command`` (a plain class attribute, not a
    dataclass field) to its wire discriminator string."""
    command: ClassVar[str] = ""


@dataclass(frozen=True)
class LoginCommand(Command):
    command: ClassVar[str] = "login"
    username: str
    password: Optional[str] = None


@dataclass(frozen=True)
class CreateRoomCommand(Command):
    command: ClassVar[str] = "create_room"


@dataclass(frozen=True)
class JoinRoomCommand(Command):
    command: ClassVar[str] = "join_room"
    room_id: str


@dataclass(frozen=True)
class PlayCommand(Command):
    """Enter matchmaking."""
    command: ClassVar[str] = "play"


@dataclass(frozen=True)
class MoveCommand(Command):
    command: ClassVar[str] = "move"
    from_: Dict[str, int] = field(metadata=_FROM_KEY)
    to: Dict[str, int] = None


@dataclass(frozen=True)
class ResignCommand(Command):
    command: ClassVar[str] = "resign"


@dataclass(frozen=True)
class LeaveRoomCommand(Command):
    """Voluntarily give up a seat (or a spectator slot) without
    disconnecting -- the architecture doc's "Cancel" option alongside
    Create/Join. Distinct from just closing the socket: the connection
    stays open (e.g. to go create or join a different room next)."""
    command: ClassVar[str] = "leave_room"


@dataclass(frozen=True)
class DisconnectCommand(Command):
    command: ClassVar[str] = "disconnect"


# Registry used by protocol.serialization to reconstruct the right
# dataclass from an incoming {"command": ...} dict.
COMMAND_TYPES = {
    "login": LoginCommand,
    "create_room": CreateRoomCommand,
    "join_room": JoinRoomCommand,
    "play": PlayCommand,
    "move": MoveCommand,
    "resign": ResignCommand,
    "leave_room": LeaveRoomCommand,
    "disconnect": DisconnectCommand,
}
