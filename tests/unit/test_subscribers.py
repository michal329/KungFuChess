import logging

from server.bus import Bus, WILDCARD_TOPIC
from server.subscribers import LoggingSubscriber, MoveLogSubscriber
from protocol.messages import MoveEventMessage, TimerMessage


def test_logging_subscriber_logs_topic_and_message(caplog):
    bus = Bus()
    bus.subscribe(WILDCARD_TOPIC, LoggingSubscriber())

    with caplog.at_level(logging.INFO):
        bus.publish("game.1", TimerMessage(current_time=100))

    assert len(caplog.records) == 1
    assert "game.1" in caplog.text
    assert "TimerMessage" in caplog.text


def test_move_log_subscriber_only_records_move_events():
    bus = Bus()
    move_log = MoveLogSubscriber()
    bus.subscribe(WILDCARD_TOPIC, move_log)

    move = MoveEventMessage(piece="WQ", from_={"row": 0, "col": 0}, to={"row": 1, "col": 1}, arrival_time=1000)
    bus.publish("game.1", move)
    bus.publish("game.1", TimerMessage(current_time=1000))

    assert move_log.moves() == [move]


def test_move_log_moves_returns_a_defensive_copy():
    move_log = MoveLogSubscriber()
    move_log("game.1", MoveEventMessage(piece="WQ", from_={"row": 0, "col": 0}, to={"row": 1, "col": 1}, arrival_time=1000))

    snapshot = move_log.moves()
    snapshot.append("tampered")

    assert move_log.moves() == [MoveEventMessage(piece="WQ", from_={"row": 0, "col": 0}, to={"row": 1, "col": 1}, arrival_time=1000)]
