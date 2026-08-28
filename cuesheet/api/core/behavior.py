from __future__ import annotations

from dataclasses import dataclass, field


# #
# marker

class Action:
    ...

class Context:
    ...


# #
# memory

@dataclass
class Memory:
    actions: set[type] = field(default_factory=set)

@dataclass(frozen=True)
class Scope:
    ...
    

# #
# behavior

class Behavior:

    def set_action(self, requires: tuple[Action, ...]) -> set[type]:
        return {type(require) for require in requires}

    async def run_action(self, memory: Memory, *, action: type[Action]) -> None:
        if action in memory.actions:
            await action.act(memory)
