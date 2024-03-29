import numpy as np 

import os
import argparse
#import torch
#import torch.nn as nn
from sklearn.linear_model import LinearRegression
import math
import random
from utils import *

def msc3d(array,x_start,x_end,y_start,y_end,z_start,z_end,error_bound,rate,maximum_rate,min_coeff_level,max_step,anchor_rate,\
    rate_list=None,x_preded=False,y_preded=False,z_preded=False,multidim_level=-1,sz_interp=False,lorenzo=-1,\
sample_rate=0.05,min_sampled_points=10,new_q_order=0,grid_mode=0,selection_criteria="l1",random_access=False,verbose=False,pred_check=False\
,fix_algo="none",fix_algo_list=None,first_level=None,last_level=0,first_order="block",fake_compression=False):#lorenzo:only check lorenzo fallback with level no larger than lorenzo level

    size_x,size_y,size_z=array.shape
    '''
    if pred_check:
        preded=np.zeros((size_x,size_y,size_z))
    '''
    #array=np.fromfile(args.input,dtype=np.float32).reshape((size_x,size_y))
    if lorenzo>=0:
        orig_array=np.copy(array)
    if random_access and lorenzo>=0:
        lorenzo=0
    #error_bound=args.error*rng
    #max_step=args.max_step
    #rate=args.rate
    if anchor_rate>0:
        anchor_eb=error_bound/anchor_rate
    else:
        anchor_eb=0

    if max_step>0:
        use_anchor=True
        max_level=int(math.log(max_step,2))  
    else:
        use_anchor=False
        max_level=int(math.log(max(array.shape)-1,2))+1
        max_step=2**max_level
        anchor_eb=error_bound/min(maximum_rate,rate**max_level)


    selected_algos=[]


    qs=[ [] for i in range(max_level+1)]
    
    us=[]
    edge_qs=[]
#min_coeff_level=args.min_coeff_level
#anchor=args.anchor
    
    startx=max_step if x_preded else 0
    starty=max_step if y_preded else 0
    startz=max_step if z_preded else 0
    if first_level==None or first_level<0 or first_level>max_level:
        first_level=max_level

    if max_step>0 and first_level==max_level and (anchor_eb>0 ):
    
    #anchor_rate=args.anchor_rate
        
        
        if verbose:
            print("Anchor eb:%f" % anchor_eb)

        if max_level>=min_coeff_level :
            reg_xs=[]
            reg_ys=[]
            for x in range(x_start+max_step,x_end,max_step):
                for y in range(y_start+max_step,y_end,max_step):
                    for z in range(z_start+max_step,z_end,max_step):
                        reg_xs.append(np.array(array[x-max_step:x+1,y-max_step:y+1,z-max_step:z+1][:7],dtype=np.float64))
                        reg_ys.append(array[x][y][z])
                        res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                        coef=res.coef_ 
                        ince=res.intercept_

 
        
        for x in range(x_start+startx,x_end,max_step):
            for y in range(y_start+starty,y_end,max_step):
                for z in range(z_start+startz,z_end,max_step):
                    orig=array[x][y][z]
                    if x and y and z and max_level>=min_coeff_level:
                        reg_block=array[x-max_step:x+1,y-max_step:y+1,z-max_step:z+1][:7]
                        pred=np.dot(reg_block,coef)+ince

            
                
                    else:
                        f_011=array[x-max_step][y][z] if x else 0
                        f_101=array[x][y-max_step][z] if y else 0
                        f_110=array[x][y][z-max_step] if z else 0
                        f_001=array[x-max_step][y-max_step][z] if x and y else 0
                        f_100=array[x][y-max_step][z-max_step] if y and z else 0
                        f_010=array[x-max_step][y][z-max_step] if x and z else 0
                        f_000=array[x-max_step][y-max_step][z-max_step] if x and y and z else 0
                
                        pred=f_000-f_001-f_010+f_011-f_100+f_101+f_110
                
        
                
                        q,decomp=quantize(orig,pred,anchor_eb)
                        qs[max_level].append(q)
                        if q==0:
                            us.append(decomp)
                        array[x][y][z]=decomp
       
    elif use_anchor and first_level==max_level:
        #pass
        
        for x in range(x_start+startx,x_end,max_step):
            for y in range(y_start+starty,y_end,max_step):
                for z in range(z_start+startz,z_end,max_step):
                    orig=array[x][y][z]
                    us.append(orig)
                    '''
                    if pred_check:
                        preded[x][y][z]=1
                    '''
        
