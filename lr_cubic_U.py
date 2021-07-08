import numpy as np 
from sklearn.linear_model import LinearRegression
from hurricane_cubic import Hurricane_cubic
path="/home/jliu447/lossycompression/Hurricane/clean-data-Jinyang"

ratio=2

dataset=Hurricane_cubic(path,"U",1,11,ratio=ratio,global_max=85.17703,global_min=-79.47297)
print("finished reading data")
x=dataset.blocks
y=dataset.regs.flatten()
print("start regression")
reg=LinearRegression(fit_intercept=False).fit(x, y)

print(reg.coef_)
#a=list(reg.coef_).append(0)
#a=np.array(a,dtype=np.float32)
reg.coef_.astype(np.float32).tofile("lr_cubic_U.dat")
