from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, DefaultDict, Dict, List, Optional


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: Dict[str, Any]
    aggregate_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


Subscriber = Callable[[DomainEvent], None]


class InMemoryEventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Subscriber) -> None:
        self._subscribers[event_name].append(callback)

    def publish(self, event: DomainEvent) -> None:
        for subscriber in self._subscribers[event.name]:
            subscriber(event)


event_bus = InMemoryEventBus()
