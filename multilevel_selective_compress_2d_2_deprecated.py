import numpy as np 

import os
import argparse
import torch
import torch.nn as nn
from sklearn.linear_model import LinearRegression
import math
def quantize(data,pred,error_bound):
    radius=32768
    
    diff = data - pred
    quant_index = (int) (abs(diff)/ error_bound) + 1
    #print(quant_index)
    if (quant_index < radius * 2) :
        quant_index =quant_index>> 1
        half_index = quant_index
        quant_index =quant_index<< 1
        #print(quant_index)
        quant_index_shifted=0
        if (diff < 0) :
            quant_index = -quant_index
            quant_index_shifted = radius - half_index
        else :
            quant_index_shifted = radius + half_index
        
        decompressed_data = pred + quant_index * error_bound
        #print(decompressed_data)
        if abs(decompressed_data - data) > error_bound :
            #print("b")
            return 0,data
        else:
            #print("c")
            data = decompressed_data
            return quant_index_shifted,data
        
    else:
        #print("a")
        return 0,data

parser = argparse.ArgumentParser()

parser.add_argument('--error','-e',type=float,default=1e-3)
parser.add_argument('--input','-i',type=str)
parser.add_argument('--output','-o',type=str)

parser.add_argument('--max_step','-s',type=int,default=-1)
parser.add_argument('--rate','-r',type=float,default=1.0)
parser.add_argument('--maximum_rate','-m',type=float,default=10.0)
parser.add_argument('--cubic','-c',type=bool,default=False)
#parser.add_argument('--level_rate','-lr',type=float,default=1.0)
parser.add_argument('--anchor_rate','-a',type=float,default=0)

parser.add_argument('--size_x','-x',type=float,default=1800)
parser.add_argument('--size_y','-y',type=float,default=3600)
#parser.add_argument('--level','-l',type=int,default=2)
#parser.add_argument('--noise','-n',type=bool,default=False)
#parser.add_argument('--intercept','-t',type=bool,default=False)
args = parser.parse_args()

size_x=args.size_x
size_y=args.size_y
array=np.fromfile(args.input,dtype=np.float32).reshape((size_x,size_y))
rng=(np.max(array)-np.min(array))
error_bound=args.error*rng
max_step=args.max_step
rate=args.rate



qs=[]

us=[]
lorenzo_qs=[]

#anchor=args.anchor
if max_step>0:
    max_level=int(math.log(max_step,2))
    anchor_rate=args.anchor_rate
    if anchor_rate>0:
        anchor_eb=error_bound/anchor_rate
        print("Anchor eb:%f" % anchor_eb)
 
   
        for x in range(0,size_x,max_step):
            for y in range(0,size_y,max_step):
            
                orig=array[x][y]
        
                f_01=array[x-max_step][y] if x else 0
                f_10=array[x][y-max_step] if y else 0
            
                f_00=array[x-max_step][y-max_step] if x and y else 0
                
                pred=f_01+f_10-f_00
                
        
                
                q,decomp=quantize(orig,pred,anchor_eb)
                qs.append(q)
                if q==0:
                    us.append(decomp)
                array[x][y]=decomp
else:
    pass#todo,some preparations before level start
#print(len(qs))

