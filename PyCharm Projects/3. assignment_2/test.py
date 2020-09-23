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
for i in range(1, len(temp) + 1):
    combs = list(itertools.combinations(temp, i))
    new_set = filter(duplicates_in_list, combs)

    print("New set")
    for order in new_set:
        print(order)

    valid_combinations += new_set
    # for comb in combs:
    #     if not duplicates_in_list(comb):
    #         valid_combinations.append(comb)

# for order in valid_combinations:
#     print(order)
