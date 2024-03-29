import numpy as np 

import os
import argparse
#import torch
#import torch.nn as nn
from sklearn.linear_model import LinearRegression
import math
import random
from utils import *
import time
def msc2d(array,error_bound,rate,maximum_rate,min_coeff_level,max_step,anchor_rate,rate_list=None,x_preded=False,y_preded=False,sz3_interp=False,multidim_level=10,lorenzo=-1,\
sample_rate=0.05,min_sampled_points=10,new_q_order=0,random_access=False,verbose=False,fix_algo="none",fix_algo_list=None,first_level=None,last_level=0,fake_compression=False):#lorenzo:only check lorenzo fallback with level no larger than lorenzo level

    size_x,size_y=array.shape
    #array=np.fromfile(args.input,dtype=np.float32).reshape((size_x,size_y))
    if lorenzo>=0:
        orig_array=np.copy(array)
    if random_access and lorenzo>=0:
        lorenzo=0
    #error_bound=args.error*rng
    #max_step=args.max_step
    #rate=args.rate
    max_level=int(math.log(max_step,2))
    selected_algos=[]


    qs=[ [] for i in range(max_level+1)]

    us=[]
    edge_qs=[]
#min_coeff_level=args.min_coeff_level
#anchor=args.anchor
    if anchor_rate>0:
        anchor_eb=error_bound/anchor_rate
    else:
        anchor_eb=0
    startx=max_step if x_preded else 0
    starty=max_step if y_preded else 0
    if (first_level==None or max_level==first_level+1) and anchor_rate>0:
    
    #anchor_rate=args.anchor_rate
        
        if verbose:
            print("Anchor eb:%f" % anchor_eb)

        if max_level>=min_coeff_level:
            reg_xs=[]
            reg_ys=[]
            for x in range(max_step,size_x,max_step):
                for y in range(max_step,size_y,max_step):
                    reg_xs.append(np.array([array[x-max_step][y-max_step],array[x-max_step][y],array[x][y-max_step]],dtype=np.float64))
                    reg_ys.append(array[x][y])
                    res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                    coef=res.coef_ 
                    ince=res.intercept_

        
        

        for x in range(startx,size_x,max_step):
            for y in range(starty,size_y,max_step):
                orig=array[x][y]
                if x and y and max_level>=min_coeff_level:
                    reg_block=np.array([array[x-max_step][y-max_step],array[x-max_step][y],array[x][y-max_step]],dtype=np.float64)
                    pred=np.dot(reg_block,coef)+ince

            
                
                else:
                    f_01=array[x-max_step][y] if x else 0
                    f_10=array[x][y-max_step] if y else 0
            
                    f_00=array[x-max_step][y-max_step] if x and y else 0
                
                    pred=f_01+f_10-f_00
                
        
                
                q,decomp=quantize(orig,pred,anchor_eb)
                qs[max_level].append(q)
                if q==0:
                    us.append(decomp)
                array[x][y]=decomp 
    
    elif (first_level==None or max_level==first_level+1) and anchor_rate==0:
        pass
        '''
        for x in range(startx,size_x,max_step):
            for y in range(starty,size_y,max_step):
                orig=array[x][y]
                us.append(orig)
        '''
