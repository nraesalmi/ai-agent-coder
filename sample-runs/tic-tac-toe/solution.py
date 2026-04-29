def print_board(board):
    print("Current Board:")
    for i, row in enumerate(board):
        print(" | ".join(row))
        if i < 2:
            print("---------")

def check_winner(board, player):
    # Check rows
    for row in board:
        if all(s == player for s in row):
            return True
    # Check columns
    for col in range(3):
        if all(board[row][col] == player for row in range(3)):
            return True
    # Check diagonals
    if all(board[i][i] == player for i in range(3)):
        return True
    if all(board[i][2 - i] == player for i in range(3)):
        return True
    return False

def is_board_full(board):
    return all(all(cell != " " for cell in row) for row in board)

def tic_tac_toe():
    board = [[" " for _ in range(3)] for _ in range(3)]
    current_player = "X"
    
    while True:
        print_board(board)
        print(f"Player {current_player}, enter your move (row and column: 1 2):")
        
        try:
            row, col = map(int, input().split())
            if row < 1 or row > 3 or col < 1 or col > 3:
                print("Invalid coordinates. Please enter row and column between 1 and 3.")
                continue
            if board[row-1][col-1] != " ":
                print("Cell already taken. Choose another one.")
                continue
            board[row-1][col-1] = current_player
        except ValueError:
            print("Invalid input. Please enter two numbers separated by space.")
            continue

        if check_winner(board, current_player):
            print_board(board)
            print(f"Player {current_player} wins!")
            break
        
        if is_board_full(board):
            print_board(board)
            print("It's a tie!")
            break
        
        current_player = "O" if current_player == "X" else "X"

if __name__ == "__main__":
    tic_tac_toe()