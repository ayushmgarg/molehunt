"""Parse authored two-variant slots and render a selected binary codeword."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_CHOICE = re.compile(r"\{\{(?P<channel>[a-z][a-z0-9_]*):(?P<a>[^{}|]*)\|(?P<b>[^{}|]*)\}\}")
_MARKERS = ("{{", "}}")


@dataclass(frozen=True, slots=True)
class Literal:
    """Unchanged text between authored variation slots."""

    text: str


@dataclass(frozen=True, slots=True)
class Choice:
    """A channel-labelled choice: bit zero selects ``zero``, bit one ``one``."""

    channel: str
    zero: str
    one: str


Node = Literal | Choice


@dataclass(frozen=True, slots=True)
class Template:
    """Immutable parsed master with choices in source order."""

    nodes: tuple[Node, ...]

    @property
    def choices(self) -> tuple[Choice, ...]:
        """Return all variation slots in their authored order."""
        return tuple(node for node in self.nodes if isinstance(node, Choice))

    def render(self, bits: Sequence[int]) -> str:
        """Render one text variant for each binary slot in source order."""
        choices = self.choices
        if len(bits) != len(choices):
            raise ValueError(f"bit count must equal slot count ({len(choices)})")
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("each codeword bit must be 0 or 1")
        output: list[str] = []
        bit_index = 0
        for node in self.nodes:
            if isinstance(node, Literal):
                output.append(node.text)
            else:
                output.append(node.zero if bits[bit_index] == 0 else node.one)
                bit_index += 1
        return "".join(output)


def parse_template(source: str) -> Template:
    """Parse `{{channel:variant0|variant1}}` tokens and reject malformed braces."""
    nodes: list[Node] = []
    cursor = 0
    for match in _CHOICE.finditer(source):
        literal = source[cursor : match.start()]
        if any(marker in literal for marker in _MARKERS):
            raise ValueError("malformed variation marker")
        if literal:
            nodes.append(Literal(literal))
        nodes.append(
            Choice(
                channel=match.group("channel"),
                zero=match.group("a"),
                one=match.group("b"),
            )
        )
        cursor = match.end()
    tail = source[cursor:]
    if any(marker in tail for marker in _MARKERS):
        raise ValueError("malformed variation marker")
    if tail:
        nodes.append(Literal(tail))
    return Template(tuple(nodes))
