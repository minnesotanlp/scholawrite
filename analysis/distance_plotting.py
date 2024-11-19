import pandas as pd
import matplotlib.pyplot as plt
import plotting

fname = "project_{}_label_w_dist.csv"

for i in range(5):
  f = fname.format(i)

  #df = pd.read_csv(f, header=0)
  plotting.plot_distance(f, i + 1)

  
