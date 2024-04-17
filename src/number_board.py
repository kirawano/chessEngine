from const import *
from move import Move
import copy
from piece import *

from dataclasses import dataclass

# TODO utils class with useful methods like int->string for rows and columns


@dataclass
class Move:
    start: tuple = None
    end: tuple
    promotion: int = None

    @classmethod
    def end(cls, end):
        return cls(end=end)

    def with_start(self, start):
        return Move(start=start, end=self.end, promotion=self.promotion)

    def __str__(self):
        return self.simple_str()

    def simple_str(self):
        """
        Displays move using simple notation
        r1c1->r2c2=promotion
        """

        def to_an(square):
            rows = ["8", "7", "6", "5", "4", "3", "2", "1"]
            cols = ["a", "b", "c", "d", "e", "f", "g", "h"]
            r, c = square
            return cols[c] + rows[r]

        def to_piece(piece):
            return [None, None, "N", "B", "R", "Q", "K"][piece]

        return (
            to_an(self.start)
            + "->"
            + to_an(self.end)
            + ("=" + to_piece(self.promotion) if self.promotion else "")
        )
        pass

    @classmethod
    def from_string(cls, string):
        def parse_an(string):
            row_dict = {"8": 0, "7": 1, "6": 2, "5": 3, "4": 4, "3": 5, "2": 6, "1": 7}
            col_dict = {
                "a": 0,
                "b": 1,
                "c": 2,
                "d": 3,
                "e": 4,
                "f": 5,
                "g": 6,
                "h": 7,
            }
            return (row_dict[string[1]], col_dict[string[0]])

        def from_ascii(piece):
            piece_dict = {"N": 2, "B": 3, "R": 4, "Q": 5}
            return piece_dict[piece]

        parts = string.split("=")
        coords = [parse_an(s) for s in parts[0].split("->")]
        if len(coords) != 2:
            print("Error, wrong format. Try again")
        start, end = coords
        promotion = from_ascii(parts[1]) if len(parts) == 2 else None
        return Move(start, end, promotion)


@dataclass
class HistoryMove:
    start: tuple
    end: tuple
    moving: int
    taking: int
    color: int
    old_en_passant: tuple
    old_white_castleable: [bool]
    old_black_castleable: [bool]

    @classmethod
    def fromMoveOn(cls, move, nb):
        return cls(
            move.start,
            move.end,
            nb.at(move.start),
            nb.at(move.end),
            color(nb.at(move.start)),
            nb.en_passant,
            nb.white_castleable[:],
            nb.black_castleable[:],
        )


BLACK_START = 0
WHITE_START = 7
PST = [None, WHITE_START, BLACK_START]  # Piece STart


def color(piece):
    if piece == 0:
        return 0
    return piece // abs(piece)