last_x=((size_x-1)//max_step)*max_step
last_y=((size_y-1)//max_step)*max_step   
step=max_step//2
level=max_level-1
while step>0:#currently no recursive lorenzo
    cur_qs=[]
    cur_us=[]
    cur_eb=error_bound/min(args.maximum_rate,(rate**level))
    cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])
    cur_size_x,cur_size_y=cur_array.shape
    #print(cur_size_x,cur_size_y)
    print("Level %d started. Current step: %d. Current error_bound: %s." % (level,step,cur_eb))
    best_preds=None#need to copy
    best_absloss=None
    best_qs=[]#need to copy
    best_us=[]#need to copy

    #linear interp
    absloss=0
    selected_algo="none"
    for x in range(1,cur_size_x,2):
        for y in range(1,cur_size_y,2):
            if x==cur_size_x-1 or y==cur_size_y-1:
                continue
            orig=cur_array[x][y]
            pred=(cur_array[x-1][y-1]+cur_array[x-1][y+1]+cur_array[x+1][y-1]+cur_array[x+1][y+1])/4
            absloss+=abs(orig-pred)
            q,decomp=quantize(orig,pred,cur_eb)
            
            cur_qs.append(q)
            if q==0:
                cur_us.append(decomp)
                #absloss+=abs(decomp)
            cur_array[x][y]=decomp
    for x in range(0,cur_size_x):
        for y in range(1-(x%2),cur_size_y,2):
            if x==cur_size_x-1 or y==cur_size_y-1:
                continue
            orig=cur_array[x][y]
            if x and y:
                pred=(cur_array[x][y-1]+cur_array[x][y+1]+cur_array[x-1][y]+cur_array[x+1][y])/4
            elif x==0:
                pred=(cur_array[x][y-1]+cur_array[x][y+1])/2
            else:
                pred=(cur_array[x-1][y]+cur_array[x+1][y])/2
            absloss+=abs(orig-pred)
            q,decomp=quantize(orig,pred,cur_eb)
            cur_qs.append(q)
            

            if q==0:
                cur_us.append(decomp)
                #absloss+=abs(decomp)
            cur_array[x][y]=decomp     
    
    
    

    best_preds=np.copy(cur_array)
    best_absloss=absloss
    best_qs=cur_qs.copy()
    best_us=cur_us.copy()
    selected_algo="interp_multidim"
    #cubic interp
    
    #lorenzo
    cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
    absloss=0
    cur_qs=[]
    cur_us=[]
    for x in range(cur_size_x):
        for y in range(1-(x%2),cur_size_y,2-(x%2)):
            orig=cur_array[x][y]
        
            f_01=cur_array[x-1][y] if x else 0
            f_10=cur_array[x][y-1] if y else 0
            
            f_00=cur_array[x-1][y-1] if x and y else 0
                
            pred=f_01+f_10-f_00
                
        
            absloss+=abs(orig-pred)
            q,decomp=quantize(orig,pred,cur_eb)
            cur_qs.append(q)
            
            if q==0:
                cur_us.append(decomp)
                #absloss+=abs(decomp)
            cur_array[x][y]=decomp
    #print(np.max(np.abs(array[0:last_x+1:step,0:last_y+1:step]-cur_array)))
    if absloss<best_absloss:
        best_preds=np.copy(cur_array)
        best_absloss=absloss
        best_qs=cur_qs.copy()
        best_us=cur_us.copy()
        selected_algo="lorenzo"
    mean_l1_loss=best_absloss/best_preds.size
    #print(np.max(np.abs(array[0:last_x+1:step,0:last_y+1:step]-best_preds)))
    array[0:last_x+1:step,0:last_y+1:step]=best_preds
    qs+=best_qs
    us+=best_us
    #print(len(qs))
    print ("Level %d finished. Selected algorithm: %s. Mean prediction abs loss: %f." % (level,selected_algo,mean_l1_loss))
    step=step//2
    level-=1



def lorenzo_2d(array,x_start,x_end,y_start,y_end):
    for x in range(x_start,x_end):
        for y in range(y_start,y_end):

            orig=array[x][y]
        
            f_01=array[x-1][y] if x else 0
            f_10=array[x][y-1] if y else 0
            
            f_00=array[x-1][y-1] if x and y else 0
                
            pred=f_01+f_10-f_00
                
        
                
            q,decomp=quantize(orig,pred,error_bound)
            lorenzo_qs.append(q)
            if q==0:
                us.append(decomp)
            array[x][y]=decomp
lorenzo_2d(array,0,last_x+1,last_y+1,size_y)
lorenzo_2d(array,last_x+1,size_x,0,size_y)




 






quants=np.concatenate( (np.array(lorenzo_qs,dtype=np.int32),np.array(qs,dtype=np.int32) ) )
unpreds=np.array(us,dtype=np.float32)
array.tofile(args.output)
quants.tofile("ml2_q.dat")
unpreds.tofile("ml2_u.dat")