#print(len(qs))

    last_x=((size_x-1)//max_step)*max_step
    last_y=((size_y-1)//max_step)*max_step   
    step=max_step//2
    if first_level==None:
        first_level=max_level-1
    level=max_level-1
    #maxlevel_q_start=len(qs[max_level])
    u_start=len(us)
    cumulated_loss=0.0
    loss_dict=[{} for i in range(max_level)]
    while level>=last_level:#step>0:
        if level>first_level:
            level-=1
            step=step//2
            continue
        cur_qs=[]
        cur_us=[]
        if rate_list!=None:
            cur_eb=error_bound/rate_list[level]
        else:
            cur_eb=error_bound/min(maximum_rate,(rate**level))
        cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])
        cur_size_x,cur_size_y=cur_array.shape
    #print(cur_size_x,cur_size_y)
        if verbose:
            print("Level %d started. Current step: %d. Current error_bound: %s." % (level,step,cur_eb))
        best_preds=None#need to copy
        best_absloss=None
        best_qs=[]#need to copy
        best_us=[]#need to copy
        xstart=2 if x_preded else 0
        ystart=2 if y_preded else 0
    #linear interp
        absloss=0
        selected_algo="none"
        if fix_algo_list!=None:
            fix_algo=fix_algo_list[level]
        #print(fix_algo)
        if (fix_algo=="none" and level<=multidim_level) or fix_algo in ["linear","cubic","multidim"] or not sz3_interp:
            if fix_algo=="none" or fix_algo=="linear":
                #tt=time.time()
                if new_q_order:
                    q_array=np.zeros(cur_array.shape,dtype=np.int32)
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            reg_xs.append(np.array([cur_array[x][y-1],cur_array[x][y+1]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
            
            
                for x in range(xstart,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x][y-1],cur_array[x][y+1]]),coef )+ince 
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                

                        if q==0:
                            cur_us.append(decomp)
                    #absloss+=abs(decomp)
                        cur_array[x][y]=decomp    



                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            reg_xs.append(np.array([cur_array[x-1][y],cur_array[x+1][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
                for x in range(1,cur_size_x,2):
                    for y in range(ystart,cur_size_y,2):
                        #if x==cur_size_x-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x-1][y],cur_array[x+1][y]]),coef )+ince 
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
               
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                        
                        cur_array[x][y]=decomp
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            md_reg_xs.append(np.array([cur_array[x-1][y],cur_array[x+1][y],cur_array[x][y-1],cur_array[x][y+1]],dtype=np.float64))
                            md_reg_ys.append(cur_array[x][y])
                            md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                            md_coef=md_res.coef_ 
                            md_ince=md_res.intercept_

        
                for x in range(1,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if x==cur_size_x-1 or y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred=np.dot(np.array([cur_array[x-1][y],cur_array[x+1][y],cur_array[x][y-1],cur_array[x][y+1]]),md_coef)+md_ince
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y]+cur_array[x][y-1]+cur_array[x][y+1])*0.25
                        absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                    #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                if new_q_order==1:
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            cur_qs.append(q_array[x][y])
                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            cur_qs.append(q_array[x][y])
                elif new_q_order==2:
                    for x in range(1 if xstart else 0,cur_size_x,1):
                        for y in range(1 if ystart else 0,cur_size_y,1):
                            if x%2==0 and y%2==0:
                                continue
                            cur_qs.append(q_array[x][y])



                loss_dict[level]["linear"]=absloss
                best_preds=np.copy(cur_array)
                best_absloss=absloss
                best_qs=cur_qs.copy()
                best_us=cur_us.copy()
                selected_algo="linear"
                #print(time.time()-tt)

        #print(len(cur_qs))


            #cubic interp
            #cubic=True
            #if cubic:
            #print("cubic")
            if fix_algo=="none" or fix_algo=="cubic":
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                if new_q_order:
                    q_array=np.zeros(cur_array.shape,dtype=np.int32)
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(3,cur_size_y,2):
                            if y+3>=cur_size_y:
                                continue
                            reg_xs.append(np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
                for x in range(xstart,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if y>=3 and y+3<cur_size_y:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]]) )+ince
                            else:
                                pred=(-cur_array[x][y-3]+9*cur_array[x][y-1]+9*cur_array[x][y+1]-cur_array[x][y+3])*0.0625
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                    
                        if q==0:
                            cur_us.append(decomp)
                            
                        cur_array[x][y]=decomp     
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            if x+3>=cur_size_x:
                                continue
                            reg_xs.append(np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
                for x in range(1,cur_size_x,2):
                    for y in range(ystart,cur_size_y,2):
                        #if x==cur_size_x-1:
                            #continue
                        orig=cur_array[x][y]
                        if x>=3 and x+3<cur_size_x:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]]) )+ince
                            else:
                                pred=(-cur_array[x-3][y]+9*cur_array[x-1][y]+9*cur_array[x+1][y]-cur_array[x+3][y])*0.0625
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                    
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                        #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            md_reg_xs.append(np.array([cur_array[x-1][y],cur_array[x+1][y],cur_array[x][y-1],cur_array[x][y+1]],dtype=np.float64))
                            md_reg_ys.append(cur_array[x][y])
                            md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                            md_coef=md_res.coef_ 
                            md_ince=md_res.intercept_

                for x in range(1,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if x==cur_size_x-1 or y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred=np.dot(np.array([cur_array[x-1][y],cur_array[x+1][y],cur_array[x][y-1],cur_array[x][y+1]]),md_coef)+md_ince
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y]+cur_array[x][y-1]+cur_array[x][y+1])*0.25
                        absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                    
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                loss_dict[level]["cubic"]=absloss

                if selected_algo=="none" or absloss<best_absloss:
                    selected_algo="cubic"
                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    if new_q_order==1:
                        for x in range(xstart,cur_size_x,2):
                            for y in range(1,cur_size_y,2):
                                cur_qs.append(q_array[x][y])
                        for x in range(1,cur_size_x,2):
                            for y in range(1 if ystart>0 else 0,cur_size_y,1):
                                cur_qs.append(q_array[x][y])
                    elif new_q_order==2:
                        for x in range(1 if xstart else 0,cur_size_x,1):
                            for y in range(1 if ystart else 0,cur_size_y,1):
                                if x%2==0 and y%2==0:
                                    continue
                                cur_qs.append(q_array[x][y])
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()

        #multidim
            if fix_algo=="none" or fix_algo=="multidim":
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                if new_q_order:
                    q_array=np.zeros(cur_array.shape,dtype=np.int32)
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            md_reg_xs.append(np.array([cur_array[x-1][y-1],cur_array[x-1][y+1],cur_array[x+1][y-1],cur_array[x+1][y+1]],dtype=np.float64))
                            md_reg_ys.append(cur_array[x][y])
                            md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                            md_coef=md_res.coef_ 
                            md_ince=md_res.intercept_
                for x in range(1,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if x==cur_size_x-1 or y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred=np.dot(np.array([cur_array[x-1][y-1],cur_array[x-1][y+1],cur_array[x+1][y-1],cur_array[x+1][y+1]]),md_coef)+md_ince
                        else:
                            pred=(cur_array[x-1][y-1]+cur_array[x-1][y+1]+cur_array[x+1][y-1]+cur_array[x+1][y+1])*0.25
                        absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(0,cur_size_x):
                        for y in range(1-(x%2),cur_size_y,2):
                            if (x==0 and xstart!=0) or (y==0 and ystart!=0) or x==cur_size_x-1 or y==cur_size_y-1:
                                continue
                            md_reg_xs.append(np.array([cur_array[x][y-1],cur_array[x][y+1],cur_array[x-1][y],cur_array[x+1][y]],dtype=np.float64))
                            md_reg_ys.append(cur_array[x][y])
                            md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                            md_coef=md_res.coef_ 
                            md_ince=md_res.intercept_

                for x in range(0,cur_size_x):
                    if x==0 and xstart!=0:
                        continue
                    for y in range(1-(x%2),cur_size_y,2):
                        if y==0 and ystart!=0:
                            continue
                    
                        orig=cur_array[x][y]
                        if x and y and x!=cur_size_x-1 and y!=cur_size_y-1:
                            if level>=min_coeff_level:
                                pred=np.dot(md_coef,np.array([cur_array[x][y-1],cur_array[x][y+1],cur_array[x-1][y],cur_array[x+1][y]]))+md_ince
                        
                            else:

                                pred=(cur_array[x][y-1]+cur_array[x][y+1]+cur_array[x-1][y]+cur_array[x+1][y])*0.25
                        elif x==0 or x==cur_size_x-1:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or (x!=cur_size_x-1 or last_x!=size_x-1) or (y!=cur_size_y-1 or last_y!=size_y-1):
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        if new_q_order:
                            q_array[x][y]=q
                        else:
                            cur_qs.append(q)
                

                        if q==0:
                            cur_us.append(decomp)
                    #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                loss_dict[level]["multidim"]=absloss
                if selected_algo=="none" or absloss<best_absloss:
                    selected_algo="multidim"
                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    if new_q_order==1:
                        for x in range(xstart,cur_size_x,2):
                            for y in range(1,cur_size_y,2):
                                cur_qs.append(q_array[x][y])
                        for x in range(1,cur_size_x,2):
                            for y in range(1 if ystart>0 else 0,cur_size_y,1):
                                cur_qs.append(q_array[x][y])
                    elif new_q_order==2:
                        for x in range(1 if xstart else 0,cur_size_x,1):
                            for y in range(1 if ystart else 0,cur_size_y,1):
                                if x%2==0 and y%2==0:
                                    continue
                                cur_qs.append(q_array[x][y])
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()
        #sz3 pure 1D interp,linear and cubic, 2 directions.
        if (fix_algo=="none" and sz3_interp) or fix_algo in ["sz3_linear","sz3_cubic","sz3_linear_yx","sz3_linear_xy","sz3_cubic_yx","sz3_cubic_xy"]:
            #linear
            #y then x
            #print("testing sz3 interp") 
            if fix_algo=="none" or fix_algo=="sz3_linear" or fix_algo=="sz3_linear_yx":
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            reg_xs.append(np.array([cur_array[x][y-1],cur_array[x][y+1]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
            

                for x in range(xstart,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x][y-1],cur_array[x][y+1]]),coef )+ince 
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        cur_qs.append(q)
                

                        if q==0:
                            cur_us.append(decomp)
                    #absloss+=abs(decomp)
                        cur_array[x][y]=decomp    



                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            reg_xs.append(np.array([cur_array[x-1][y],cur_array[x+1][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
                for x in range(1,cur_size_x,2):
                    for y in range(1 if ystart>0 else 0,cur_size_y,1):
                        #if x==cur_size_x-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x-1][y],cur_array[x+1][y]]),coef )+ince 
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
               
                        cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                        #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                loss_dict[level]["sz3_linear_yx"]=absloss
                if selected_algo=="none" or absloss<best_absloss:

                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()
                    selected_algo="sz3_linear_yx"

            if fix_algo=="none" or fix_algo=="sz3_linear" or fix_algo=="sz3_linear_xy":
            #x then y 
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            reg_xs.append(np.array([cur_array[x-1][y],cur_array[x+1][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
            

                for x in range(1,cur_size_x,2):
                    for y in range(ystart,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x-1][y],cur_array[x+1][y]]),coef )+ince 
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        cur_qs.append(q)
                

                        if q==0:
                            cur_us.append(decomp)
                    #absloss+=abs(decomp)
                        cur_array[x][y]=decomp    



                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 ,cur_size_y,2):
                            reg_xs.append(np.array([cur_array[x][y-1],cur_array[x][y+1]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_
                for x in range(1 if xstart>0 else 0,cur_size_x,1):
                    for y in range(1 ,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if level>=min_coeff_level:
                            pred= np.dot( np.array([cur_array[x][y-1],cur_array[x][y+1]]),coef )+ince 
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
               
                        cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                        #absloss+=abs(decomp)
                        cur_array[x][y]=decomp
                loss_dict[level]["sz3_linear_xy"]=absloss
                if selected_algo=="none" or absloss<best_absloss:

                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()
                    selected_algo="sz3_linear_xy"

            #cubic interp
            #yx
            if fix_algo=="none" or fix_algo=="sz3_cubic" or fix_algo=="sz3_cubic_yx":
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(3,cur_size_y,2):
                            if y+3>=cur_size_y:
                                continue
                            reg_xs.append(np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_



                for x in range(xstart,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if y>=3 and y+3<cur_size_y:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]]) )+ince
                            else:
                                pred=(-cur_array[x][y-3]+9*cur_array[x][y-1]+9*cur_array[x][y+1]-cur_array[x][y+3])*0.0625
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        cur_qs.append(q)
                    
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp    



                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            if x+3>=cur_size_x:
                                continue
                            reg_xs.append(np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_


                for x in range(1,cur_size_x,2):
                    for y in range(1 if ystart>0 else 0,cur_size_y,1):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if x>=3 and x+3<cur_size_x:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]]) )+ince
                            else:
                                pred=(-cur_array[x-3][y]+9*cur_array[x-1][y]+9*cur_array[x+1][y]-cur_array[x+3][y])*0.0625
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                    
                        cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp


                loss_dict[level]["sz3_cubic_yx"]=absloss
                if selected_algo=="none" or absloss<best_absloss:
                    selected_algo="sz3_cubic_yx"
                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()


                #xy 
            if fix_algo=="none" or fix_algo=="sz3_cubic" or fix_algo=="sz3_cubic_xy":
                absloss=0
                cur_qs=[]
                cur_us=[]
                cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            if x+3>=cur_size_x:
                                continue
                            reg_xs.append(np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_



                for x in range(1,cur_size_x,2):
                    for y in range(ystart,cur_size_y,2):
                        #if x==cur_size_x-1:
                            #continue
                        orig=cur_array[x][y]
                        if x>=3 and x+3<cur_size_x:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x-3][y],cur_array[x-1][y],cur_array[x+1][y],cur_array[x+3][y]]) )+ince
                            else:
                                pred=(-cur_array[x-3][y]+9*cur_array[x-1][y]+9*cur_array[x+1][y]-cur_array[x+3][y])*0.0625
                        else:
                            pred=(cur_array[x-1][y]+cur_array[x+1][y])*0.5
                        if (not random_access) or level!=0 or y!=cur_size_y-1 or last_y!=size_y-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        cur_qs.append(q)
                    
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp    



                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(3,cur_size_y,2):
                            if y+3>=cur_size_y:
                                continue
                            reg_xs.append(np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]],dtype=np.float64))
                            reg_ys.append(cur_array[x][y])
                            res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                            coef=res.coef_ 
                            ince=res.intercept_


                for x in range(1 if xstart>0 else 0,cur_size_x,1):
                    for y in range(1,cur_size_y,2):
                        #if y==cur_size_y-1:
                            #continue
                        orig=cur_array[x][y]
                        if y>=3 and y+3<cur_size_y:
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y-3],cur_array[x][y-1],cur_array[x][y+1],cur_array[x][y+3]]) )+ince
                            else:
                                pred=(-cur_array[x][y-3]+9*cur_array[x][y-1]+9*cur_array[x][y+1]-cur_array[x][y+3])*0.0625
                        else:
                            pred=(cur_array[x][y-1]+cur_array[x][y+1])*0.5
                        if (not random_access) or level!=0 or x!=cur_size_x-1 or last_x!=size_x-1:
                            absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                    
                        cur_qs.append(q)
                        if q==0:
                            cur_us.append(decomp)
                            #absloss+=abs(decomp)
                        cur_array[x][y]=decomp


                loss_dict[level]["sz3_cubic_xy"]=absloss
                if selected_algo=="none" or absloss<best_absloss:
                    selected_algo="sz3_cubic_xy"
                    best_preds=np.copy(cur_array)
                    best_absloss=absloss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()











        #Lorenzo fallback
        if level<=lorenzo:
            absloss=0
        #cur_qs=[]
        #cur_us=[]
        #cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
            xstart=1 if x_preded else 0
            ystart=1 if y_preded else 0
            cur_orig_array=orig_array[0:last_x+1:step,0:last_y+1:step]
            x_end_offset=1 if (random_access and last_x==size_x-1 and level==0) else 0
            y_end_offset=1 if (random_access and last_y==size_y-1 and level==0) else 0
            total_points=[(x,y) for x in range(cur_orig_array.shape[0]-1) for y in range(cur_orig_array.shape[1]-1) if (max_step<=0 or ((x*step)%max_step!=0 and (y*step)%max_step!=0))]
            if len(total_points)<min_sampled_points:
                num_sumples=len(total_points)
                sampled_points=total_points
            else:
                num_sumples=max(min_sampled_points,int(len(total_points)*sample_rate) )
                sampled_points=random.sample(total_points,num_sumples)
            for x,y in sampled_points:
                orig=cur_orig_array[x][y]
                f_01=cur_orig_array[x-1][y] if x else 0
                if x and max_step>0 and ((x-1)*step)%max_step==0 and (y*step)%max_step==0:
                    f_01+=anchor_eb*(2*np.random.rand()-1)
                elif x:
                    f_01+=cur_eb*(2*np.random.rand()-1)

                f_10=cur_orig_array[x][y-1] if y else 0
                if y and max_step>0 and (x*step)%max_step==0 and ((y-1)*step)%max_step==0:
                    f_10+=anchor_eb*(2*np.random.rand()-1)
                elif y:
                    f_10+=cur_eb*(2*np.random.rand()-1)
            
                f_00=cur_orig_array[x-1][y-1] if x and y else 0
                if x and y and max_step>0 and ((x-1)*step)%max_step==0 and ((y-1)*step)%max_step==0:
                    f_00+=anchor_eb*(2*np.random.rand()-1)
                elif x and y:
                    f_00+=cur_eb*(2*np.random.rand()-1)
                
                pred=f_01+f_10-f_00

                absloss+=abs(orig-pred)
            #print(absloss*len(total_points)/len(sampled_points))
            #print(best_absloss)
            #print(cumulated_loss)
            if absloss*len(total_points)/len(sampled_points)<best_absloss+cumulated_loss:
                selected_algo="lorenzo_fallback"
                best_absloss=0
                best_preds=np.copy(cur_orig_array)
                best_qs=[]
                best_us=[]
           
            #qs[max_level]=qs[:maxlevel_q_start]
                for i in range(max_level-1,level,-1):
                    qs[i]=[]
                us=us[:u_start]
                for x in range(xstart,cur_size_x-x_end_offset):
                    for y in range(ystart,cur_size_y-y_end_offset):
                    
                        if max_step>0 and (x*step)%max_step==0 and (y*step)%max_step==0:
                            #print(x,y)
                            continue
                        orig=best_preds[x][y]
                        f_01=best_preds[x-1][y] if x else 0
                
                        f_10=best_preds[x][y-1] if y else 0
            
                        f_00=best_preds[x-1][y-1] if x and y else 0
                
                        pred=f_01+f_10-f_00
                
        
                        best_absloss+=abs(orig-pred)
                        q,decomp=quantize(orig,pred,cur_eb)
                        best_qs.append(q)
                        if q==0:
                            best_us.append(decomp)
                #absloss+=abs(decomp)
                        best_preds[x][y]=decomp
            

        #print(len(best_qs))




        mean_l1_loss=best_absloss/len(best_qs)
        if not fake_compression:
            array[0:last_x+1:step,0:last_y+1:step]=best_preds
        if selected_algo!="lorenzo_fallback":
            cumulated_loss+=best_absloss
        
        else:
            cumulated_loss=best_absloss
        
        #print(np.max(np.abs(array[0:last_x+1:step,0:last_y+1:step]-best_preds)))
    
        #if args.lorenzo_fallback_check:
        #    print(np.max(np.abs(orig_array-array))/rng)
        qs[level]+=best_qs
        us+=best_us
        selected_algos.append(selected_algo)
        #print(len(qs))
        if verbose:
            print ("Level %d finished. Selected algorithm: %s. Mean prediction abs loss: %f." % (level,selected_algo,mean_l1_loss))
        step=step//2
        level-=1
        #print(sum([len(_) for _ in qs] ))
        #print(best_absloss)
        #print(cumulated_loss)



    def lorenzo_2d(array,x_start,x_end,y_start,y_end):
        for x in range(x_start,x_end):
            for y in range(y_start,y_end):

                orig=array[x][y]
        
                f_01=array[x-1][y] if x else 0
                f_10=array[x][y-1] if y else 0
            
                f_00=array[x-1][y-1] if x and y else 0
                
                pred=f_01+f_10-f_00
                
        
                
                q,decomp=quantize(orig,pred,error_bound)
                edge_qs.append(q)
                if q==0:
                    us.append(decomp)
                array[x][y]=decomp
    offset_x1=1 if x_preded else 0
    offset_y1=1 if y_preded else 0
    offset_x2=1 if random_access else 0
    offset_y2=1 if random_access else 0
    lorenzo_2d(array,offset_x1,last_x+1,last_y+1,size_y-offset_y2)
    lorenzo_2d(array,last_x+1,size_x-offset_x2,offset_y1,size_y-offset_y2)
    return array,qs,edge_qs,us,selected_algos,loss_dict


    
