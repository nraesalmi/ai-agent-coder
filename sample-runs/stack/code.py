class Product:
    def __init__(self, name: str, price: float, quantity: int = 1):
        self.name = name
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return f"Product(name={self.name!r}, price={self.price}, quantity={self.quantity})"


class Stack:
    def __init__(self):
        self._items = []

    def is_empty(self) -> bool:
        """Check if the stack is empty"""
        return len(self._items) == 0

    def push(self, item: Product):
        """Push a product onto the stack"""
        self._items.append(item)

    def pop(self) -> Product:
        """Remove and return the top product from the stack."""
        if self.is_empty():
            raise IndexError("Pop from empty stack")
        return self._items.pop()

    def peek(self) -> Product:
        """Return the top product without removing it."""
        if self.is_empty():
            raise IndexError("Peek from empty stack")
        return self._items[-1]

    def size(self) -> int:
        """Return number of products in the stack."""
        return len(self._items)

    def clear(self):
        """Remove all products from the stack"""
        self._items.clear()

    def __repr__(self):
        return f"Stack({self._items})"


# Example usage:
if __name__ == "__main__":
    stack = Stack()
    
    stack.push(Product("Apple", 0.5, 10))
    stack.push(Product("Milk", 1.2, 2))
    stack.push(Product("Bread", 1.0))
    
    print(f"Stack size: {stack.size()}")
    print("Top product:", stack.peek())
    
    popped = stack.pop()
    print(f"Popped product: {popped}")
    print(f"Stack after popping: {stack}")