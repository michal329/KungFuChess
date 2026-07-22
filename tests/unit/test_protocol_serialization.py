import json

import pytest

from protocol.commands import LeaveRoomCommand, LoginCommand, MoveCommand, PlayCommand, ResignCommand
from protocol.messages import ErrorMessage, JumpQueuedMessage, MoveEventMessage, MoveQueuedMessage, SnapshotMessage
from protocol.serialization import (
    MissingFieldError,
    UnknownCommandError,
    UnknownMessageTypeError,
    decode_command,
    decode_message,
    encode_command,
    encode_message,
)


def test_move_command_round_trips_with_from_as_wire_key():
    cmd = MoveCommand(from_={"row": 6, "col": 4}, to={"row": 4, "col": 4})
    raw = encode_command(cmd)
    data = json.loads(raw)
    assert data == {"command": "move", "from": {"row": 6, "col": 4}, "to": {"row": 4, "col": 4}}
    assert decode_command(raw) == cmd


def test_jump_is_a_move_command_with_equal_from_and_to():
    cmd = MoveCommand(from_={"row": 6, "col": 4}, to={"row": 6, "col": 4})
    assert cmd.from_ == cmd.to


def test_login_command_optional_password_defaults_to_none():
    raw = encode_command(LoginCommand(username="alice"))
    assert json.loads(raw) == {"command": "login", "username": "alice", "password": None}
    assert decode_command(raw) == LoginCommand(username="alice", password=None)


def test_play_command_has_no_extra_fields():
    raw = encode_command(PlayCommand())
    assert json.loads(raw) == {"command": "play"}


def test_decode_unknown_command_raises():
    with pytest.raises(UnknownCommandError):
        decode_command(json.dumps({"command": "teleport"}))


def test_resign_command_has_no_extra_fields():
    raw = encode_command(ResignCommand())
    assert json.loads(raw) == {"command": "resign"}
    assert decode_command(raw) == ResignCommand()


def test_leave_room_command_round_trips():
    raw = encode_command(LeaveRoomCommand())
    assert json.loads(raw) == {"command": "leave_room"}
    assert decode_command(raw) == LeaveRoomCommand()


def test_decode_command_missing_required_field_raises():
    with pytest.raises(MissingFieldError):
        decode_command(json.dumps({"command": "join_room"}))


def test_snapshot_message_carries_opaque_payload():
    payload = {"board": {"height": 1, "width": 1, "grid": [["."]]}, "current_time": 0}
    raw = encode_message(SnapshotMessage(payload=payload))
    assert decode_message(raw) == SnapshotMessage(payload=payload)


def test_move_event_message_round_trips():
    msg = MoveEventMessage(piece="WQ", from_={"row": 0, "col": 0}, to={"row": 1, "col": 1}, arrival_time=3000)
    raw = encode_message(msg)
    assert json.loads(raw) == {
        "type": "move_event", "piece": "WQ",
        "from": {"row": 0, "col": 0}, "to": {"row": 1, "col": 1}, "arrival_time": 3000,
    }
    assert decode_message(raw) == msg


def test_move_queued_message_round_trips_with_from_as_wire_key():
    msg = MoveQueuedMessage(piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, start_time=0, arrival_time=3000)
    raw = encode_message(msg)
    assert json.loads(raw) == {
        "type": "move_queued", "piece": "WR",
        "from": {"row": 0, "col": 0}, "to": {"row": 0, "col": 3}, "start_time": 0, "arrival_time": 3000,
    }
    assert decode_message(raw) == msg


def test_jump_queued_message_round_trips():
    msg = JumpQueuedMessage(piece="WN", pos={"row": 0, "col": 0}, start_time=0, land_time=500)
    raw = encode_message(msg)
    assert decode_message(raw) == msg


def test_error_message_round_trips():
    raw = encode_message(ErrorMessage(reason="room not found"))
    assert decode_message(raw) == ErrorMessage(reason="room not found")


def test_decode_unknown_message_type_raises():
    with pytest.raises(UnknownMessageTypeError):
        decode_message(json.dumps({"type": "confetti"}))
