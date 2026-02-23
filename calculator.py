#!/usr/bin/env python3
    """A simple command-line calculator."""
    
    import sys
    
    def add(a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(a, b):
        """Subtract b from a."""
        return a - b
    
    def multiply(a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero!")
        return a / b
    
    def calculator():
        """Run the interactive calculator."""
        print("=== Python Calculator ===")
        print("Operations: + (add), - (subtract), * (multiply), / (divide)")
        print("Type 'q' or 'quit' to exit\n")
        
        while True:
            user_input = input("Enter expression (e.g., 5 + 3) or 'q' to quit: ").strip().lower()
            
            if user_input in ('q', 'quit', 'exit'):
                print("Goodbye!")
                break
            
            try:
                # Split input by spaces
                parts = user_input.split()
                
                if len(parts) != 3:
                    print("Error: Please use format: number operator number (e.g., '5 + 3')")
                    continue
                
                num1 = float(parts[0])
                operator = parts[1]
                num2 = float(parts[2])
                
                if operator == '+':
                    result = add(num1, num2)
                elif operator == '-':
                    result = subtract(num1, num2)
                elif operator == '*':
                    result = multiply(num1, num2)
                elif operator == '/':
                    result = divide(num1, num2)
                else:
                    print(f"Error: Unknown operator '{operator}'. Use +, -, *, or /")
                    continue
                
                # Format result (show as int if it's a whole number)
                if result == int(result):
                    print(f"Result: {int(result)}")
                else:
                    print(f"Result: {result}")
                    
            except ValueError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error: Invalid input. {e}")
    
    def calculate(expr):
        """Calculate a simple expression.
        
        Usage: calculate("5 + 3")  # Returns 8
        """
        try:
            parts = expr.split()
            if len(parts) != 3:
                raise ValueError("Expression must be: number operator number")
            
            num1 = float(parts[0])
            operator = parts[1]
            num2 = float(parts[2])
            
            if operator == '+':
                return add(num1, num2)
            elif operator == '-':
                return subtract(num1, num2)
            elif operator == '*':
                return multiply(num1, num2)
            elif operator == '/':
                return divide(num1, num2)
            else:
                raise ValueError(f"Unknown operator: {operator}")
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    if __name__ == "__main__":
        calculator()
    