from typing import Callable, Dict, List, Type
from contracts.events.events import DomainEvent

class EventBus:
    _instance: 'EventBus' = None

    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}

    @classmethod
    def get_instance(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            handler(event)