class NumberBoard:
    def __init__(self, board=None):
        self.en_passant = None  # MUST BE: a tuple of (row, col)
        self.white_castleable = [True, True]
        self.black_castleable = [True, True]
        self.castleable = [None, self.white_castleable, self.black_castleable]
        self.move_number = 0
        self.move_list = []
        if board:
            self.move_number = board.counter
            self.squares = self.from_board(board)
            self.en_passant = board.en_passant
            self.white_castleable = self.castleable_from_board(board, 7)
            self.black_castleable = self.castleable_from_board(board, 0)
            self.castleable = [None, self.white_castleable, self.black_castleable]

    def castleable_from_board(self, board, row):
        def unmoved_piece(cls, sq):
            return sq.has_piece() and isinstance(sq.piece, cls) and not sq.piece.moved

        rl = board.at((row, 0))
        rr = board.at((row, 7))
        k = board.at((row, 4))
        if not (unmoved_piece(King, k)):
            return [False, False]  # king spot does not fufill king not moved reqs
        return [unmoved_piece(Rook, rl), unmoved_piece(Rook, rr)]

    def from_board(self, board):
        number_board = [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        for row in range(ROWS):
            for col in range(COLS):
                p = board.squares[row][col].piece
                number_board[row][col] = p.piece_id if p else 0
        return number_board

    def copy(self):
        nb = NumberBoard()
        nb.squares = [row[:] for row in self.squares]
        nb.en_passant = copy.deepcopy(self.en_passant)
        nb.white_castleable = self.white_castleable[:]
        nb.black_castleable = self.black_castleable[:]
        nb.castleable = [None, nb.white_castleable, nb.black_castleable]
        return nb

    def evaluate_board(self):
        total = 0
        for cols in self.squares:
            for piece in cols:
                total += piece
        return total

    def at(self, square):
        row, col = square
        return self.squares[row][col]

    def put(self, square, piece):
        row, col = square
        self.squares[row][col] = piece

    def _move(self, start, end):
        # start is a (row, col)
        # end is a (row, col)
        moved_piece = self.at(start)
        self.put(end, moved_piece)
        self.put(start, 0)

    def move(self, move):
        hist_move = HistoryMove.fromMoveOn(move, self)
        self.move_list.append(hist_move)
        return self._tuple_move(move.start, move.end, move.promotion)

    def _tuple_move(self, start, end, promotion=None):
        # p is the piece being moved
        # ep is the current en_passant square, when this move was made
        # ir, ic, fr & fc are the initial and final rows and columns
        p = self.at(start)
        ep = self.en_passant  # saved for pawn checks
        ir, ic = start
        fr, fc = end
        self.en_passant = None
        assert p != 0
        self._move(start, end)

        if abs(p) == 1:  # Pawn
            diff = fc - ic
            if diff != 0 and end == ep:
                # If a pawn took onto en_passant square,
                # delete the pawn that was next to it.
                self.put((ir, ic + diff), 0)
            elif abs(fr - ir) == 2:
                self.en_passant = ((fr + ir) // 2, fc)  # avg of start and end is middle
            else:
                pr = [None, 0, 7]  # promotion rows
                if fr == pr[color(p)]:
                    self.put(end, promotion * color(p))
                    # Promote must be positive if it exists (see above assert)
        elif abs(p) == 6:  # King
            self.castleable[color(p)] = [False, False]
            diff = fc - ic
            if abs(diff) == 2:  # king moved 2(sideways). must be a castle
                rc = 0 if diff < 0 else 7  # rook column
                self._tuple_move((ir, rc), (ir, abs(fc - ic // 2)))
                # rook goes to avg of where king was/is
        elif abs(p) == 4:  # Rook
            if (ic == 0 or ic == 7) and ir == PST[color(p)]:  #
                self.castleable[color(p)][(0 if ic == 0 else 1)] = False

    def in_board(self, square):
        row, col = square
        return 0 <= row < 8 and 0 <= col < 8

    def places_in_board(self, places):
        return [p for p in places if self.in_board(p)]

    def calc_moves_no_check(self, square):
        def color(piece):
            if piece == 0:
                return 0
            return piece // abs(piece)

        # calculate all moves for a square
        if self.at(square) == 0:
            return []
        row, col = square
        pcolor = color(self.at(square))

        def pawn():
            def promotion_moves(move):
                pfr = [None, 0, 7]
                r, c = move
                if r == pfr[pcolor]:
                    return [Move(end=(r, c), promotion=p) for p in [2, 3, 4, 5]]
                return [Move.end((r, c))]

            pawn_ranks = [None, 6, 1]
            ends = []
            # row+1, ?row+2, (col+-1, row+1)
            d = -pcolor
            m = (row + d, col)
            if self.in_board(m) and self.at(m) == 0:
                ends.append(m)
                m = (row + (d * 2), col)
                if row == pawn_ranks[pcolor]:
                    if self.at(m) == 0:
                        ends.append(m)
            m = (row + d, col + 1)
            if (
                self.in_board(m)
                and color(self.at(m)) == -pcolor
                or m == self.en_passant
            ):
                ends.append(m)
            m = (row + d, col - 1)
            if (
                self.in_board(m)
                and color(self.at(m)) == -pcolor
                or m == self.en_passant
            ):
                ends.append(m)

            ends = [end for end in ends if self.in_board(end)]
            moves = [promotion_moves(end) for end in ends]
            return [move for ms in moves for move in ms]

        def knight():
            possible_ends = [
                (row + 2, col + 1),
                (row + 2, col - 1),
                (row - 2, col - 1),
                (row - 2, col + 1),
                (row + 1, col + 2),
                (row + 1, col - 2),
                (row - 1, col - 2),
                (row - 1, col + 2),
            ]
            possible_ends = self.places_in_board(possible_ends)
            return [Move.end(e) for e in possible_ends if color(self.at(e)) != pcolor]

        def bishop():
            moves = []
            moves.extend(straight_line_moves((1, 1)))
            moves.extend(straight_line_moves((-1, 1)))
            moves.extend(straight_line_moves((1, -1)))
            moves.extend(straight_line_moves((-1, -1)))
            return moves

        def rook():
            moves = []
            moves.extend(straight_line_moves((1, 0)))
            moves.extend(straight_line_moves((0, 1)))
            moves.extend(straight_line_moves((-1, 0)))
            moves.extend(straight_line_moves((0, -1)))
            return moves

        def queen():
            moves = []
            moves.extend(rook())
            moves.extend(bishop())
            return moves

        def king():
            possible_ends = [
                (row + 1, col - 1),
                (row + 1, col + 0),
                (row + 1, col + 1),
                (row + 0, col - 1),
                (row + 0, col + 1),
                (row - 1, col - 1),
                (row - 1, col + 0),
                (row - 1, col + 1),
            ]

            possible_ends = self.places_in_board(possible_ends)

            if (
                self.castleable[pcolor][0]
                and self.in_board(
                    (row, col - 2)
                )  # should not come up in an actual game, but useful for testing
                and self.at((row, col - 1)) == 0
                and self.at((row, col - 2)) == 0
            ):
                possible_ends.append((row, col - 2))
            if (
                self.castleable[pcolor][1]
                and self.in_board(
                    (row, col + 2)
                )  # should not come up in an actual game, but useful for testing
                and self.at((row, col + 1)) == 0
                and self.at((row, col + 2)) == 0
            ):
                possible_ends.append((row, col + 2))

            return [Move.end(e) for e in possible_ends if (color(self.at(e)) != pcolor)]

        def straight_line_moves(direction):
            ends = []
            drow, dcol = direction
            mrow, mcol = row, col
            mrow += drow
            mcol += dcol
            while self.in_board((mrow, mcol)):
                p = self.at((mrow, mcol))

                if color(p) == 0:
                    ends.append((mrow, mcol))
                elif color(p) == pcolor:
                    break
                elif -1 * color(p) == pcolor:  # p is rival color
                    ends.append((mrow, mcol))
                    break
                mrow += drow
                mcol += dcol
            return [Move.end(e) for e in ends]

        funcs = [lambda: [], pawn, knight, bishop, rook, queen, king]

        return [
            m.with_start(square) for m in funcs[abs(self.at(square))]()
        ]  # if not self.in_check(square, m)

    def calc_moves(self, square):
        # The moves returned here
        moves = self.calc_moves_no_check(square)
        pcolor = color(self.at(square))
        return [m for m in moves if (not self.in_check(m, pcolor))]

    def in_check(self, move, color):
        nb = self.copy()
        nb.move(move)
        for row in range(ROWS):
            for col in range(COLS):
                moves = nb.calc_moves_no_check((row, col))
                for move in moves:
                    p = nb.at(move.end)
                    if p == 6 * color:
                        return True
        return False

    def print(self, guides=False):
        def to_ascii(piece):
            return [".", "P", "N", "B", "R", "Q", "K", "k", "q", "r", "b", "n", "p"][
                piece
            ]

        rows = ["8", "7", "6", "5", "4", "3", "2", "1"]
        cols_header = "  a b c d e f g h\n +----------------"

        y = 0
        if guides:
            print(cols_header)
        for row in self.squares:
            if guides:
                print(rows[y], end="|")
            for piece in row:
                print(to_ascii(piece), end=" ")
            print("")
            y += 1

    def from_string(self, string):
        counter = 0
        d = {
            ".": 0,
            "P": 1,
            "N": 2,
            "B": 3,
            "R": 4,
            "Q": 5,
            "K": 6,
            "k": -6,
            "q": -5,
            "r": -4,
            "b": -3,
            "n": -2,
            "p": -1,
        }
        for token in string.split():
            x = counter % 8
            y = counter // 8
            self.squares[y][x] = d[token]
            counter += 1

    def calc_color_moves(self, pcolor):
        moves = []
        for row in range(ROWS):
            for col in range(COLS):
                p = self.at((row, col))
                if color(p) == pcolor:
                    moves.extend(self.calc_moves((row, col)))
        return moves

    def draw_by_insufficient_material():
        def side_insufficient_material(c, ps):
            cps = [p for p in ps if color(p) == c and abs(p) != 6]
            # Color has more than 2 non-king pieces
            if len(cps) > 2:
                return False
            # Color has 2 knights
            if len(cps) == 2 and all(abs(p) == 2 for p in cps):
                return True
            # Color has 2 pieces, both of which are not knights
            if len(cps) == 2:
                return False
            p = cps[0]  # only one piece
            if abs(p) == 2 or abs(p) == 3:
                return True  # Bishop or knight
            # Color has one piece (non-king), which is not a bishop or a knight
            return False

        # no pawns
        ps = [p for row in self.squares for p in row if p != 0]
        if any(abs(p) == 1 for p in ps):
            return False  # Pawns
        if len(ps) >= 5:
            return False  # At least 5 pieces on the board
        # (There is a possible forced mate)
        # If one side has a king and 2 knights, the other side has a king and one piece
        # each colors pieces, excluding kings
        return side_insufficient_material(1, ps) and side_insufficient_material(-1, ps)

    def take_back(self):
        lm = self.move_list.pop()
        self.put(lm.start, lm.moving)
        self.put(lm.end, lm.taking)
        self.en_passant = lm.old_en_passant
        self.white_castleable = lm.old_white_castleable[:]
        self.black_castleable = lm.old_black_castleable[:]
        self.castleable = [None, self.white_castleable, self.black_castleable]
