import numpy as np 
from sklearn.linear_model import LinearRegression
from nyx_cubic import NYX_cubic
path="/home/jliu447/lossycompression/NYX"
field="baryon_density"
ratio=1

dataset=NYX_cubic(path,field,0,1,ratio=ratio,log=1)
print("finished reading data")
x=dataset.blocks.astype(np.float64)
y=dataset.regs.astype(np.float64).flatten()
print("start regression")
reg=LinearRegression(fit_intercept=False).fit(x, y)

print(reg.coef_)
#a=list(reg.coef_).append(0)
#a=np.array(a,dtype=np.float32)
reg.coef_.astype(np.float32).tofile("lr_cubic_b.dat")
