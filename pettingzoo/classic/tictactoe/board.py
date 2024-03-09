class BadTicTacToeMoveException(Exception):
    """Exception raised when a bad move is made on TicTacToe board."""

    def __init__(self, message="Bad TicTacToe move"):
        super().__init__(message)


class Board:
    # indices of the winning lines: vertical(x3), horizontal(x3), diagonal(x2)
    winning_combinations = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]

    def __init__(self):
        # internally self.board.squares holds a flat representation of tic tac toe board
        # where an empty board is [0, 0, 0, 0, 0, 0, 0, 0, 0]
        # where indexes are column wise order
        # 0 3 6
        # 1 4 7
        # 2 5 8

        # empty -- 0
        # player 0 -- 1
        # player 1 -- 2
        self.squares = [0] * 9

    def play_turn(self, agent, pos):
        """Place a mark by the agent in the spot given.

        The following are required for a move to be valid:
        * The agent must be a known agent (either 0 or 1).
        * The spot must be be empty.
        * The spot must be in the board (integer: 0 <= spot <= 8)

        If any of those are not true, a BadTicTacToeMoveException
        will be raised.
        """
        if pos < 0 or pos > 8:
            raise BadTicTacToeMoveException("Invalid move location")
        if agent != 0 and agent != 1:
            raise BadTicTacToeMoveException("Invalid agent")
        if self.squares[pos] != 0:
            raise BadTicTacToeMoveException("Location is not empty")
        if agent == 0:
            self.squares[pos] = 1
        elif agent == 1:
            self.squares[pos] = 2
        return

    def check_for_winner(self):
        """Return the winning player (1 or 2), or -1 if no winner."""
        for indices in self.winning_combinations:
            states = [self.squares[idx] for idx in indices]
            if states == [1, 1, 1]:
                return 1
            if states == [2, 2, 2]:
                return 2
        # no winner found
        return -1

    def check_game_over(self):
        winner = self.check_for_winner()

        if winner == -1 and all(square in [1, 2] for square in self.squares):
            # tie
            return True
        elif winner in [1, 2]:
            return True
        else:
            return False

    def __str__(self):
        return str(self.squares)