#print(len(qs))

    #last_x=((x_end-1)//max_step)*max_step
    #last_y=((y_end-1)//max_step)*max_step 
    #last_z=((z_end-1)//max_step)*max_step   
    #global_last_x=((size_x-1)//max_step)*max_step
    #global_last_y=((size_y-1)//max_step)*max_step
    #global_last_z=((size_z-1)//max_step)*max_step
    step=max_step//2
    level=max_level-1
    
    #maxlevel_q_start=len(qs[max_level])
    u_start=len(us)
    cumulated_loss=0.0
    loss_dict=[{} for i in range(max_level)]
    cross_before=(not random_access) #or (max_step>0 and level==max_level-1)
     
    
    #cross_after=((not random_access) and first_order=="level") or (max_step>0 and level==max_level-1)
    
    while level>=last_level:#step>0:
        if level>first_level:
            level-=1
            step=step//2
            continue

        def inlosscal(x,y,z):
            return (not random_access) or level!=0 or (x!=x_end-1 and y!=y_end-1 and z!=z_end-1)
        cur_qs=[]
        cur_us=[]
        if rate_list!=None:
            cur_eb=error_bound/rate_list[level]
        else:
            cur_eb=error_bound/min(maximum_rate,(rate**level))
        array_slice=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
        #cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step,0:last_z+1:step])
        #cur_size_x,cur_size_y,cur_size_z=cur_array.shape
        '''
        if pred_check:
            cur_preded=np.copy(preded[0:last_x+1:step,0:last_y+1:step,0:last_z+1:step])
            best_preded=np.copy(preded[0:last_x+1:step,0:last_y+1:step,0:last_z+1:step])
        '''

        #print(cur_array.shape)
        
    #print(cur_size_x,cur_size_y)
        if verbose:
            print("Level %d started. Current step: %d. Current error_bound: %s." % (level,step,cur_eb))
        best_preds=None#need to copy
        best_loss=None

        best_qs=[]#need to copy
        best_us=[]#need to copy
        doublestep=step*2
        triplestep=step*3
        pentastep=step*5
        x_start_offset=doublestep if x_preded else 0
        y_start_offset=doublestep if y_preded else 0
        z_start_offset=doublestep if z_preded else 0
        def cross_after(x,y,z):
            if random_access:
                return False
            if (x%max_step==0 and y%max_step==0 and z%max_step==0) or (grid_mode and (x%max_step==0 or y%max_step==0 or z%max_step==0)):
                return True
            if first_order=="block":
                return False

            else:
                #print("woshinidebaba")
                #print()
                return (x%doublestep==0 and y%doublestep==0 and z%doublestep==0)


     
    #linear interp
        loss=0
        selected_algo="none"
        if fix_algo_list!=None:
            fix_algo=fix_algo_list[level]
        if (fix_algo=="none" and level>=multidim_level) or fix_algo in ["linear","cubic","multidim"] or not sz_interp:
            if fix_algo=="none" or fix_algo=="linear":
                if new_q_order:# all new_q_order remain unmodified
                    q_array=np.zeros(array_slice.shape,dtype=np.int32)
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
            

                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                            #if z==cur_size_z-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error1")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]]),coef )+ince 
                            else:
                                if z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) ):
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                elif (z-triplestep>=z_start) or (cross_before and z-triplestep>=0):
                                    pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                else:
                                    pred=array[x][y][z-step]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp    
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1
                            '''



                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if y==cur_size_y-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0:
                                    print("error2")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]]),coef )+ince 
                            else:
                                if y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) ):
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif (y-triplestep>=y_start) or (cross_before and y-triplestep>=0):
                                    pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                else:
                                    pred=array[x][y-step][z]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1
                            '''
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if x==cur_size_x-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0:
                                    print("error3")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]]),coef )+ince 
                            else:
                                if x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)):
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif (x-triplestep>=x_start) or (cross_before and x-triplestep>=0):
                                    pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                else:
                                    pred=array[x-step][y][z]


                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp  
                            ''' 
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''
        
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0:
                                    print("error4")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z]]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z) )
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                if x_wise and y_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                else:
                                    pred=lor_2d(array[x-step][y-step][z],array[x-step][y][z],array[x][y-step][z])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                    
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):

                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''
        
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error5")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y][z-1],cur_array[x][y][z+1]]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z) )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if x_wise and z_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_2d(array[x-step][y][z-step],array[x-step][y][z],array[x][y][z-step])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''

                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error6")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]]),md_coef)+md_ince
                            else:
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if y_wise and z_wise:
                                    pred=interp_2d(array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_2d(array[x][y-step][z-step],array[x][y-step][z],array[x][y][z-step])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            '''
                            if pred_check:

                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''

                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error7")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1] ]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z) )
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if x_wise and y_wise and z_wise:
                                    pred=interp_3d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise and y_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z])
                                elif x_wise and z_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y][z-step],array[x][y][z+step])
                                elif y_wise and z_wise:
                                    pred=interp_2d(array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_3d(array[x-step][y-step][z-step],array[x-step][y-step][z],array[x-step][y][z-step],array[x-step][y][z],array[x][y-step][z-step],array[x][y-step][z],array[x][y][z-step])
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
 
                if new_q_order==1:
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])
                elif new_q_order==2:
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                if x%2==0 and y%2==0 and z%2==0:
                                    continue
                                cur_qs.append(q_array[x][y][z])


                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)





                loss_dict[level]["linear"]=loss
                best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                '''
                if pred_check:
                    best_preded=np.copy(cur_preded)
                '''
                best_loss=loss
                


                best_qs=cur_qs.copy()
                best_us=cur_us.copy()
                selected_algo="linear"

            #print(len(cur_qs))


            #cubic interp
            #cubic=True
            #if cubic:
            #print("cubic")
            if fix_algo=="none" or fix_algo=="cubic":
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                if new_q_order:
                    q_array=np.zeros(array_slice.shape,dtype=np.int32)
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(3,cur_size_z,2):
                                if z+3>=cur_size_z:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= z-triplestep>=z_start or (cross_before and z>=triplestep)
                                plusthree= z+triplestep<z_end or (z+triplestep<size_z and cross_after(x,y,z+triplestep) )
                                plusone= plusthree or z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                               
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step])
                                
                                elif plusone:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:#exterp
                                    if minusthree:
                                        minusfive= z-pentastep>=z_start or (cross_before and z>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y][z-pentastep],array[x][y][z-triplestep],array[x][y][z-step])
                                        else:
                                            pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                    else:
                                        pred=array[x][y][z-step]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp     

                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(3,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                if y+3>=cur_size_y:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y-3][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y+3][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= y-triplestep>=y_start or (cross_before and y>=triplestep)
                                plusthree= y+triplestep<y_end or (y+triplestep<size_y and cross_after(x,y+triplestep,z) )
                                plusone= plusthree or y+step<y_end or (y+step<size_y and cross_after(x,y+step,z)  )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                                #'''
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z])
                                #'''
                                elif plusone:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                else:#exterp
                                    if minusthree:
                                        minusfive= y-pentastep>=y_start or (cross_before and y>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y-pentastep][z],array[x][y-triplestep][z],array[x][y-step][z])
                                        else:
                                            pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                    else:
                                        pred=array[x][y-step][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                if x+3>=cur_size_x:
                                    continue
                                reg_xs.append(np.array([cur_array[x-3][y][z],cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x+3][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''

                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= x-triplestep>=x_start or (cross_before and x>=triplestep)
                                plusthree= x+triplestep<x_end or (x+triplestep<size_x and cross_after(x+triplestep,y,z) )
                                plusone= plusthree or x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                #'''
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z])
                                #'''
                                elif plusone:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                else:#exterp
                                    if minusthree:
                                        minusfive= x-pentastep>=x_start or (cross_before and x>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x-pentastep][y][z],array[x-triplestep][y][z],array[x-step][y][z])
                                        else:
                                            pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                    else:
                                        pred=array[x-step][y][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 

    
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_

                '''
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0:
                                    print("error4")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z]]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  )
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z)  )
                                if x_wise and y_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                else:
                                    pred=lor_2d(array[x-step][y-step][z],array[x-step][y][z],array[x][y-step][z])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                    
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):

                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''
        
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error5")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y][z-1],cur_array[x][y][z+1]]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if x_wise and z_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_2d(array[x-step][y][z-step],array[x-step][y][z],array[x][y][z-step])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    
                            array[x][y][z]=decomp
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''

                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error6")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]]),md_coef)+md_ince
                            else:
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if y_wise and z_wise:
                                    pred=interp_2d(array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_2d(array[x][y-step][z-step],array[x][y-step][z],array[x][y][z-step])

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            '''
                            if pred_check:

                                cur_preded[x][y][z]=1  
                            '''
                '''
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                md_reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                '''

                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                    
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0 or cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0 or cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error7")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred=np.dot(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y][z-1],cur_array[x][y][z+1] ]),md_coef)+md_ince
                            else:
                                x_wise=x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  )
                                y_wise=y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                z_wise=z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if x_wise and y_wise and z_wise:
                                    pred=interp_3d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise and y_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y-step][z],array[x][y+step][z])
                                elif x_wise and z_wise:
                                    pred=interp_2d(array[x-step][y][z],array[x+step][y][z],array[x][y][z-step],array[x][y][z+step])
                                elif y_wise and z_wise:
                                    pred=interp_2d(array[x][y-step][z],array[x][y+step][z],array[x][y][z-step],array[x][y][z+step])
                                elif x_wise:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif y_wise:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif z_wise:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:
                                    pred=lor_3d(array[x-step][y-step][z-step],array[x-step][y-step][z],array[x-step][y][z-step],array[x-step][y][z],array[x][y-step][z-step],array[x][y-step][z],array[x][y][z-step])
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                    
                            array[x][y][z]=decomp


                if new_q_order==1:
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])
                elif new_q_order==2:
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                if x%2==0 and y%2==0 and z%2==0:
                                    continue
                                cur_qs.append(q_array[x][y][z])

                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)
                
                loss_dict[level]["cubic"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="cubic"
                    best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                    best_loss=loss

                   
                    

                    

                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()
            
            #full multidim
            if 0: #fix_algo=="none" or fix_algo=="multidim":#too diffcult for coding, temp deprecated
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                if new_q_order:
                    q_array=np.zeros(cur_array.shape,dtype=np.int32)
                #center
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1,cur_size_y,2):
                                md_reg_xs.append(np.array(cur_array[x-1:x+2:2,y-1:y+2:2,z-1:z+2:2],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                for x in range(1,cur_size_x,2):
                    for y in range(1,cur_size_y,2):
                        for z in range(1,cur_size_y,2):
                            if x==cur_size_x-1 or y==cur_size_y-1:
                                continue
                            orig=cur_array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(cur_array[x-1:x+2:2,y-1:y+2:2,z-1:z+2:2],md_coef)+md_ince
                            else:
                                pred=np.mean(cur_array[x-1:x+2:2,y-1:y+2:2,z-1:z+2:2])
                            if selection_criteria=="l1":
                                loss+=abs(orig-pred)
                            elif selection_criteria=="l2":
                                loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            cur_array[x][y][z]=decomp

                #face
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(0,cur_size_x):
                        for y in range(1-(x%2),cur_size_y,2-(x%2)):

                            for z in range((x+y)%2,cur_size_z,2):
                                if (x==0 and xstart!=0) or (y==0 and ystart!=0) or (z==0 and zstart!=0) or x==cur_size_x-1 or y==cur_size_y-1 or z==cur_size_z-1:
                                    continue
                                md_reg_xs.append(np.array([cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x-1][y][z],cur_array[x+1][y][z]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                
                for x in range(0,cur_size_x):
                    for y in range(1-(x%2),cur_size_y,2-(x%2)):

                        for z in range((x+y)%2,cur_size_z,2):
                            if (x==0 and xstart!=0) or (y==0 and ystart!=0) or (z==0 and zstart!=0):
                                 continue
                    
                            orig=cur_array[x][y][z]
                            if x and y and z and x!=cur_size_x-1 and y!=cur_size_y-1 and z!=cur_size_z-1:
                                if level>=min_coeff_level:
                                    pred=np.dot(md_coef,np.array([cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x-1][y][z],cur_array[x+1][y][z]]))+md_ince
                        
                                else:

                                    pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x][y-1][z]+cur_array[x][y+1][z]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/6
                            elif x and y and x!=cur_size_x-1 and y!=cur_size_y-1:
                                pred=(cur_array[x][y-1][z]+cur_array[x][y+1][z]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/4
                            elif x and z and x!=cur_size_x-1 and z!=cur_size_z-1:
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/4
                            elif y and z and y!=cur_size_y-1 and z!=cur_size_z-1:
                              
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x][y-1][z]+cur_array[x][y+1][z])/4



                            elif x and x!=cur_size_x-1:
                                pred=(cur_array[x-1][y][z]+cur_array[x+1][y][z])/2
                            elif y and y!=cur_size_y-1:
                                pred=(cur_array[x][y-1][z]+cur_array[x][y+1][z])/2
                            else:
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1])/2
                            if (not random_access) or level!=0 or ((x!=cur_size_x-1 or last_x!=size_x-1) and (y!=cur_size_y-1 or last_y!=size_y-1) and (z!=cur_size_z-1 or last_z!=size_z-1)):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                   
                            cur_array[x][y][z]=decomp
                #edge
                if level>=min_coeff_level:
                    md_reg_xs=[]
                    md_reg_ys=[]
                    for x in range(0,cur_size_x):
                        for y in range(0,cur_size_y,1+(x%2)):

                            for z in range(1-((x+y)%2),cur_size_z,2):
                                if (x==0 and xstart!=0) or (y==0 and ystart!=0) or (z==0 and zstart!=0) or x==cur_size_x-1 or y==cur_size_y-1 or z==cur_size_z-1:
                                    continue
                                md_reg_xs.append(np.array([cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x-1][y][z],cur_array[x+1][y][z]],dtype=np.float64))
                                md_reg_ys.append(cur_array[x][y][z])
                                md_res=LinearRegression(fit_intercept=True).fit(md_reg_xs, md_reg_ys)
                                md_coef=md_res.coef_ 
                                md_ince=md_res.intercept_
                
                for x in range(0,cur_size_x):
                    for y in range(0,cur_size_y,1+(x%2)):

                        for z in range(1-((x+y)%2),cur_size_z,2):
                            if (x==0 and xstart!=0) or (y==0 and ystart!=0) or (z==0 and zstart!=0):
                                 continue
                    
                            orig=cur_array[x][y][z]
                            if x and y and z and x!=cur_size_x-1 and y!=cur_size_y-1 and z!=cur_size_z-1:
                                if level>=min_coeff_level:
                                    pred=np.dot(md_coef,np.array([cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x-1][y][z],cur_array[x+1][y][z]]))+md_ince
                        
                                else:

                                    pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x][y-1][z]+cur_array[x][y+1][z]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/6
                            elif x and y and x!=cur_size_x-1 and y!=cur_size_y-1:
                                pred=(cur_array[x][y-1][z]+cur_array[x][y+1][z]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/4
                            elif x and z and x!=cur_size_x-1 and z!=cur_size_z-1:
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x-1][y][z]+cur_array[x+1][y][z])/4
                            elif y and z and y!=cur_size_y-1 and z!=cur_size_z-1:
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1]+cur_array[x][y-1][z]+cur_array[x][y+1][z])/4



                            elif x and x!=cur_size_x-1:
                                pred=(cur_array[x-1][y][z]+cur_array[x+1][y][z])/2
                            elif y and y!=cur_size_y-1:
                                pred=(cur_array[x][y-1][z]+cur_array[x][y+1][z])/2
                            else:
                                pred=(cur_array[x][y][z-1]+cur_array[x][y][z+1])/2
                            if (not random_access) or level!=0 or ((x!=cur_size_x-1 or last_x!=size_x-1) and (y!=cur_size_y-1 or last_y!=size_y-1) and (z!=cur_size_z-1 or last_z!=size_z-1)):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            if new_q_order:
                                q_array[x][y][z]=q
                            else:
                                cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                   
                            cur_array[x][y][z]=decomp

                if new_q_order==1:
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])

                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                cur_qs.append(q_array[x][y][z])
                elif new_q_order==2:
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                if x%2==0 and y%2==0 and z%2==0:
                                    continue
                                cur_qs.append(q_array[x][y][z])
                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)
                loss_dict[level]["multidim"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="multidim"
                    best_preds=np.copy(cur_array)

                    best_loss=loss
                    

                    

                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()


        if (fix_algo=="none" and sz_interp) or fix_algo in ["sz3_linear","sz3_cubic","sz3_linear_zyx","sz3_linear_xyz","sz3_cubic_zyx","sz3_cubic_xyz"]:
            #1D linear
            #zyx
            
            if fix_algo=="none" or fix_algo=="sz3_linear" or fix_algo=="sz3_linear_zyx":
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                '''
                if pred_check:
                    
                    cur_preded=np.copy(preded[0:last_x+1:step,0:last_y+1:step,0:last_z+1:step])
                '''
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(1,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''

                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                            #if z==cur_size_z-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error1")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]]),coef )+ince 
                            else:
                                if z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) ):
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                elif (z-triplestep>=z_start) or (cross_before and z-triplestep>=0):
                                    pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                else:
                                    pred=array[x][y][z-step]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            
                            
                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp
                            ''' 
                            if pred_check:
                                cur_preded[x][y][z]=1
                            '''
                            

                
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(1,cur_size_y,2):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                reg_xs.append(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+ (step if z_start_offset else 0),z_end,step):
                            #if y==cur_size_y-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y-1][z]==0 or cur_preded[x][y+1][z]==0:
                                    print("error2")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]]),coef )+ince 
                            else:
                                if y+step<y_end or (y+step<size_y and cross_after(x,y+step,z)  ):
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif (y-triplestep>=y_start) or (cross_before and y-triplestep>=0):
                                    pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                else:
                                    pred=array[x][y-step][z]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)

                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp 
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1
                            '''

                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+(step if y_start_offset else 0),y_end,step):
                        for z in range(z_start+(step if z_start_offset else 0),z_end,step):
                           
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x-1][y][z]==0 or cur_preded[x+1][y][z]==0:
                                    print("error12")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]]),coef )+ince 
                            else:
                                if x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  ):
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif (x-triplestep>=x_start) or (cross_before and x-triplestep>=0):
                                    pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                else:
                                    pred=array[x-step][y][z]


                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp 
                            '''
                            if pred_check:
                                cur_preded[x][y][z]=1
                            '''
                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)
                loss_dict[level]["sz3_linear_zyx"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="sz3_linear_zyx"
                    best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                    best_loss=loss
                    '''
                    if pred_check:
                        best_preded=np.copy(cur_preded)
                    '''
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()


            if fix_algo=="none" or fix_algo=="sz3_linear" or fix_algo=="sz3_linear_xyz":
                #xyz
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(x_start+step,x_end,doublestep):
                        for y in range(y_start+y_start_offset,y_end,doublestep):
                            for z in range(z_start+z_start_offset,z_end,doublestep):
                                reg_xs.append(np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''

                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if z==cur_size_z-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x-1][y][z],cur_array[x+1][y][z]]),coef )+ince 
                            else:
                                if x+step<x_end or (x+step<size_x and cross_after(x+step,y,z) ):
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                elif (x-triplestep>=x_start) or (cross_before and x-triplestep>=0):
                                    pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                else:
                                    pred=array[x-step][y][z]


                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp    


                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                 ince=res.intercept_
                '''
                for x in range(x_start+(step if x_start_offset>0 else 0),x_end,step):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if y==cur_size_y-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y-1][z],cur_array[x][y+1][z]]),coef )+ince 
                            else:
                                if y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) ):
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                elif (y-triplestep>=y_start) or (cross_before and y-triplestep>=0):
                                    pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                else:
                                    pred=array[x][y-step][z]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)

                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp 

                '''

                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 ,cur_size_z,2):
                                reg_xs.append(np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+(step if x_start_offset>0 else 0),x_end,step):
                    for y in range(y_start+(step if y_start_offset>0 else 0),y_end,step):
                        for z in range(z_start+step,z_end,doublestep):
                            #if x==cur_size_x-1:
                                #continue
                            orig=array[x][y][z]
                            '''
                            if pred_check:
                                if cur_preded[x][y][z-1]==0 or cur_preded[x][y][z+1]==0:
                                    print("error1")
                                    return
                            '''
                            if level>=min_coeff_level:
                                pred= np.dot( np.array([cur_array[x][y][z-1],cur_array[x][y][z+1]]),coef )+ince 
                            else:
                                if z+step<z_end or (z+step<size_z and cross_after(x,y,z+step)):
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                elif (z-triplestep>=z_start) or (cross_before and z-triplestep>=0):
                                    pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                else:
                                    pred=array[x][y][z-step]
                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            
                            
                            cur_qs.append(q)
                

                            if q==0:
                                cur_us.append(decomp)
                        #absloss+=abs(decomp)
                            array[x][y][z]=decomp

                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)

                loss_dict[level]["sz3_linear_xyz"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="sz3_linear_xyz"
                    best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                    best_loss=loss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()

            #1D cubic
            #ZYX
            if fix_algo=="none" or fix_algo=="sz3_cubic" or fix_algo=="sz3_cubic_zyx":
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(3,cur_size_z,2):
                                if z+3>=cur_size_z:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''

                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+step,z_end,doublestep):
                    
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= z-triplestep>=z_start or (cross_before and z>=triplestep)
                                plusthree= z+triplestep<z_end or (z+triplestep<size_z and cross_after(x,y,z+triplestep) )
                                plusone= plusthree or z+step<z_end or (z+step<size_z and cross_after(x,y,z+step) )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                                #'''
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step])
                                #'''
                                elif plusone:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:#exterp
                                    #print(x,y,z,step)
                                    if minusthree:
                                        minusfive= z-pentastep>=z_start or (cross_before and z>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y][z-pentastep],array[x][y][z-triplestep],array[x][y][z-step])
                                        else:
                                            pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                    else:
                                        pred=array[x][y][z-step]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp         


                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(xstart,cur_size_x,2):
                        for y in range(3,cur_size_y,2):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                if y+3>=cur_size_y:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y-3][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y+3][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
               '''
                for x in range(x_start+x_start_offset,x_end,doublestep):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+ (step if z_start_offset else 0),z_end,step):
                            #if y==cur_size_y-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= y-triplestep>=y_start or (cross_before and y>=triplestep)
                                plusthree= y+triplestep<y_end or (y+triplestep<size_y and cross_after(x,y+triplestep,z) )
                                plusone= plusthree or y+step<y_end or (y+step<size_y and cross_after(x,y+step,z)  )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                            
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z])
                                
                                elif plusone:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                else:#exterp
                                    #print(x,y,z,step)
                                    if minusthree:
                                        minusfive= y-pentastep>=y_start or (cross_before and y>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y-pentastep][z],array[x][y-triplestep][z],array[x][y-step][z])
                                        else:
                                            pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                    else:
                                        pred=array[x][y-step][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                           
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(1 if zstart>0 else 0,cur_size_z,1):
                                if x+3>=cur_size_x:
                                    continue
                                reg_xs.append(np.array([cur_array[x-3][y][z],cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x+3][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''

                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+( step if y_start_offset else 0),y_end,step):
                        for z in range(z_start+( step if z_start_offset else 0),z_end,step):
                            
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= x-triplestep>=x_start or (cross_before and x>=triplestep)
                                plusthree= x+triplestep<x_end or (x+triplestep<size_x and cross_after(x+triplestep,y,z) )
                                plusone= plusthree or x+step<x_end or (x+step<size_x and cross_after(x+step,y,z)  )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z])
                                
                                elif plusone:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                else:#exterp
                                    #print(x,y,z,step)
                                    if minusthree:
                                        minusfive= x-pentastep>=x_start or (cross_before and x>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x-pentastep][y][z],array[x-triplestep][y][z],array[x-step][y][z])
                                        else:
                                            pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                    else:
                                        pred=array[x-step][y][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                           
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 


                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)
                loss_dict[level]["sz3_cubic_zyx"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="sz3_cubic_zyx"
                    best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                    best_loss=loss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()



            #xyz
            if fix_algo=="none" or fix_algo=="sz3_cubic" or fix_algo=="sz3_cubic_xyz":
                loss=0
                cur_qs=[]
                cur_us=[]
                if selected_algo!="none":
                    array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice#reset cur_array
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(3,cur_size_x,2):
                        for y in range(ystart,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                if x+3>=cur_size_x:
                                    continue
                                reg_xs.append(np.array([cur_array[x-3][y][z],cur_array[x-1][y][z],cur_array[x+1][y][z],cur_array[x+3][y][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
            
                '''
                for x in range(x_start+step,x_end,doublestep):
                    for y in range(y_start+y_start_offset,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if z==cur_size_z-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= x-triplestep>=x_start or (cross_before and x>=triplestep)
                                plusthree= x+triplestep<x_end or (x+triplestep<size_x and cross_after(x+triplestep,y,z)  )
                                plusone= plusthree or x+step<x_end or (x+step<size_x and cross_after(x+step,y,z) )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x-step][y][z],array[x+step][y][z],array[x+triplestep][y][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x-triplestep][y][z],array[x-step][y][z],array[x+step][y][z])
                                
                                elif plusone:
                                    pred=interp_linear(array[x-step][y][z],array[x+step][y][z])
                                else:#exterp
                                    if minusthree:
                                        minusfive= x-pentastep>=x_start or (cross_before and x>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x-pentastep][y][z],array[x-triplestep][y][z],array[x-step][y][z])
                                        else:
                                            pred=exterp_linear(array[x-triplestep][y][z],array[x-step][y][z])
                                    else:
                                        pred=array[x-step][y][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                           
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 


                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(3,cur_size_y,2):
                            for z in range(zstart,cur_size_z,2):
                                if y+3>=cur_size_y:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y-3][z],cur_array[x][y-1][z],cur_array[x][y+1][z],cur_array[x][y+3][z]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+(step if x_start_offset>0 else 0),x_end,step):
                    for y in range(y_start+step,y_end,doublestep):
                        for z in range(z_start+z_start_offset,z_end,doublestep):
                            #if y==cur_size_y-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= y-triplestep>=y_start or (cross_before and y>=triplestep)
                                plusthree= y+triplestep<y_end or (y+triplestep<size_y and cross_after(x,y+triplestep,z)  )
                                plusone= plusthree or y+step<y_end or (y+step<size_y and cross_after(x,y+step,z) )
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                                
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y-step][z],array[x][y+step][z],array[x][y+triplestep][z])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y-triplestep][z],array[x][y-step][z],array[x][y+step][z])
                                
                                elif plusone:
                                    pred=interp_linear(array[x][y-step][z],array[x][y+step][z])
                                else:#exterp
                                    if minusthree:
                                        minusfive= y-pentastep>=y_start or (cross_before and y>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y-pentastep][z],array[x][y-triplestep][z],array[x][y-step][z])
                                        else:
                                            pred=exterp_linear(array[x][y-triplestep][z],array[x][y-step][z])
                                    else:
                                        pred=array[x][y-step][z]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                           
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp 
                '''
                if level>=min_coeff_level:
                    reg_xs=[]
                    reg_ys=[]
                    for x in range(1 if xstart>0 else 0,cur_size_x,1):
                        for y in range(1 if ystart>0 else 0,cur_size_y,1):
                            for z in range(3 ,cur_size_z,2):
                                if z+3>=cur_size_z:
                                    continue
                                reg_xs.append(np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]],dtype=np.float64))
                                reg_ys.append(cur_array[x][y][z])
                                res=LinearRegression(fit_intercept=True).fit(reg_xs, reg_ys)
                                coef=res.coef_ 
                                ince=res.intercept_
                '''
                for x in range(x_start+(step if x_start_offset>0 else 0),x_end,step):
                    for y in range(y_start+(step if y_start_offset>0 else 0),y_end,step):
                        for z in range(z_start+step,z_end,doublestep):
                            #if x==cur_size_x-1:
                                #continue
                            orig=array[x][y][z]
                            if level>=min_coeff_level:
                                pred=np.dot(coef,np.array([cur_array[x][y][z-3],cur_array[x][y][z-1],cur_array[x][y][z+1],cur_array[x][y][z+3]]) )+ince
                            else:
                                minusthree= z-triplestep>=z_start or (cross_before and z>=triplestep)
                                plusthree= z+triplestep<z_end or (z+triplestep<size_z and cross_after(x,y,z+triplestep)  )
                                plusone= plusthree or z+step<z_end or (z+step<size_z and cross_after(x,y,z+step))
                                if minusthree and plusthree and plusone:

                                    pred=interp_cubic(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                                #'''
                                elif plusone and plusthree:
                                    pred=interp_quad(array[x][y][z-step],array[x][y][z+step],array[x][y][z+triplestep])
                                elif minusthree and plusone:
                                    pred=interp_quad2(array[x][y][z-triplestep],array[x][y][z-step],array[x][y][z+step])
                                #'''
                                elif plusone:
                                    pred=interp_linear(array[x][y][z-step],array[x][y][z+step])
                                else:#exterp
                                    if minusthree:
                                        minusfive= z-pentastep>=z_start or (cross_before and z>=pentastep)
                                        if minusfive:
                                            pred=exterp_quad(array[x][y][z-pentastep],array[x][y][z-triplestep],array[x][y][z-step])
                                        else:
                                            pred=exterp_linear(array[x][y][z-triplestep],array[x][y][z-step])
                                    else:
                                        pred=array[x][y][z-step]

                            if inlosscal(x,y,z):
                                if selection_criteria=="l1":
                                    loss+=abs(orig-pred)
                                elif selection_criteria=="l2":
                                    loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            
                            cur_qs.append(q)
                    
                            if q==0:
                                cur_us.append(decomp)
                                #absloss+=abs(decomp)
                            array[x][y][z]=decomp

                if selection_criteria=="bitrate":
                    loss=estimate_bitrate(cur_qs)

                loss_dict[level]["sz3_cubic_xyz"]=loss
                if selected_algo=="none" or loss<best_loss:
                    selected_algo="sz3_cubic_xyz"
                    best_preds=np.copy(array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step])
                    best_loss=loss
                    best_qs=cur_qs.copy()
                    best_us=cur_us.copy()







        
        #Lorenzo fallback
        if level<=lorenzo or fix_algo=="lorenzo":#current lorenzo fallback check does not support bitrate criteria well
            loss=0
        #cur_qs=[]
        #cur_us=[]
        #cur_array=np.copy(array[0:last_x+1:step,0:last_y+1:step])#reset cur_array
            x_start_offset=step if x_preded else 0
            y_start_offset=step if y_preded else 0
            z_start_offset=step if z_preded else 0
            cur_orig_array=orig_array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]
            x_end_offset=1 if (random_access and level==0 and x_end!=size_x) else 0
            y_end_offset=1 if (random_access and level==0 and y_end!=size_y) else 0
            z_end_offset=1 if (random_access and level==0 and z_end!=size_z) else 0
            total_points=[(x,y,z) for x in range(cur_orig_array.shape[0]-1) for y in range(cur_orig_array.shape[1]-1) for z in range(cur_orig_array.shape[2]-1) if (max_step<=0 or ((x*step)%max_step!=0 and (y*step)%max_step!=0 and (z*step)%max_step!=0 ))  ]
            if len(total_points)<min_sampled_points:
                num_sumples=len(total_points)
                sampled_points=total_points
            else:
                num_sumples=max(min_sampled_points,int(len(total_points)*sample_rate) )
                sampled_points=random.sample(total_points,num_sumples)
            for x,y,z in sampled_points:
                '''
                f_011=array[x-max_step][y][z] if x else 0
                f_101=array[x][y-max_step][z] if y else 0
                f_110=array[x][y][z-max_step] if z else 0
                f_001=array[x-max_step][y-max_step][z] if x and y else 0
                f_100=array[x][y-max_step][z-max_step] if y and z else 0
                f_010=array[x-max_step][y][z-max_step] if x and z else 0
                f_000=array[x-max_step][y-max_step][z-max_step] if x and y and z else 0
                
                pred=f_000+f_011+f_101+f_110-f_001-f_010-f_100
                '''
                orig=cur_orig_array[x][y][z]
                f_011=cur_orig_array[x-1][y][z] if x else 0
                if x and max_step>0 and ((x-1)*step)%max_step==0 and (y*step)%max_step==0 and (z*step)%max_step==0:
                    f_011+=anchor_eb*(2*np.random.rand()-1)
                elif x:
                    f_011+=cur_eb*(2*np.random.rand()-1)


                f_101=cur_orig_array[x][y-1][z] if y else 0
                if y and max_step>0 and (x*step)%max_step==0 and ((y-1)*step)%max_step==0 and (z*step)%max_step==0:
                    f_101+=anchor_eb*(2*np.random.rand()-1)
                elif y:
                    f_101+=cur_eb*(2*np.random.rand()-1)
                 
                f_110=cur_orig_array[x][y][z-1] if z else 0
                if z and max_step>0 and (x*step)%max_step==0 and (y*step)%max_step==0 and ((z-1)*step)%max_step==0:
                    f_110+=anchor_eb*(2*np.random.rand()-1)
                elif z:
                    f_110+=cur_eb*(2*np.random.rand()-1)


                f_001=cur_orig_array[x-1][y-1][z] if x and y else 0
                if x and y and max_step>0 and ((x-1)*step)%max_step==0 and ((y-1)*step)%max_step==0 and (z*step)%max_step==0:
                    f_001+=anchor_eb*(2*np.random.rand()-1)
                elif x and y:
                    f_001+=cur_eb*(2*np.random.rand()-1)

                f_100=cur_orig_array[x][y-1][z-1] if y and z else 0
                if y and z and max_step>0 and (x*step)%max_step==0 and ((y-1)*step)%max_step==0 and ((z-1)*step)%max_step==0:
                    f_100+=anchor_eb*(2*np.random.rand()-1)
                elif y and z:
                    f_100+=cur_eb*(2*np.random.rand()-1)

                f_010=cur_orig_array[x-1][y][z-1] if x and z else 0
                if x and z and max_step>0 and ((x-1)*step)%max_step==0 and (y*step)%max_step==0 and ((z-1)*step)%max_step==0:
                    f_010+=anchor_eb*(2*np.random.rand()-1)
                elif x and z:
                    f_010+=cur_eb*(2*np.random.rand()-1)

                f_000=cur_orig_array[x-1][y-1][z-1] if x and y and z else 0
                if x and y and z and max_step>0 and ((x-1)*step)%max_step==0 and ((y-1)*step)%max_step==0 and ((z-1)*step)%max_step==0:
                    f_000+=anchor_eb*(2*np.random.rand()-1)
                elif x and y and z:
                    f_000+=cur_eb*(2*np.random.rand()-1)


                
                pred=f_000+f_011+f_101+f_110-f_001-f_010-f_100

                if selection_criteria=="l1":
                    loss+=abs(orig-pred)
                elif selection_criteria=="l2":
                    loss+=(orig-pred)**2
            #print(absloss*len(total_points)/len(sampled_points))
            #print(best_absloss)
            #print(cumulated_loss)
            if loss*len(total_points)/len(sampled_points)<best_loss+cumulated_loss or fix_algo=="lorenzo":
                selected_algo="lorenzo_fallback"
                best_loss=0
                array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=orig_array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]#reset array
                best_qs=[]
                best_us=[]
           
            #qs[max_level]=qs[:maxlevel_q_start]
                for i in range(max_level-1,level,-1):
                    qs[i]=[]
                us=us[:u_start]
                for x in range(x_start+x_start_offset,x_end-x_end_offset*step,step):
                    for y in range(y_start+y_start_offset,y_end-y_end_offset*step,step):
                        for z in range(z_start+z_start_offset,y_end-y_end_offset*step,step):
                    
                            if max_step>0 and x%max_step==0 and y%max_step==0 and z%max_step==0:
                            #print(x,y)
                                continue
                            orig=array[x][y][z]
                            f_011=array[x-step][y][z] if x-step>=x_start or (x-step>=0 and cross_before) else 0
                            f_101=array[x][y-step][z] if y-step>=y_start or (y-step>=0 and cross_before) else 0
                            f_110=array[x][y][z-step] if z-step>=z_start or (z-step>=0 and cross_before) else 0
                            f_001=array[x-step][y-step][z] if (x-step>=x_start or (x-step>=0 and cross_before)) and (y-step>=y_start or (y-step>=0 and cross_before)) else 0
                            f_100=array[x][y-step][z-step] if (y-step>=y_start or (y-step>=0 and cross_before)) and (z-step>=z_start or (z-step>=0 and cross_before)) else 0
                            f_010=array[x-step][y][z-step] if (x-step>=x_start or (x-step>=0 and cross_before)) and (z-step>=z_start or (z-step>=0 and cross_before)) else 0
                            f_000=array[x-step][y-step][z-step] if (x-step>=x_start or (x-step>=0 and cross_before)) and (y-step>=y_start or (y-step>=0 and cross_before)) and (z-step>=z_start or (z-step>=0 and cross_before)) else 0
                
                            pred=f_000+f_011+f_101+f_110-f_001-f_010-f_100
                        
                
        
                            if selection_criteria=="l1":
                                best_loss+=abs(orig-pred)
                            elif selection_criteria=="l2":
                                best_loss+=(orig-pred)**2
                            q,decomp=quantize(orig,pred,cur_eb)
                            best_qs.append(q)
                            if q==0:
                                best_us.append(decomp)
                #absloss+=abs(decomp)
                            array[x][y][z]=decomp
            

        #print(len(best_qs))



        if len(best_qs)!=0:
            mean_loss=best_loss/len(best_qs)
        else:
            mean_loss=0

        if fake_compression:
            array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=array_slice
        elif selected_algo!="lorenzo_fallback":
            array[x_start:x_end:step,y_start:y_end:step,z_start:z_end:step]=best_preds

        if selected_algo!="lorenzo_fallback":
            cumulated_loss+=best_loss

        else:
            cumulated_loss=best_loss
        
        #print(np.max(np.abs(array[0:last_x+1:step,0:last_y+1:step]-best_preds)))
    
        #if args.lorenzo_fallback_check:
        #    print(np.max(np.abs(orig_array-array))/rng)
        qs[level]+=best_qs
        us+=best_us
        selected_algos.append(selected_algo)
        #print(len(qs))
        if verbose:
            print ("Level %d finished. Selected algorithm: %s. Mean prediction loss: %f." % (level,selected_algo,mean_loss))
        step=step//2
        level-=1
        #print(np.max(np.abs(orig_array-array)))
        #print(sum([len(_) for _ in qs] ))
        #print(best_absloss)
        #print(cumulated_loss)



    def lorenzo_3d(array,x_start,x_end,y_start,y_end,z_start,z_end):
        for x in range(x_start,x_end):
            for y in range(y_start,y_end):
                for z in range(z_start,z_end):
                    if x<=last_x and y<=last_y and z<=last_z:
                        continue

                    orig=array[x][y][z]
                    f_011=array[x-1][y][z] if x else 0
                    f_101=array[x][y-1][z] if y else 0
                    f_110=array[x][y][z-1] if z else 0
                    f_001=array[x-1][y-1][z] if x and y else 0
                    f_100=array[x][y-1][z-1] if y and z else 0
                    f_010=array[x-1][y][z-1] if x and z else 0
                    f_000=array[x-1][y-1][z-1] if x and y and z else 0
                
                    pred=f_000+f_011+f_101+f_110-f_001-f_010-f_100
        
                
                
        
                
                    q,decomp=quantize(orig,pred,error_bound)
                    edge_qs.append(q)
                    if q==0:
                        us.append(decomp)
                    array[x][y][z]=decomp
    '''
    offset_x1=1 if x_preded else 0
    offset_y1=1 if y_preded else 0
    offset_z1=1 if z_preded else 0
    offset_x2=1 if random_access else 0
    offset_y2=1 if random_access else 0
    offset_z2=1 if random_access else 0
    lorenzo_3d(array,offset_x1,size_x-offset_x2,offset_y1,size_y-offset_y2,offset_z1,size_z-offset_z2)
    '''
    #print(np.max(np.abs(orig_array-array)))
    #lorenzo_2d(array,last_x+1,,offset_y1,size_y-offset_y2)
    return array,qs,edge_qs,us,selected_algos,loss_dict


    
