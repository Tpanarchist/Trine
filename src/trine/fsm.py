"""MiniFSM — pure-Python deterministic state machine.

The constraint substrate. Controls what transitions are PERMITTED.
Never computes. Never decides. Only enforces.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


class MachineError(Exception):
    """Illegal transition attempted."""


class EventData:
    """Minimal event object passed to callbacks."""
    __slots__ = ("kwargs",)

    def __init__(self, kwargs: Dict[str, Any]) -> None:
        self.kwargs = kwargs


class MiniFSM:
    """Lightweight deterministic FSM with callback support.

    Supports flat and hierarchical (dot-separated) state names,
    wildcard '*' sources, before/after/on_enter callbacks.
    """

    __slots__ = ("model", "_state_names", "_dispatch", "_on_enter")

    def __init__(
        self,
        model: Any,
        states: List[Any],
        transitions: List[Dict[str, Any]],
        initial: str = "idle",
    ) -> None:
        self.model = model
        self._state_names = self._flatten_states(states)
        self._on_enter: Dict[str, List[str]] = {}
        self._extract_on_enter(states, prefix="")

        # Build dispatch table: trigger → [(sources, dest, before, after), ...]
        self._dispatch: Dict[str, List[Tuple]] = {}
        for t in transitions:
            trigger = t["trigger"]
            sources = t.get("source", "*")
            if isinstance(sources, str):
                sources = [sources]
            entry = (sources, t["dest"], t.get("before"), t.get("after"))
            self._dispatch.setdefault(trigger, []).append(entry)

        model.state = initial
        self._bind_triggers()

    def _flatten_states(self, states: List[Any], prefix: str = "") -> List[str]:
        result: List[str] = []
        for s in states:
            if isinstance(s, str):
                result.append(f"{prefix}{s}" if prefix else s)
            elif isinstance(s, dict):
                name = s["name"]
                full = f"{prefix}{name}" if prefix else name
                result.append(full)
                for child in s.get("children", []):
                    if isinstance(child, str):
                        result.append(f"{full}.{child}")
                    elif isinstance(child, dict):
                        result.extend(self._flatten_states([child], prefix=f"{full}."))
        return result

    def _extract_on_enter(self, states: List[Any], prefix: str) -> None:
        for s in states:
            if isinstance(s, dict):
                name = s["name"]
                full = f"{prefix}{name}" if prefix else name
                if "on_enter" in s:
                    cb = s["on_enter"]
                    self._on_enter[full] = [cb] if isinstance(cb, str) else cb
                for child in s.get("children", []):
                    if isinstance(child, dict):
                        self._extract_on_enter([child], prefix=f"{full}.")

    def _bind_triggers(self) -> None:
        seen: set = set()
        for trigger in self._dispatch:
            if trigger not in seen:
                seen.add(trigger)
                self._make_trigger(trigger)

    def _make_trigger(self, trigger: str) -> None:
        def fire(**kwargs: Any) -> None:
            self._fire(trigger, kwargs)
        setattr(self.model, trigger, fire)

    def _fire(self, trigger: str, kwargs: Dict[str, Any]) -> None:
        entries = self._dispatch.get(trigger)
        if not entries:
            raise MachineError(f"no transition for trigger '{trigger}'")
        current = self.model.state
        event = EventData(kwargs)
        for sources, dest, before_cb, after_cb in entries:
            if self._source_matches(current, sources):
                if before_cb:
                    self._call(before_cb, event)
                self.model.state = dest
                self._fire_on_enter(dest, event)
                if after_cb:
                    self._call(after_cb, event)
                return
        raise MachineError(f"can't trigger '{trigger}' from state '{current}'")

    def _source_matches(self, current: str, sources: List[str]) -> bool:
        for s in sources:
            if s == "*" or current == s or current.startswith(s + "."):
                return True
        return False

    def _fire_on_enter(self, state: str, event: EventData) -> None:
        if state in self._on_enter:
            for cb in self._on_enter[state]:
                self._call(cb, event)
        parts = state.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            if ancestor in self._on_enter:
                for cb in self._on_enter[ancestor]:
                    self._call(cb, event)

    def _call(self, name: str, event: EventData) -> None:
        fn = getattr(self.model, name, None)
        if fn is None:
            raise MachineError(f"callback '{name}' not found on model")
        try:
            fn(event)
        except TypeError:
            fn()

    @property
    def states(self) -> List[str]:
        return list(self._state_names)
