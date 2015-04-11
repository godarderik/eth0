import csv
import numpy as np
import matplotlib.pyplot as plt

with open('data.csv', 'r') as fh:
	csvfile = csv.reader(fh)

	data = []
	for row in csvfile:
		data.append(row[0])

	print(len(data))
	plt.plot(data)
	plt.show()