if __name__=="__main__":
 



    parser = argparse.ArgumentParser()

    parser.add_argument('--error','-e',type=float,default=1e-3)
    parser.add_argument('--input','-i',type=str)
    parser.add_argument('--output','-o',type=str)
    parser.add_argument('--quant','-q',type=str,default="ml3_q.dat")
    parser.add_argument('--unpred','-u',type=str,default="ml3_u.dat")
    parser.add_argument('--max_step','-s',type=int,default=16)
    parser.add_argument('--min_coeff_level','-cl',type=int,default=99)
    parser.add_argument('--rate','-r',type=float,default=-1.0)
    parser.add_argument('--rlist',type=float,default=-1,nargs="+")
    parser.add_argument('--maximum_rate','-m',type=float,default=-1)
    #parser.add_argument('--cubic','-c',type=int,default=1)
    parser.add_argument('--multidim_level','-d',type=int,default=-1)
    parser.add_argument('--lorenzo_fallback_check','-l',type=int,default=-1)
    parser.add_argument('--fallback_sample_ratio','-p',type=float,default=0.05)

#parser.add_argument('--level_rate','-lr',type=float,default=1.0)
    parser.add_argument('--anchor_rate','-a',type=float,default=0.0)
    parser.add_argument('--sz_interp','-n',type=int,default=1)

    parser.add_argument('--size_x','-x',type=int,default=129)
    #parser.add_argument('--double','-b',type=int,default=0)
    parser.add_argument('--size_y','-y',type=int,default=129)
    parser.add_argument('--size_z','-z',type=int,default=129)
    parser.add_argument('--fix_algo','-f',type=str,default="none")
    parser.add_argument('--autotuning','-t',type=int,default=0)
    parser.add_argument('--criteria','-c',type=str,default="l1")
    parser.add_argument('--block_size','-b',type=int,default=16)
    parser.add_argument('--interp_block_size',type=int,default=0)#interp block size
    parser.add_argument('--one_interpolator',type=int,default=0)
    parser.add_argument('--predictor_first',type=int,default=1)
