import numpy as np 
from sklearn.linear_model import LinearRegression
from nyx import NYX
import sys
path="/home/jliu447/lossycompression/NYX"
field="baryon_density"
if len(sys.argv)>=2:
    level=int(sys.argv[1])
else:
    level=2
if len(sys.argv)>=3:
    ratio=int(sys.argv[2])
else:
    ratio=1
if len(sys.argv)>=4:
    outfile=sys.argv[3]
else:
    outfile="lr_b.dat"

dataset=NYX(path,field,0,3,level=level,ratio=ratio,log=1)
print("finished reading data")
x=dataset.blocks.astype(np.double)
y=dataset.regs.astype(np.double).flatten()
print("start regression")
reg=LinearRegression(fit_intercept=False).fit(x, y)

print(reg.coef_)
reg.coef_.tofile(outfile)
