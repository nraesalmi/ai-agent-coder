def test_print_board_empty():
    board = [' '] * 9
    print_board(board)

def test_print_board_partial():
    board = ['X', 'O', 'X',
             ' ', 'O', ' ',
             'X', ' ', 'O']
    print_board(board)

def test_print_board_full_x_wins():
    board = ['X', 'X', 'X',
             'O', 'O', 'X',
             'O', 'X', 'O']
    print_board(board)

def test_print_board_numbers():
    board = [str(i) for i in range(1, 10)]
    print_board(board)