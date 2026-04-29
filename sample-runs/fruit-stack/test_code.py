def test_is_empty_on_new_stack():
    stack = FruitStack()
    assert stack.is_empty() == True

def test_is_empty_after_push():
    stack = FruitStack()
    stack.push("Apple")
    assert stack.is_empty() == False

def test_is_empty_after_pop_to_empty():
    stack = FruitStack()
    stack.push("Banana")
    stack.pop()
    assert stack.is_empty() == True

def test_is_empty_after_clear():
    stack = FruitStack()
    stack.push("Cherry")
    stack.push("Date")
    stack.clear()
    assert stack.is_empty() == True

def test_is_empty_after_multiple_push_and_pop():
    stack = FruitStack()
    fruits = ["Apple", "Banana", "Cherry"]
    for fruit in fruits:
        stack.push(fruit)
    assert stack.is_empty() == False

    for _ in fruits:
        stack.pop()
    assert stack.is_empty() == True