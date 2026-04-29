class FruitStack:
    def __init__(self):
        """
        Initialize an empty stack to store fruits.
        """
        self.stack = []

    def is_empty(self):
        """
        Check if the stack is empty.

        Returns:
            bool: True if stack is empty, False otherwise.
        """
        return len(self.stack) == 0

    def push(self, fruit):
        """
        Add a fruit to the top of the stack.

        Args:
            fruit (str): The name of the fruit to add.

        Raises:
            ValueError: If fruit is not a non-empty string.
        """
        if not isinstance(fruit, str):
            raise ValueError("Fruit must be a string.")
        if fruit.strip() == "":
            raise ValueError("Fruit name cannot be empty or whitespace.")
        self.stack.append(fruit)
        print(f"Pushed '{fruit}' onto the stack.")

    def pop(self):
        """
        Remove and return the top fruit from the stack.

        Returns:
            str: The fruit at the top of the stack.

        Raises:
            IndexError: If the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Cannot pop from an empty stack.")
        fruit = self.stack.pop()
        print(f"Popped '{fruit}' from the stack.")
        return fruit

    def peek(self):
        """
        Return the top fruit without removing it from the stack.

        Returns:
            str: The fruit at the top of the stack.

        Raises:
            IndexError: If the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Cannot peek at an empty stack.")
        return self.stack[-1]

    def size(self):
        """
        Return the number of fruits in the stack.

        Returns:
            int: The size of the stack.
        """
        return len(self.stack)

    def clear(self):
        """
        Clear all fruits from the stack.
        """
        self.stack.clear()
        print("Cleared the stack.")

    def __str__(self):
        """
        Return a string representation of the stack from bottom to top.

        Returns:
            str: String showing the stack contents.
        """
        if self.is_empty():
            return "FruitStack is empty."
        else:
            return "FruitStack (bottom->top): " + " -> ".join(self.stack)


# Example usage:
if __name__ == "__main__":
    fruit_stack = FruitStack()

    # Adding fruits
    fruit_stack.push("Apple")
    fruit_stack.push("Banana")
    fruit_stack.push("Cherry")

    print(fruit_stack)

    # Peek top fruit
    try:
        top_fruit = fruit_stack.peek()
        print(f"Top fruit is: {top_fruit}")
    except IndexError as e:
        print(e)

    # Pop fruits
    try:
        fruit_stack.pop()
        fruit_stack.pop()
        fruit_stack.pop()
        # This pop will raise exception since stack is empty now
        fruit_stack.pop()
    except IndexError as e:
        print(f"Error: {e}")

    print(fruit_stack)

    # Clear the stack (already empty)
    fruit_stack.clear()

    # Trying to push invalid fruits
    try:
        fruit_stack.push("")  # Should raise ValueError
    except ValueError as e:
        print(f"Error: {e}")

    try:
        fruit_stack.push(123)  # Should raise ValueError
    except ValueError as e:
        print(f"Error: {e}")