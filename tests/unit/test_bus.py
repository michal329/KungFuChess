from server.bus import Bus, WILDCARD_TOPIC


def test_publish_calls_only_matching_topic_subscribers():
    bus = Bus()
    received = []
    bus.subscribe("game.1", lambda topic, message: received.append((topic, message)))
    bus.subscribe("game.2", lambda topic, message: received.append("wrong"))

    bus.publish("game.1", "hello")

    assert received == [("game.1", "hello")]


def test_wildcard_subscriber_receives_every_topic():
    bus = Bus()
    received = []
    bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append((topic, message)))

    bus.publish("game.1", "a")
    bus.publish("game.2", "b")

    assert received == [("game.1", "a"), ("game.2", "b")]


def test_topic_and_wildcard_subscribers_both_fire_once_each():
    bus = Bus()
    calls = []
    bus.subscribe("game.1", lambda topic, message: calls.append("specific"))
    bus.subscribe(WILDCARD_TOPIC, lambda topic, message: calls.append("wildcard"))

    bus.publish("game.1", "x")

    assert calls == ["specific", "wildcard"]


def test_publish_with_no_subscribers_is_a_no_op():
    bus = Bus()
    bus.publish("nobody.listening", "x")  # must not raise
