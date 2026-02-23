import unittest

class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):
        return a * b
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()
    def test_add(self):
        self.assertEqual(self.calc.add(2, 2), 4)
        self.assertEqual(self.calc.add(-2, 2), 0)
        self.assertEqual(self.calc.add(-2, -2), -4)
    def test_subtract(self):
        self.assertEqual(self.calc.subtract(2, 2), 0)
        self.assertEqual(self.calc.subtract(-2, 2), -4)
        self.assertEqual(self.calc.subtract(-2, -2), 0)
    def test_multiply(self):
        self.assertEqual(self.calc.multiply(2, 2), 4)
        self.assertEqual(self.calc.multiply(-2, 2), -4)
        self.assertEqual(self.calc.multiply(-2, -2), 4)
    def test_divide(self):
        self.assertEqual(self.calc.divide(2, 2), 1)
        self.assertEqual(self.calc.divide(-2, 2), -1)
        self.assertEqual(self.calc.divide(-2, -2), 1)
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(2, 0)

if __name__ == '__main__':
    unittest.main()