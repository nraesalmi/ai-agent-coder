import unittest
from code import Stack, Product  # Replace 'code' with the actual module name


class TestStackIsEmpty(unittest.TestCase):

    def test_empty_stack_is_empty(self):
        stack = Stack()
        self.assertTrue(stack.is_empty())

    def test_stack_with_one_item_is_not_empty(self):
        stack = Stack()
        stack.push(Product("Apple", 0.5, 10))
        self.assertFalse(stack.is_empty())

    def test_stack_after_pop_becomes_empty(self):
        stack = Stack()
        stack.push(Product("Milk", 1.2, 2))
        stack.pop()
        self.assertTrue(stack.is_empty())

    def test_stack_after_push_and_clear_is_empty(self):
        stack = Stack()
        stack.push(Product("Bread", 1.0))
        stack.clear()
        self.assertTrue(stack.is_empty())

    def test_stack_with_multiple_items_is_not_empty(self):
        stack = Stack()
        stack.push(Product("Apple", 0.5, 10))
        stack.push(Product("Milk", 1.2, 2))
        stack.push(Product("Bread", 1.0))
        self.assertFalse(stack.is_empty())