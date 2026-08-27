from __future__ import annotations

import unittest

from jarvis.core.event_bus import Event, EventBus, EventType


class EventBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_specific_and_global_subscribers(self) -> None:
        bus = EventBus()
        received: list[str] = []
        bus.subscribe(EventType.SYSTEM_STARTED, lambda event: received.append("specific"))

        async def global_handler(event: Event) -> None:
            received.append(event.type.value)

        unsubscribe = bus.subscribe(None, global_handler)
        await bus.publish(Event(EventType.SYSTEM_STARTED))
        unsubscribe()
        await bus.publish(Event(EventType.SYSTEM_SHUTDOWN))
        self.assertEqual(received, ["specific", "SYSTEM_STARTED"])

    async def test_faulty_subscriber_does_not_block_others(self) -> None:
        bus = EventBus()
        received: list[bool] = []

        def broken(event: Event) -> None:
            raise RuntimeError("boom")

        bus.subscribe(None, broken)
        bus.subscribe(None, lambda event: received.append(True))
        await bus.publish(Event(EventType.ERROR_OCCURRED))
        self.assertEqual(received, [True])


if __name__ == "__main__":
    unittest.main()

