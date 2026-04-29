def print_board(board):
    print("\n")
    print(f" {board[0]} | {board[1]} | {board[2]} ")
    print("---+---+---")
    print(f" {board[3]} | {board[4]} | {board[5]} ")
    print("---+---+---")
    print(f" {board[6]} | {board[7]} | {board[8]} ")
    print("\n")

def check_winner(board, mark):
    win_conditions = [
        [0,1,2], [3,4,5], [6,7,8],  # rows
        [0,3,6], [1,4,7], [2,5,8],  # columns
        [0,4,8], [2,4,6]            # diagonals
    ]
    for condition in win_conditions:
        if all(board[i] == mark for i in condition):
            return True
    return False

def is_draw(board):
    return all(space != ' ' for space in board)

def tic_tac_toe():
    board = [' '] * 9
    current_player = "X"

    print("Welcome to Tic Tac Toe!")
    print_board([str(i+1) for i in range(9)])
    print("Players take turns entering a number 1-9 to place their mark.\n")

    while True:
        print_board(board)
        try:
            move = int(input(f"Player {current_player}, enter your move (1-9): "))
            if move < 1 or move > 9:
                print("Invalid move. Select a number between 1 and 9.")
                continue
            if board[move-1] != ' ':
                print("That spot is already taken. Choose another.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number 1-9.")
            continue

        board[move-1] = current_player

        if check_winner(board, current_player):
            print_board(board)
            print(f"Player {current_player} wins! Congratulations!")
            break
        if is_draw(board):
            print_board(board)
            print("It's a draw!")
            break

        current_player = "O" if current_player == "X" else "X"

if __name__ == "__main__":
    tic_tac_toe()