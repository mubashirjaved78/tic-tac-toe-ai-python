import math

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   
    (0, 4, 8), (2, 4, 6),              
]


def empty_board():
    return [None] * 9


def opponent(mark):
    return 'O' if mark == 'X' else 'X'


def winner(board):
    for line in WIN_LINES:
        a, b, c = line
        if board[a] is not None and board[a] == board[b] == board[c]:
            return board[a], line
    return None, None


def is_full(board):
    return all(cell is not None for cell in board)


def legal_moves(board):
    return [i for i, cell in enumerate(board) if cell is None]


def game_status(board):
    w, _ = winner(board)
    if w:
        return 'win'
    if is_full(board):
        return 'draw'
    return 'ongoing'


def apply_move(board, index, mark):
    new_board = board[:]
    new_board[index] = mark
    return new_board


def _score(board, depth, ai_mark):
    w, _ = winner(board)
    if w == ai_mark:
        return 10 - depth
    elif w == opponent(ai_mark):
        return depth - 10
    return 0


def _minimax(board, depth, alpha, beta, maximizing, ai_mark):
    status = game_status(board)
    if status != 'ongoing':
        return _score(board, depth, ai_mark)

    current_mark = ai_mark if maximizing else opponent(ai_mark)

    if maximizing:
        best = -math.inf
        for move in legal_moves(board):
            nb = apply_move(board, move, current_mark)
            val = _minimax(nb, depth + 1, alpha, beta, False, ai_mark)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = math.inf
        for move in legal_moves(board):
            nb = apply_move(board, move, current_mark)
            val = _minimax(nb, depth + 1, alpha, beta, True, ai_mark)
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def best_move(board, ai_mark, difficulty='hard'):
    import random
    moves = legal_moves(board)
    if not moves:
        return None
    if len(moves) == 9:
        return 4

    if difficulty == 'easy' and random.random() < 0.70:
        return random.choice(moves)
    if difficulty == 'medium' and random.random() < 0.35:
        return random.choice(moves)

    best_val = -math.inf
    chosen = moves[0]
    alpha, beta = -math.inf, math.inf
    for move in moves:
        nb = apply_move(board, move, ai_mark)
        val = _minimax(nb, 1, alpha, beta, False, ai_mark)
        if val > best_val:
            best_val = val
            chosen = move
        alpha = max(alpha, best_val)
    return chosen
