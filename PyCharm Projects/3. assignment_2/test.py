import numpy as np
import time

payoffs = {'A': [1000, 0, 750, 250], 'B': [0, 250, 750, 100], 'C': [0, 750, 250, 1000], 'Note': [500, 500, 500, 500]}
# print(list(payoffs.values()))
y = 0

# test 1
start_time = time.time()
for i in range(10000):
    y = np.cov(list(payoffs.values()), bias=True)
    # print(y)
    # print(x)
    # print(np.var([1000, 0, 750, 250]))
# print(y)
print(f"Avg time taken: {(time.time() - start_time)/100000}")

# test 2
# start_time = time.time()
# for i in range(10000):
#     y = np.cov(np.array(list(payoffs.values())), bias=True)
#     # print(y)
#     # print(x)
#     # print(np.var([1000, 0, 750, 250]))
# # print(y)
# print(f"Avg time taken: {(time.time() - start_time)/100000}")