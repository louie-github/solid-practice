from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass
from typing import Protocol

from .project_types import PlayerId, Cell, Symbol, Feedback, Field


@dataclass(eq=True, frozen=True)
class GridGameMove:
    player: PlayerId
    symbol: Symbol
    cell: Cell


type GridGameMoveHistory = Sequence[GridGameMove]
type MutableGridGameMoveHistory = MutableSequence[GridGameMove]


class WinValidator(Protocol):
    def get_winner(
        self, field: Field, move_history: GridGameMoveHistory
    ) -> PlayerId | None: ...


class TicTacToeWinValidator:
    def _get_groups(self, field: Field):
        yield from (  # rows
            [Cell(row, k) for k in field.valid_coords] for row in field.valid_coords
        )
        yield from (  # columns
            [Cell(k, col) for k in field.valid_coords] for col in field.valid_coords
        )
        yield from (  # diagonals
            # Backslash
            [Cell(k, k) for k in field.valid_coords],
            # Forward slash
            [Cell(k, field.grid_size - k + 1) for k in field.valid_coords],
        )

    def get_winner(self, field: Field, move_history: GridGameMoveHistory):
        for group in self._get_groups(field):
            basis = field.get_symbol_at(group[0])
            if basis is not None and field.are_all_equal_to_basis(basis, group):
                for move in reversed(move_history):
                    if move.cell in group and move.symbol == basis:
                        return move.player
                else:
                    assert False, (
                        f"Winning symbol {basis} in cell group {group} has no associated player"
                    )
        else:
            return None


class GridGameModel:
    def __init__(
        self,
        grid_size: int,
        player_symbols: Sequence[Symbol],
        player_count: int,
        win_validator: WinValidator,
    ):
        if player_count <= 1:
            raise ValueError(f"Must have at least two players (found {player_count})")

        unique_symbols = set(player_symbols)

        if len(unique_symbols) != len(player_symbols):
            raise ValueError(f"Player symbols must be unique (was {player_symbols}")

        if len(player_symbols) != player_count:
            raise ValueError(
                f"Player symbols must be exactly {player_count} (was {player_symbols})"
            )

        self._field = Field(grid_size)
        self._move_history: MutableGridGameMoveHistory = []
        self._win_validator: WinValidator = win_validator

        self._player_count = player_count
        self._player_to_symbol: dict[PlayerId, Symbol] = {
            k: symbol for k, symbol in enumerate(player_symbols, start=1)
        }
        self._symbol_to_player: dict[Symbol, PlayerId] = {
            symbol: k for k, symbol in self._player_to_symbol.items()
        }
        self._current_player: PlayerId = 1

    @property
    def occupied_cells(self) -> dict[Cell, Symbol]:
        return self._field.occupied_cells

    @property
    def grid_size(self):
        return self._field.grid_size

    @property
    def is_game_over(self):
        return self.winner is not None or not self._field.has_unoccupied_cell()

    @property
    def current_player(self) -> PlayerId:
        return self._current_player

    @property
    def player_count(self):
        return self._player_count

    @property
    def next_player(self) -> PlayerId:
        return (
            self.current_player + 1 if self.current_player != self.player_count else 1
        )

    @property
    def winner(self) -> PlayerId | None:
        return self._win_validator.get_winner(self._field, self._move_history)

    def get_symbol_choices(self, player: PlayerId) -> list[Symbol]:
        if player not in self._player_to_symbol:
            raise ValueError(f"Invalid player: {player}")

        return [self._player_to_symbol[player]]

    def place_symbol(self, symbol: Symbol, cell: Cell) -> Feedback:
        if self.is_game_over:
            return Feedback.GAME_OVER

        if symbol not in self.get_symbol_choices(self.current_player):
            return Feedback.INVALID_SYMBOL

        if not self._field.is_within_bounds(cell):
            return Feedback.OUT_OF_BOUNDS

        if self._field.get_symbol_at(cell) is not None:
            return Feedback.OCCUPIED

        self._field.place_symbol(symbol, cell)
        self._move_history.append(GridGameMove(self._current_player, symbol, cell))
        self._switch_to_next_player()

        return Feedback.VALID

    def _switch_to_next_player(self):
        self._current_player = self.next_player
