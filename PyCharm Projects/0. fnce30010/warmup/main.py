"""
Warmup python exercises
"""
import random
import time


def surface_area_pyramid(base, height):
    # calculate and return the surface area
    return base**2 + 2*base*(base**2 / 4 + height**2)**0.5


def ackermann_peter_function(m, n):
    # calculate and return the value of Ackermann-Peter function

    if (m < 0) or (n < 0):
        return

    if m == 0:
        return n+1
    elif (m>0) and (n==0):
        return ackermann_peter_function(m-1,1)
    elif (m>0) and (n>0):
        return ackermann_peter_function(m-1, ackermann_peter_function(m, n-1))


def check_palindrome(some_input):
    # print the reasoning!

    some_input = ''.join([x for x in some_input if x.isalpha()])
    l = 0
    r = len(some_input) - 1

    while l <= r:
        if some_input[l].lower() == some_input[r].lower():
            print(some_input[l:r+1])
        else:
            return

        l += 1
        r -= 1

    return "String is too short!"


def status_quo(units, prices):
    # calculate and return the status of portfolio!
    output = [units[x] * prices[x] for x in range(len(units))]

    return output, sum(output)


def birthday_sharing_probability(num_people, num_trials):
    # we need to run some simulations
    num_matches = 0

    # num_trials number of simulations
    for i in range(num_trials):
        matches = {}

        # 1 simulation
        i = 0
        while i < num_people:
            # 366 days to account for leap years
            birthdate = random.randint(1, 366)

            if birthdate not in matches:
                matches[birthdate] = 0
            else:
                num_matches += 1
                break

            i += 1

    return num_matches / num_trials


def monty_hall_strategy(num_doors, switch, num_trials):
    # we need to run some simulations. let switch be boolean
    wins = 0

    for i in range(num_trials):
        wins += monty_hall_simulation(num_doors, switch, num_trials)

    return wins/num_trials


def monty_hall_simulation(num_doors, switch, num_trials):
    # 1 simulation
    win = random.randint(1, num_doors)
    choice = random.randint(1, num_doors)

    # if witching
    if switch:
        # host needs to pick ONE door that remains closed
        host_pick = random.randint(1, num_doors)

        # if contestant chose goat, host must keep car door closed
        if win != choice:
            host_pick = win

        # if contestant chose car, host can keep any other random door closed
        else:
            # this ensures that the host does not pick the same door as contestant
            while host_pick == choice:
                host_pick = random.randint(1, num_doors)

        # contestant switches in this strategy
        choice = host_pick

    # if contestant chose right, win
    if win == choice:
        return 1
    else:
        return 0


def console_menu():

    # display menu
    def display():
        print("Hi There! The following functions are on the menu today:"
              "\n1) Python Pyramids"
              "\n2) Ackermann-Peter function"
              "\n3) Python Palindromes"
              "\n4) Status Quo!"
              "\n5) Birthday Problem Solver"
              "\n6) Monty Hall Strategy Evaluation"
              "\n7) Exit")

    display()
    user_input = 0

    # keep running program till exit
    while user_input != 7:
        user_input = input("Please make a selection: ")

        # try casting input to int, if it works proceed, otherwise loop back to start
        try:
            user_input = int(user_input)

            # valid integer entered
            if (user_input >= 1) and (user_input <= 7):
                # cases
                if user_input == 1:
                    base = input("Enter base: ")
                    height = input("Enter height: ")
                    print(surface_area_pyramid(int(base), int(height)))

                elif user_input == 2:
                    m = input("Enter m: ")
                    n = input("Enter n: ")
                    print(ackermann_peter_function(int(m), int(n)))

                elif user_input == 3:
                    text = input("Enter text to be palindromed: ")
                    check_palindrome(text)

                elif user_input == 5:
                    num_people = input("Enter number of people: ")
                    num_trials = input("Enter number of trials: ")
                    print(birthday_sharing_probability(int(num_people), int(num_trials)))

                elif user_input == 6:
                    flag = False
                    num_doors = input("How many doors are there? ")
                    strat = input("Is your strategy to switch? y or n? ")
                    if strat == "y":
                        flag = True
                    num_trials = input("How many times do you want to play? ")

                    print("Your win ratio will be:", monty_hall_strategy(int(num_doors), flag, int(num_trials)))

                elif user_input == 4:
                    units = []
                    prices = []

                    unit = '0'
                    while len(unit) > 0:
                        unit = input("Enter units one by one: ")
                        if unit.isnumeric():
                            units.append(int(unit))
                        else:
                            if len(unit) > 0:
                                print("Enter a positive integer!")

                    price = '0'
                    while len(price) > 0:
                        price = input("Enter prices one stock at a time: ")
                        try:
                            prices.append(float(price))
                        except ValueError:
                            if len(price) > 0:
                                print("Enter a positive float!")

                    print(status_quo(units, prices))

            # invalid integer entered
            else:
                print("Bye Bye!")
                return

            if user_input == 7:
                return

            time.sleep(5)
            display()

        except ValueError:
            pass


if __name__ == '__main__':
    console_menu()

    '''
    Testing - Passes 6/6 use cases
    
    # 1 - Surface Area of Pyramid
    print("# 1 - Surface Area of Pyramid")
    for b, h in [(2, 2), (4, 8)]:
        print(surface_area_pyramid(b, h))

    # 2 - Ackermann Peter Function
    print("\n# 2 - Ackermann Peter Function")
    print(ackermann_peter_function(3,5))

    # 3 - Check palindrome
    print("\n# 3 - Check palindrome")
    print(check_palindrome("Madam, I am not Adam"))

    # 4 - Status quo
    print("\n# 4 - Status quo")
    print(status_quo([10, 12, 5], [10.2, 20, 3.5]))

    # 5 - Birthday Matches
    print("\n# 5 - Birthday Matches")
    print(birthday_sharing_probability(23, 10000))

    # 6 - Monty Hall
    print("\n# 6 - Monty Hall")
    print("With No Switch" , monty_hall_strategy(100, False, 1000000), "%")
    print("With Switch", monty_hall_strategy(100, True, 1000000), "%")
    '''