#parser.add_argument('--level','-l',type=int,default=2)
#parser.add_argument('--noise','-n',type=bool,default=False)
#parser.add_argument('--intercept','-t',type=bool,default=False)
    
    args = parser.parse_args()
    print(args)
    if 0:#if args.double:
        dtype=np.double
    else:
        dtype=np.float32
    array=np.fromfile(args.input,dtype=dtype).reshape((args.size_x,args.size_y,args.size_z))
    orig_array=np.copy(array)
    rng=np.max(array)-np.min(array)
    error_bound=args.error*rng
    if args.max_step>0:

        max_level=int(math.log(args.max_step,2))
        
    else:

        max_level=int(math.log(max(array.shape)-1,2))+1

    rate_list=args.rlist
    block_size=args.block_size
    fix_algo_list=None
    #print(rate_list)
    if args.autotuning!=0 and (not args.predictor_first or args.fix_algo!="none"):
        #pid=os.getpid()
        alpha_list=[1,1.25,1.5,1.75,2]
        #beta_list=[2,4,4,6,6]
        beta_list=[1.5,2,3,4]
        #rate_list=None
        max_step=args.max_step
        #max_step=16#special
        block_num_x=(args.size_x-1)//block_size
        block_num_y=(args.size_y-1)//block_size
        block_num_z=(args.size_z-1)//block_size
        steplength=int(args.autotuning**(1/3))
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
        
        block_max_level=int(math.log(args.block_size,2))
        for m,alpha in enumerate(alpha_list):
            for beta in beta_list:
                if alpha>beta:
                    continue
                #maybe some pruning
                test_qs=[[] for i in range(block_max_level+1)]
                test_us=[]
                square_error=0
                #zero_square_error=0
                element_counts=0
                #themax=-9999999999999
                #themin=99999999999999
                #themean=0
                #print(themean)
                idx=0
                for i in range(0,block_num_x,1):#steplength):
                    for j in range(0,block_num_y,1):#steplength):
                        for k in range(0,block_num_z,1):#steplength):
                            if idx%args.autotuning!=0:
                                idx+=1
                                continue
                        
                            x_start=block_size*i
                            y_start=block_size*j
                            z_start=block_size*k
                            x_end=x_start+block_size+1
                            y_end=y_start+block_size+1
                            z_end=z_start+block_size+1
                            #print(x_start)
                            #print(y_start)
                            cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                            '''
                            curmax=np.max(cur_array)
                            curmin=np.min(cur_array)
                            if curmax>themax:
                                themax=curmax
                            if curmin<themin:
                                themin=curmin
                            '''
                            #print("a")
                            cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,error_bound,alpha,beta,9999,max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                    sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,\
                                                    lorenzo=-1,sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
                            #print("b")
                            #print(len(cur_qs[max_level]))
                            #print(len(test_qs[max_level]))
                            for level in range(block_max_level+1):
                                #print(level)
                                test_qs[level]+=cur_qs[level]
                            #test_us+=cur_us
                            #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                            square_error+=np.sum((array[x_start:x_end,y_start:y_end,z_start:z_end]-cur_array)**2)
                            
                            element_counts+=(block_size+1)**3 
                            idx+=1
                            #array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]

                t_mse=square_error/element_counts
                #zero_mse=zero_square_error/element_counts
                if t_mse==0:
                    psnr=9999
                else:
                    psnr=20*math.log(rng,10)-10*math.log(t_mse,10)
                #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                #print(zero_psnr)
              
                np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                    lines=f.read().splitlines()
                    cr=eval(lines[4].split("=")[-1])
                    if args.max_step>0 and args.anchor_rate==0:
                        anchor_ratio=1/(args.max_step**3)
                        cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                    bitrate=32/cr
                os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                #pdb=(psnr-zero_psnr)/bitrate
                if psnr<=bestp and bitrate>=bestb:
                    if alpha**(block_max_level-1)<=beta:
                        break
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
                    test_qs=[[] for i in range(block_max_level+1)]
                    test_us=[]
                    square_error=0
                    #zero_square_error=0
                    element_counts=0
                    themax=-9999999999999
                    themin=99999999999999
                    #themean=0
                    #print(themean)
                    idx=0
                    for i in range(0,block_num_x,1):#steplength):
                        for j in range(0,block_num_y,1):#steplength):
                            for k in range(0,block_num_z,1):#steplength):
                                if idx%args.autotuning!=0:
                                    idx+=1
                                    continue
                                x_start=block_size*i
                                y_start=block_size*j
                                z_start=block_size*k
                                x_end=x_start+block_size+1
                                y_end=y_start+block_size+1
                                z_end=z_start+block_size+1
                                #print(x_start)
                                #print(y_start)
                                cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                                '''
                                curmax=np.max(cur_array)
                                curmin=np.min(cur_array)
                                if curmax>themax:
                                    themax=curmax
                                if curmin<themin:
                                    themin=curmin
                                '''
                                #print("v")
                                cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,new_error_bound,alpha,beta,9999,max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                        sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,\
                                                        sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
                                #print("d")
                                #print(len(cur_qs[max_level]))
                                #print(len(test_qs[max_level]))
                                for level in range(block_max_level+1):
                                    #print(level)
                                    test_qs[level]+=cur_qs[level]
                                #test_us+=cur_us
                                #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                                square_error+=np.sum((array[x_start:x_end,y_start:y_end,z_start:z_end]-cur_array)**2)
                            
                                element_counts+=(block_size+1)**3 
                                idx+=1
                                #array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]
                    t_mse=square_error/element_counts
                    #zero_mse=zero_square_error/element_counts
                    if t_mse==0:
                        psnr_r=9999
                    else:
                        psnr_r=20*math.log(rng,10)-10*math.log(t_mse,10)
                    #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                    #print(zero_psnr)
                  
                    np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                    np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                    with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                        lines=f.read().splitlines()
                        cr=eval(lines[4].split("=")[-1])
                        if args.max_step>0 and args.anchor_rate==0:
                            anchor_ratio=1/(args.max_step**3)
                            cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                        bitrate_r=32/cr
                    os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                    a=(psnr-psnr_r)/(bitrate-bitrate_r+1e-12)
                    b=psnr-a*bitrate
                    #print(a)
                    #print(b)
                    reg=a*bestb+b
                    if reg>bestp:
                        bestalpha=alpha
                        bestbeta=beta
                   
                        bestb=bitrate
                        bestp=psnr
                if alpha**(block_max_level-1)<=beta:
                    break

                
                
               


        print("Autotuning finished. Selected alpha: %f. Selected beta: %f. Best bitrate: %f. Best PSNR: %f."\
        %(bestalpha,bestbeta,bestb,bestp) )
        #max_step=args.max_step#special
        args.rate=bestalpha
        args.maximum_rate=bestbeta

        if args.fix_algo=="none":
            print("Start predictor tuning.")
            #tune predictor
            fix_algo_list=[]
            block_size=args.block_size
            block_max_level=int(math.log(block_size,2))
            block_num_x=(args.size_x-1)//block_size
            block_num_y=(args.size_y-1)//block_size
            for level in range(block_max_level-1,-1,-1):
                loss_dict={}
                pred_candidates=[]
                best_predictor=None
                best_loss=9e10
                if args.sz_interp:
                    pred_candidates+=["sz3_linear_xyz","sz3_linear_zyx","sz3_cubic_xyz","sz3_cubic_zyx"]
                if level>=args.multidim_level:
                    pred_candidates+=["linear","cubic"]#multidim temp depred
                idx=0
                for i in range(0,block_num_x,1):#steplength):
                    for j in range(0,block_num_y,1):#steplength):
                        for k in range(0,block_num_z,1):#steplength):
                            if idx%args.autotuning!=0:
                                idx+=1
                                continue
                  
                            x_start=block_size*i
                            y_start=block_size*j
                            z_start=block_size*k
                            x_end=x_start+block_size+1
                            y_end=y_start+block_size+1
                            z_end=z_start+block_size+1
                            #print(x_start)
                            #print(y_start)
                            cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                            for predictor in pred_candidates:
                                cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,error_bound,args.rate,args.maximum_rate,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                        sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                        min_sampled_points=100,random_access=False,verbose=False,\
                                                                        first_level=None if args.one_interpolator else level,last_level=0 if args.one_interpolator else level,fix_algo=predictor,fake_compression=True)
                                if args.one_interpolator:
                                    cur_loss=0
                                    for level in range(len(lsd)):
                                        if predictor in lsd[level]:
                                            cur_loss+=lsd[level][predictor]
                                    if cur_loss<best_loss:
                                        best_loss=cur_loss
                                        best_predictor=predictor



                                else:
                                    cur_loss=lsd[level][predictor]
                                    if predictor not in loss_dict:
                                        loss_dict[predictor]=cur_loss
                                    else:
                                        loss_dict[predictor]+=cur_loss
                            idx+=1
                if args.one_interpolator:
                    fix_algo_list=None
                    args.fix_algo=best_predictor
                    print("Predictor tuned. Best predictor: %s." % best_predictor)
                    break
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
                idx=0
                for i in range(0,block_num_x,1):#steplength):
                    for j in range(0,block_num_y,1):#steplength):
                        for k in range(0,block_num_z,1):#steplength):
                            if idx%args.autotuning!=0:
                                idx+=1
                                continue
                  
                            x_start=block_size*i
                            y_start=block_size*j
                            z_start=block_size*k
                            x_end=x_start+block_size+1
                            y_end=y_start+block_size+1
                            z_end=z_start+block_size+1
                        #print(x_start)
                        #print(y_start)
                            #cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                           
                            array[x_start:x_end,y_start:y_end,z_start:z_end],cur_qs,edge_qs,cur_us,_,lsd=msc3d(array[x_start:x_end,y_start:y_end,z_start:z_end],error_bound,args.rate,args.maximum_rate,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                    sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                    min_sampled_points=100,random_access=False,verbose=False,first_level=level,last_level=level,fix_algo=best_predictor,fake_compression=False)
                            idx+=1
                '''
            if not args.one_interpolator:
                fix_algo_list.reverse()
                while len(fix_algo_list)<max_level:
                    fix_algo_list.append(fix_algo_list[-1])
            '''
            idx=0
            for i in range(0,block_num_x,1):#steplength):
                for j in range(0,block_num_y,1):#steplength):
                    for k in range(0,block_num_z,1):#steplength):
                        if idx%args.autotuning!=0:
                            idx+=1
                            continue
                  
                        x_start=max_step*i
                        y_start=max_step*j
                        z_start=max_step*k
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        z_end=z_start+max_step+1
                        array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]
                        idx+=1
            '''
            
        else:
            fix_algo_list=None

    elif args.predictor_first and args.fix_algo=="none" and args.autotuning>0:
        if 1:
            print("Start predictor tuning.")
            #tune predictor
            fix_algo_list=[]
            block_size=args.block_size
            block_max_level=int(math.log(block_size,2))
            block_num_x=(args.size_x-1)//block_size
            block_num_y=(args.size_y-1)//block_size
            block_num_z=(args.size_z-1)//block_size
            o_alpha=args.rate
            o_beta=args.maximum_rate
            if o_alpha<1:
                if args.error>=0.01:
                    args.rate=2
                    args.maximum_rate=2
                elif args.error>=0.007:
                    args.rate=1.75
                    args.maximum_rate=2
                elif args.error>=0.004:
                    args.rate=1.5
                    args.maximum_rate=2
                elif args.error>=0.001:
                    args.rate=1.25
                    args.maximum_rate=2
                else:
                    args.rate=1
                    args.maximum_rate=1
            for level in range(block_max_level-1,-1,-1):
                loss_dict={}
                pred_candidates=[]
                best_predictor=None
                best_loss=9e10
                if args.sz_interp:
                    pred_candidates+=["sz3_linear_xyz","sz3_linear_zyx","sz3_cubic_xyz","sz3_cubic_zyx"]
                if level>=args.multidim_level:
                    pred_candidates+=["linear","cubic"]#multidim temp depred
                idx=0
                for i in range(0,block_num_x,1):#steplength):
                    for j in range(0,block_num_y,1):#steplength):
                        for k in range(0,block_num_z,1):#steplength):
                            if idx%args.autotuning!=0:
                                idx+=1
                                continue
                  
                            x_start=block_size*i
                            y_start=block_size*j
                            z_start=block_size*k
                            x_end=x_start+block_size+1
                            y_end=y_start+block_size+1
                            z_end=z_start+block_size+1
                            #print(x_start)
                            #print(y_start)
                            cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                            for predictor in pred_candidates:
                                cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,error_bound,args.rate,args.maximum_rate,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                        sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                        min_sampled_points=100,random_access=False,verbose=False,\
                                                                        first_level=None if args.one_interpolator else level,last_level=0 if args.one_interpolator else level,fix_algo=predictor,fake_compression=True)
                                if args.one_interpolator:
                                    cur_loss=0
                                    for level in range(len(lsd)):
                                        if predictor in lsd[level]:
                                            cur_loss+=lsd[level][predictor]
                                    if cur_loss<best_loss:
                                        best_loss=cur_loss
                                        best_predictor=predictor



                                else:
                                    cur_loss=lsd[level][predictor]
                                    if predictor not in loss_dict:
                                        loss_dict[predictor]=cur_loss
                                    else:
                                        loss_dict[predictor]+=cur_loss
                            idx+=1
                if args.one_interpolator:
                    fix_algo_list=None
                    args.fix_algo=best_predictor
                    print("Predictor tuned. Best predictor: %s." % best_predictor)
                    break
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
                idx=0
                for i in range(0,block_num_x,1):#steplength):
                    for j in range(0,block_num_y,1):#steplength):
                        for k in range(0,block_num_z,1):#steplength):
                            if idx%args.autotuning!=0:
                                idx+=1
                                continue
                  
                            x_start=block_size*i
                            y_start=block_size*j
                            z_start=block_size*k
                            x_end=x_start+block_size+1
                            y_end=y_start+block_size+1
                            z_end=z_start+block_size+1
                        #print(x_start)
                        #print(y_start)
                            #cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                           
                            array[x_start:x_end,y_start:y_end,z_start:z_end],cur_qs,edge_qs,cur_us,_,lsd=msc3d(array[x_start:x_end,y_start:y_end,z_start:z_end],error_bound,args.rate,args.maximum_rate,9999,args.max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                                    sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,sample_rate=0.0,\
                                                                    min_sampled_points=100,random_access=False,verbose=False,first_level=level,last_level=level,fix_algo=best_predictor,fake_compression=False)
                            idx+=1
                '''
            if not args.one_interpolator:
                fix_algo_list.reverse()
                while len(fix_algo_list)<max_level:
                    fix_algo_list.append(fix_algo_list[-1])
            '''
            idx=0
            for i in range(0,block_num_x,1):#steplength):
                for j in range(0,block_num_y,1):#steplength):
                    for k in range(0,block_num_z,1):#steplength):
                        if idx%args.autotuning!=0:
                            idx+=1
                            continue
                  
                        x_start=max_step*i
                        y_start=max_step*j
                        z_start=max_step*k
                        x_end=x_start+max_step+1
                        y_end=y_start+max_step+1
                        z_end=z_start+max_step+1
                        array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]
                        idx+=1
            '''
            args.rate=o_alpha
            args.maximum_rate=o_beta



        if args.rate<1 :
            print("Alphabeta tuning started.")
            alpha_list=[1,1.25,1.5,1.75,2]
            #beta_list=[2,4,4,6,6]
            beta_list=[1.5,2,3,4]
            #rate_list=None
            max_step=args.max_step
            #max_step=16#special
            block_num_x=(args.size_x-1)//block_size
            block_num_y=(args.size_y-1)//block_size
            block_num_z=(args.size_z-1)//block_size
            steplength=int(args.autotuning**(1/3))
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
            
            block_max_level=int(math.log(args.block_size,2))
            for m,alpha in enumerate(alpha_list):
                for beta in beta_list:
                    if alpha>beta:
                        continue
                    #maybe some pruning
                    test_qs=[[] for i in range(block_max_level+1)]
                    test_us=[]
                    square_error=0
                    #zero_square_error=0
                    element_counts=0
                    #themax=-9999999999999
                    #themin=99999999999999
                    #themean=0
                    #print(themean)
                    idx=0
                    for i in range(0,block_num_x,1):#steplength):
                        for j in range(0,block_num_y,1):#steplength):
                            for k in range(0,block_num_z,1):#steplength):
                                if idx%args.autotuning!=0:
                                    idx+=1
                                    continue
                            
                                x_start=block_size*i
                                y_start=block_size*j
                                z_start=block_size*k
                                x_end=x_start+block_size+1
                                y_end=y_start+block_size+1
                                z_end=z_start+block_size+1
                                #print(x_start)
                                #print(y_start)
                                cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                                '''
                                curmax=np.max(cur_array)
                                curmin=np.min(cur_array)
                                if curmax>themax:
                                    themax=curmax
                                if curmin<themin:
                                    themin=curmin
                                '''
                                #print("a")
                                cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,error_bound,alpha,beta,9999,max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                        sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,\
                                                        lorenzo=-1,sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
                                #print("b")
                                #print(len(cur_qs[max_level]))
                                #print(len(test_qs[max_level]))
                                for level in range(block_max_level+1):
                                    #print(level)
                                    test_qs[level]+=cur_qs[level]
                                #test_us+=cur_us
                                #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                                square_error+=np.sum((array[x_start:x_end,y_start:y_end,z_start:z_end]-cur_array)**2)
                                
                                element_counts+=(block_size+1)**3 
                                idx+=1
                                #array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]

                    t_mse=square_error/element_counts
                    #zero_mse=zero_square_error/element_counts
                    if t_mse==0:
                        psnr=9999
                    else:
                        psnr=20*math.log(rng,10)-10*math.log(t_mse,10)
                    #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                    #print(zero_psnr)
                  
                    np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                    np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                    with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                        lines=f.read().splitlines()
                        cr=eval(lines[4].split("=")[-1])
                        if args.max_step>0 and args.anchor_rate==0:
                            anchor_ratio=1/(args.max_step**3)
                            cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                        bitrate=32/cr
                    os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                    #pdb=(psnr-zero_psnr)/bitrate
                    if psnr<=bestp and bitrate>=bestb:
                        if alpha**(block_max_level-1)<=beta:
                            break
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
                        test_qs=[[] for i in range(block_max_level+1)]
                        test_us=[]
                        square_error=0
                        #zero_square_error=0
                        element_counts=0
                        themax=-9999999999999
                        themin=99999999999999
                        #themean=0
                        #print(themean)
                        idx=0
                        for i in range(0,block_num_x,1):#steplength):
                            for j in range(0,block_num_y,1):#steplength):
                                for k in range(0,block_num_z,1):#steplength):
                                    if idx%args.autotuning!=0:
                                        idx+=1
                                        continue
                                    x_start=block_size*i
                                    y_start=block_size*j
                                    z_start=block_size*k
                                    x_end=x_start+block_size+1
                                    y_end=y_start+block_size+1
                                    z_end=z_start+block_size+1
                                    #print(x_start)
                                    #print(y_start)
                                    cur_array=np.copy(array[x_start:x_end,y_start:y_end,z_start:z_end])
                                    '''
                                    curmax=np.max(cur_array)
                                    curmin=np.min(cur_array)
                                    if curmax>themax:
                                        themax=curmax
                                    if curmin<themin:
                                        themin=curmin
                                    '''
                                    #print("v")
                                    cur_array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(cur_array,0,block_size+1,0,block_size+1,0,block_size+1,new_error_bound,alpha,beta,9999,max_step,args.anchor_rate,rate_list=None,x_preded=False,y_preded=False,\
                                                            sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=-1,\
                                                            sample_rate=0.0,min_sampled_points=100,random_access=False,verbose=False,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
                                    #print("d")
                                    #print(len(cur_qs[max_level]))
                                    #print(len(test_qs[max_level]))
                                    for level in range(block_max_level+1):
                                        #print(level)
                                        test_qs[level]+=cur_qs[level]
                                    #test_us+=cur_us
                                    #zero_square_error=np.sum((array[x_start:x_end,y_start:y_end]-themean*np.ones((max_step+1,max_step+1)) )**2)
                                    square_error+=np.sum((array[x_start:x_end,y_start:y_end,z_start:z_end]-cur_array)**2)
                                
                                    element_counts+=(block_size+1)**3 
                                    idx+=1
                                    #array[x_start:x_end,y_start:y_end,z_start:z_end]=orig_array[x_start:x_end,y_start:y_end,z_start:z_end]
                        t_mse=square_error/element_counts
                        #zero_mse=zero_square_error/element_counts
                        if t_mse==0:
                            psnr_r=9999
                        else:
                            psnr_r=20*math.log(rng,10)-10*math.log(t_mse,10)
                        #zero_psnr=20*math.log(themax-themin,10)-10*math.log(zero_mse,10)
                        #print(zero_psnr)
                      
                        np.array(sum(test_qs,[]),dtype=np.int32).tofile(tq_name)
                        np.array(sum(test_us,[]),dtype=np.int32).tofile(tu_name)
                        with os.popen("sz_backend %s %s" % (tq_name,tu_name)) as f:
                            lines=f.read().splitlines()
                            cr=eval(lines[4].split("=")[-1])
                            if args.max_step>0 and args.anchor_rate==0:
                                anchor_ratio=1/(args.max_step**3)
                                cr=1/((1-anchor_ratio)/cr+anchor_ratio)
                            bitrate_r=32/cr
                        os.system("rm -f %s;rm -f %s" % (tq_name,tu_name))
                        a=(psnr-psnr_r)/(bitrate-bitrate_r+1e-12)
                        b=psnr-a*bitrate
                        #print(a)
                        #print(b)
                        reg=a*bestb+b
                        if reg>bestp:
                            bestalpha=alpha
                            bestbeta=beta
                       
                            bestb=bitrate
                            bestp=psnr
                    if alpha**(block_max_level-1)<=beta:
                        break

                    
                    
                   


            print("Autotuning finished. Selected alpha: %f. Selected beta: %f. Best bitrate: %f. Best PSNR: %f."\
            %(bestalpha,bestbeta,bestb,bestp) )
            #max_step=args.max_step#special
            args.rate=bestalpha
            args.maximum_rate=bestbeta


            

    else:
        fix_algo_list=None
    if ((isinstance(rate_list,int) or isinstance(rate_list,float)) and  rate_list>0) or (isinstance(rate_list,list ) and rate_list[0]>0):

        if isinstance(rate_list,int) or isinstance(rate_list,float):
            rate_list=[rate_list]

        while len(rate_list)<max_level:
            rate_list.insert(0,rate_list[0])
    else:
        rate_list=None

    if args.rate<1:
        args.rate=1
        args.maximum_rate=1

    #print(rate_list)
    if args.interp_block_size<=0:
        array,qs,edge_qs,us,_,lsd=msc3d(array,0,args.size_x,0,args.size_y,0,args.size_z,error_bound,args.rate,args.maximum_rate,args.min_coeff_level,args.max_step,args.anchor_rate,rate_list=rate_list,x_preded=False,y_preded=False,z_preded=False,\
            sz_interp=args.sz_interp,selection_criteria=args.criteria,multidim_level=args.multidim_level,lorenzo=args.lorenzo_fallback_check,sample_rate=args.fallback_sample_ratio,min_sampled_points=100,random_access=False,verbose=True,fix_algo=args.fix_algo,fix_algo_list=fix_algo_list)
        #print(len(edge_qs))
        quants=np.concatenate( (np.array(edge_qs,dtype=np.int32),np.array(sum(qs,[]),dtype=np.int32) ) )
        unpreds=np.array(us,dtype=np.float32)
    else:
        qs=[]
        us=[]


        for level in range(max_level,-1,-1):
            print("Level %d started." % level)
            cur_interp_block_size=args.interp_block_size*(2**level)
            fix_algo= fix_algo_list[level] if fix_algo_list!=None and level!=max_level else None
            for x_start in range(0,args.size_x,cur_interp_block_size):
                if x_start+2*cur_interp_block_size>=args.size_x:
                    x_end=args.size_x
                    
                else:
                    x_end=x_start+cur_interp_block_size+1
                   
                for y_start in range(0,args.size_y,cur_interp_block_size):
                    if y_start+2*cur_interp_block_size>=args.size_y:
                        y_end=args.size_y
                      
                    else:
                        y_end=y_start+cur_interp_block_size+1
                    for z_start in range(0,args.size_z,cur_interp_block_size):
                        if z_start+2*cur_interp_block_size>=args.size_z:
                            z_end=args.size_z
                          
                        else:
                            z_end=z_start+cur_interp_block_size+1




                        array,cur_qs,edge_qs,cur_us,_,lsd=msc3d(array,x_start,x_end,y_start,y_end,z_start,z_end,error_bound,args.rate,args.maximum_rate,args.min_coeff_level,args.max_step,args.anchor_rate,rate_list=rate_list,\
                                                                        sz_interp=args.sz_interp,multidim_level=args.multidim_level,lorenzo=args.lorenzo_fallback_check,sample_rate=args.fallback_sample_ratio,\
                                                                        first_level=level,last_level=level,min_sampled_points=100,random_access=False,verbose=False,fix_algo=fix_algo,x_preded=(x_start>0),y_preded=(y_start>0),z_preded=(z_start>0))
                        qs+=sum(cur_qs,[])

                        us+=cur_us
                        if z_end==args.size_z:
                            break
                    if y_end==args.size_y:
                        break
                if x_end==args.size_x:
                    break
            #print(qs)
            print("Level %d finished." % level)
        quants=np.array(qs,dtype=np.int32)
        unpreds=np.array(us,dtype=np.float32)






    array.tofile(args.output)
    quants.tofile(args.quant)
    unpreds.tofile(args.unpred)

    '''
    for x in range(args.size_x):
        for y in range(args.size_y):
            for z in range(args.size_z):
                if array[x][y][z]==orig_array[x][y][z] and x%args.max_step!=0 and y%args.max_step!=0 and z%args.max_step!=0:
                    print(x,y,z)
    '''