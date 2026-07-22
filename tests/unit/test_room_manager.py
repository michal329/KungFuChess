import pytest

from server.room_manager import RoomManager, RoomNotFoundError


def test_create_room_returns_distinct_ids():
    manager = RoomManager()
    room_a = manager.create_room()
    room_b = manager.create_room()
    assert room_a.room_id != room_b.room_id
    assert room_a.white is None and room_a.black is None and room_a.spectators == []


def test_first_join_becomes_white_second_becomes_black_rest_are_spectators():
    manager = RoomManager()
    room = manager.create_room()

    manager.join_room(room.room_id, "conn-1")
    manager.join_room(room.room_id, "conn-2")
    manager.join_room(room.room_id, "conn-3")

    assert room.white == "conn-1"
    assert room.black == "conn-2"
    assert room.spectators == ["conn-3"]


def test_joining_the_same_room_twice_is_idempotent():
    manager = RoomManager()
    room = manager.create_room()
    manager.join_room(room.room_id, "conn-1")

    manager.join_room(room.room_id, "conn-1")  # joins again

    assert room.white == "conn-1"
    assert room.black is None  # must not have been bumped into black


def test_join_unknown_room_raises():
    manager = RoomManager()
    with pytest.raises(RoomNotFoundError):
        manager.join_room("nope", "conn-1")


def test_room_for_connection_finds_the_right_room():
    manager = RoomManager()
    room_a = manager.create_room()
    room_b = manager.create_room()
    manager.join_room(room_a.room_id, "conn-1")
    manager.join_room(room_b.room_id, "conn-2")

    assert manager.room_for_connection("conn-1").room_id == room_a.room_id
    assert manager.room_for_connection("conn-2").room_id == room_b.room_id
    assert manager.room_for_connection("conn-99") is None


def test_leave_frees_the_white_seat():
    manager = RoomManager()
    room = manager.create_room()
    manager.join_room(room.room_id, "conn-1")

    manager.leave("conn-1")

    assert room.white is None
    assert manager.room_for_connection("conn-1") is None


def test_leave_removes_a_spectator():
    manager = RoomManager()
    room = manager.create_room()
    manager.join_room(room.room_id, "conn-1")
    manager.join_room(room.room_id, "conn-2")
    manager.join_room(room.room_id, "conn-3")

    manager.leave("conn-3")

    assert room.spectators == []


def test_leave_for_a_connection_in_no_room_is_a_no_op():
    manager = RoomManager()
    assert manager.leave("nobody") is None