if __name__=="__main__":
 



    parser = argparse.ArgumentParser()

    parser.add_argument('--error','-e',type=float,default=1e-3)
    parser.add_argument('--input','-i',type=str)
    parser.add_argument('--output','-o',type=str)
    parser.add_argument('--quant','-q',type=str,default="ml2_q.dat")
    parser.add_argument('--unpred','-u',type=str,default="ml2_u.dat")
    parser.add_argument('--max_step','-s',type=int,default=-1)
    parser.add_argument('--min_coeff_level','-cl',type=int,default=99)
    parser.add_argument('--rate','-r',type=float,default=1.0)
    parser.add_argument('--rlist',type=float,default=-1,nargs="+")
    parser.add_argument('--maximum_rate','-m',type=float,default=10.0)
    parser.add_argument('--cubic','-c',type=int,default=1)
    parser.add_argument('--multidim_level','-d',type=int,default=99)
    parser.add_argument('--lorenzo_fallback_check','-l',type=int,default=-1)
    parser.add_argument('--fallback_sample_ratio','-p',type=float,default=0.05)
    parser.add_argument('--anchor_rate','-a',type=float,default=0.0)

    parser.add_argument('--size_x','-x',type=int,default=1800)
    parser.add_argument('--size_y','-y',type=int,default=3600)
    parser.add_argument('--sz_interp','-n',type=int,default=0)
    parser.add_argument('--autotuning','-t',type=float,default=0.0)
    parser.add_argument('--fix_algo','-f',type=str,default="none")
    args = parser.parse_args()
    print(args)
    array=np.fromfile(args.input,dtype=np.float32).reshape((args.size_x,args.size_y))
    orig_array=np.copy(array)
    rng=(np.max(array)-np.min(array))
    error_bound=args.error*rng
    max_level=int(math.log(args.max_step,2))
    rate_list=args.rlist
    #print(rate_list)
    if args.autotuning!=0:
        #pid=os.getpid()
        alpha_list=[1,1.25,1.5,1.75,2]
        beta_list=[2,4]
        rate_list=None
        block_num_x=(args.size_x-1)//args.max_step
        block_num_y=(args.size_y-1)//args.max_step
        steplength=int(math.sqrt(args.autotuning))
        bestalpha=1
        bestbeta=1
        #bestpdb=0
        bestb=9999
        #bestb_r=9999
        bestp=0
        #bestp_r=0
        pid=os.getpid()
        tq_name="%s_tq.dat"%pid
        tu_name="%s_tu.dat"%pid
        max_step=args.max_step
        max_level=int(math.log(max_step,2))
        for k,alpha in enumerate(alpha_list):
            for beta in beta_list:
                #maybe some pruning
                test_qs=[[] for i in range(max_level+1)]
                test_us=[]
                square_error=0
                #zero_square_error=0
                element_counts=0
                themax=-9999999999999
                themin=99999999999999
                #themean=0
                #print(themean)
                for i in range(0,block_num_x,steplength):
                    for j in range(0,block_num_y,steplength):
                      
                        x_start=max_step*i
                        y_start=max_step*j
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        #print(x_start)
                        #print(y_start)
                        cur_array=np.copy(array[x_start:x_end,y_start:y_end])
                        '''
                        curmax=np.max(cur_array)
                        curmin=np.min(cur_array)
                        if curmax>themax:
                            themax=curmax
                        if curmin<themin:
                            themin=curmin
                        '''
                        #left question: The predictor selection is separated on each block, which does not follow the real compression
                        #What about fix the prediction on SZ3_cubic?
                        cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc2d(cur_array,error_bound,alpha,beta,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                sz3_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=None)
                        #print(len(cur_qs[max_level]))
                        #print(len(test_qs[max_level]))
                        for level in range(max_level+1):
                            #print(level)
                            test_qs[level]+=cur_qs[level]
                        test_us+=cur_us
                        #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                        square_error+=np.sum((array[x_start:x_end,y_start:y_end]-cur_array)**2)
                        
                        element_counts+=(max_step+1)**2 
                t_mse=square_error/element_counts
                #zero_mse=zero_square_error/element_counts
                psnr=20*math.log(rng,10)-10*math.log(t_mse,10)
                #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                #print(zero_psnr)
              
                np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                    lines=f.read().splitlines()
                    cr=eval(lines[4].split("=")[-1])
                    if args.anchor_rate==0:
                        anchor_ratio=1/(args.max_step**2)
                        cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                    bitrate=32/cr
                os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                #pdb=(psnr-zero_psnr)/bitrate
                if psnr<=bestp and bitrate>=bestb:
                    continue
                elif psnr>=bestp and bitrate<=bestb:

                    bestalpha=alpha
                    bestbeta=beta
                   
                    bestb=bitrate
                    bestp=psnr
                       
                else:
                    if psnr>bestp:
                        new_error_bound=1.2*error_bound
                    else:
                        new_error_bound=0.8*error_bound
                    test_qs=[[] for i in range(max_level+1)]
                    test_us=[]
                    square_error=0
                    #zero_square_error=0
                    element_counts=0
                    themax=-9999999999999
                    themin=99999999999999
                    #themean=0
                    #print(themean)
                    for i in range(0,block_num_x,steplength):
                        for j in range(0,block_num_y,steplength):
                          
                            x_start=max_step*i
                            y_start=max_step*j
                            x_end=x_start+max_step+1
                            y_end=y_start+max_step+1
                            #print(x_start)
                            #print(y_start)
                            cur_array=np.copy(array[x_start:x_end,y_start:y_end])
                            '''
                            curmax=np.max(cur_array)
                            curmin=np.min(cur_array)
                            if curmax>themax:
                                themax=curmax
                            if curmin<themin:
                                themin=curmin
                            '''
                            cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc2d(cur_array,new_error_bound,alpha,beta,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                    sz3_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=None)
                            #print(len(cur_qs[max_level]))
                            #print(len(test_qs[max_level]))
                            for level in range(max_level+1):
                                #print(level)
                                test_qs[level]+=cur_qs[level]
                            test_us+=cur_us
                            #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                            square_error+=np.sum((array[x_start:x_end,y_start:y_end]-cur_array)**2)
                            
                            element_counts+=(max_step+1)**2 
                    t_mse=square_error/element_counts
                    #zero_mse=zero_square_error/element_counts
                    psnr_r=20*math.log(rng,10)-10*math.log(t_mse,10)
                    #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                    #print(zero_psnr)
                  
                    np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                    np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                    with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                        lines=f.read().splitlines()
                        cr=eval(lines[4].split("=")[-1])
                        if args.anchor_rate==0:
                            anchor_ratio=1/(args.max_step**2)
                            cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                        bitrate_r=32/cr
                    os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                    a=(psnr-psnr_r)/(bitrate-bitrate_r)
                    b=psnr-a*bitrate
                    #print(a)
                    #print(b)
                    reg=a*bestb+b
                    if reg>bestp:
                        bestalpha=alpha
                        bestbeta=beta
                   
                        bestb=bitrate
                        bestp=psnr
                if alpha**(max_level-1)<=beta:
                    break

                
                
               


        print("Autotuning finished. Selected alpha: %f. Selected beta: %f. Best bitrate: %f. Best PSNR: %f."\
        %(bestalpha,bestbeta,bestb,bestp) )
        args.rate=bestalpha
        args.maximum_rate=bestbeta

        if args.fix_algo=="none":
            print("Start predictor tuning.")
            #tune predictor
            fix_algo_list=[]
            for level in range(max_level-1,-1,-1):
                loss_dict={}
                pred_candidates=[]
                if args.sz_interp:
                    pred_candidates+=["sz3_linear_xy","sz3_linear_yx","sz3_cubic_xy","sz3_cubic_yx"]
                if level<=args.multidim_level:
                    pred_candidates+=["linear","cubic","multidim"]
                for i in range(0,block_num_x,steplength):
                    for j in range(0,block_num_y,steplength):
                  
                        x_start=max_step*i
                        y_start=max_step*j
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        #print(x_start)
                        #print(y_start)
                        cur_array=np.copy(array[x_start:x_end,y_start:y_end])
                        for predictor in pred_candidates:
                            cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc2d(cur_array,error_bound,alpha,beta,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                    sz3_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                    min_sampled_points=100,random_access=False,verbose=False,first_level=level,last_level=level,fix_algo=predictor,fake_compression=True)
                            cur_loss=lsd[level][predictor]
                            if predictor not in loss_dict:
                                loss_dict[predictor]=cur_loss
                            else:
                                loss_dict[predictor]+=cur_loss
                best_predictor="none"
                min_loss=9e20
                for pred in loss_dict:
                    pred_loss=loss_dict[pred]
                    if pred_loss<min_loss:
                        min_loss=pred_loss
                        best_predictor=pred 

                print("Level %d tuned. Best predictor: %s." % (level,best_predictor))
                fix_algo_list.append(best_predictor)
                '''
                for i in range(0,block_num_x,steplength):
                    for j in range(0,block_num_y,steplength):
                  
                        x_start=max_step*i
                        y_start=max_step*j
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        #print(x_start)
                        #print(y_start)
                        #array[x_start:x_end,y_start:y_end]
                        
                        array[x_start:x_end,y_start:y_end],cur_qs,edge_qs,cur_us,_,lsd=msc2d(array[x_start:x_end,y_start:y_end],error_bound,alpha,beta,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                sz3_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                min_sampled_points=100,random_access=False,verbose=False,first_level=level,last_level=level,fix_algo=best_predictor,fake_compression=False)
                '''

            fix_algo_list.reverse()
            #print(fix_algo_list)
            '''
            for i in range(0,block_num_x,steplength):
                for j in range(0,block_num_y,steplength):
                  
                        x_start=max_step*i
                        y_start=max_step*j
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        array[x_start:x_end,y_start:y_end]=np.copy(orig_array[x_start:x_end,y_start:y_end])
            '''
        else:
            fix_algo_list=None


            


    else:
        fix_algo_list=None
        if ((isinstance(rate_list,int) or isinstance(rate_list,float)) and  rate_list>0) or (isinstance(rate_list,list ) and rate_list[0]>0):

            if isinstance(rate_list,int) or isinstance(rate_list,float):
                rate_list=[rate_list]

            while len(rate_list)<max_level:
                rate_list.insert(0,rate_list[0])
        else:
            rate_list=None
        
   

    #array=np.copy(orig_array)


    array,qs,edge_qs,us,_,lsd=msc2d(array,error_bound,args.rate,args.maximum_rate,args.min_coeff_level,args.max_step,args.anchor_rate,rate_list=rate_list,x_preded=False,y_preded=False,\
        sz3_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=args.lorenzo_fallback_check,sample_rate=args.fallback_sample_ratio,min_sampled_points=100,random_access=False,verbose=True,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
    quants=np.concatenate( (np.array(edge_qs,dtype=np.int32),np.array(sum(qs,[]),dtype=np.int32) ) )
    unpreds=np.array(us,dtype=np.float32)
    array.tofile(args.output)
    quants.tofile(args.quant)
    unpreds.tofile(args.unpred)
    '''
    for x in range(args.size_x):
        for y in range(args.size_y):
            if array[x][y]==orig_array[x][y] and x%args.max_step!=0 and y%args.max_step!=0:
                print(x,y)
    '''