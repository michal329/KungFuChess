"""Encodes/decodes commands and messages to/from JSON text -- the only
format that crosses the wire (never pickle: unsafe, and unnecessary
here since every field is already a JSON primitive).
"""
from __future__ import annotations

import dataclasses
import json
from typing import Type, TypeVar

from protocol.commands import COMMAND_TYPES, Command
from protocol.messages import MESSAGE_TYPES, Message

T = TypeVar("T")


class ProtocolError(ValueError):
    """Base class for malformed wire data."""


class UnknownCommandError(ProtocolError):
    def __init__(self, name):
        super().__init__(f"unknown command: {name!r}")


class UnknownMessageTypeError(ProtocolError):
    def __init__(self, name):
        super().__init__(f"unknown message type: {name!r}")


class MissingFieldError(ProtocolError):
    def __init__(self, field_name):
        super().__init__(f"missing required field: {field_name!r}")


def _wire_key(f: dataclasses.Field) -> str:
    return f.metadata.get("json_key", f.name)


def _fields_to_dict(obj) -> dict:
    return {_wire_key(f): getattr(obj, f.name) for f in dataclasses.fields(obj)}


def _dict_to_kwargs(cls: Type[T], data: dict) -> dict:
    kwargs = {}
    for f in dataclasses.fields(cls):
        key = _wire_key(f)
        if key in data:
            kwargs[f.name] = data[key]
        elif f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            raise MissingFieldError(f.name)
    return kwargs


def command_to_dict(command: Command) -> dict:
    return {"command": command.command, **_fields_to_dict(command)}


def message_to_dict(message: Message) -> dict:
    return {"type": message.type, **_fields_to_dict(message)}


def command_from_dict(data: dict) -> Command:
    name = data.get("command")
    cls = COMMAND_TYPES.get(name)
    if cls is None:
        raise UnknownCommandError(name)
    return cls(**_dict_to_kwargs(cls, data))


def message_from_dict(data: dict) -> Message:
    name = data.get("type")
    cls = MESSAGE_TYPES.get(name)
    if cls is None:
        raise UnknownMessageTypeError(name)
    return cls(**_dict_to_kwargs(cls, data))


def encode_command(command: Command) -> str:
    return json.dumps(command_to_dict(command))


def encode_message(message: Message) -> str:
    return json.dumps(message_to_dict(message))


def decode_command(raw: str) -> Command:
    return command_from_dict(json.loads(raw))


def decode_message(raw: str) -> Message:
    return message_from_dict(json.loads(raw))
