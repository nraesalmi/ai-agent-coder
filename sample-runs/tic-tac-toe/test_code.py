import pytest
from solution import print_board, check_winner, is_board_full

def test_check_winner_rows():
    board = [
        ["X", "X", "X"],
        ["O", " ", "O"],
        [" ", "O", " "]
    ]
    assert check_winner(board, "X") is True
    assert check_winner(board, "O") is False

def test_check_winner_columns():
    board = [
        ["O", "X", " "],
        ["O", "X", " "],
        ["O", " ", "X"]
    ]
    assert check_winner(board, "O") is True
    assert check_winner(board, "X") is False

def test_check_winner_diagonals():
    board1 = [
        ["X", "O", " "],
        ["O", "X", "O"],
        [" ", " ", "X"]
    ]
    board2 = [
        ["O", "X", "X"],
        [" ", "O", " "],
        ["X", " ", "O"]
    ]
    assert check_winner(board1, "X") is True
    assert check_winner(board2, "O") is True

def test_check_winner_none():
    board = [
        ["X", "O", "X"],
        ["O", "X", "O"],
        ["O", "X", "O"]
    ]
    assert check_winner(board, "X") is False
    assert check_winner(board, "O") is False

def test_is_board_full_true():
    board = [
        ["X", "O", "X"],
        ["O", "X", "O"],
        ["O", "X", "O"]
    ]
    assert is_board_full(board) is True

def test_is_board_full_false():
    board = [
        ["X", "O", "X"],
        ["O", " ", "O"],
        ["O", "X", " "]
    ]
    assert is_board_full(board) is False

def test_print_board(capsys):
    board = [
        ["X", "O", "X"],
        ["O", "X", "O"],
        ["O", "X", " "]
    ]
    print_board(board)
    captured = capsys.readouterr()
    expected_output = (
        "Current Board:\n"
        "X | O | X\n"
        "---------\n"
        "O | X | O\n"
        "---------\n"
        "O | X |  \n"
    )
    assert captured.out == expected_output