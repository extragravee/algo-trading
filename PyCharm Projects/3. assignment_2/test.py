import numpy as np
import time
import itertools

payoffs = {'A': [1000, 0, 750, 250], 'B': [0, 250, 750, 100],
           'C': [0, 750, 250, 1000], 'Note': [500, 500, 500, 500]}
# print(list(payoffs.values()))

temp = [[1, 'A'], [2, 'B'], [3, 'C'], [4, 'A']]


def duplicates_in_list(comb1):
    temp1 = [x[1] for x in comb1]

    return len(set(temp1)) == len(temp1)

valid_combinations = []

print("all=====================")
for i in range(1, len(temp)+1):
    combs = list(itertools.combinations(temp, i))
    valid_combinations += filter(duplicates_in_list, combs)
    # for comb in combs:
    #     if not duplicates_in_list(comb):
    #         valid_combinations.append(comb)
    print(combs)
print("all=====================")
# print(valid_combinations)
for combination in valid_combinations:
    print(combination)
