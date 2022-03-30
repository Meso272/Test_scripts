import os
import numpy as np 
import argparse
import pandas as pd
if __name__=="__main__":

    parser = argparse.ArgumentParser()

    
    parser.add_argument('--input','-i',type=str)
    parser.add_argument('--output','-o',type=str)
    
   
    
    parser.add_argument('--dim','-d',type=int,default=2)
    parser.add_argument('--lorenzo','-z',type=int,default=0)
    parser.add_argument('--dims','-m',type=str,nargs="+")
    parser.add_argument('--levelwise','-l',type=int,default=0)
    parser.add_argument('--maxstep','-s',type=int,default=0)
    parser.add_argument('--blocksize','-b',type=int,default=0)
    parser.add_argument('--sample_blocksize','-e',type=int,default=0)
    
    parser.add_argument('--abtuningrate',"-a",type=float,default=0.01)
    parser.add_argument('--predtuningrate',"-p",type=float,default=0.01)
    parser.add_argument('--totaltuningrate',"-t",type=float,default=None)
    parser.add_argument('--tuning_target',"-n",type=str,default="rd")
    parser.add_argument('--linear_reduce',"-r",type=int,default=0)
    parser.add_argument('--multidim',"-u",type=int,default=0)
    parser.add_argument('--profiling',type=int,default=0)
    parser.add_argument('--fixblock',"-f",type=int,default=0)
   
    #parser.add_argument('--config','-c',type=str,default=None)
    #parser.add_argument('--ssim',"-s",type=int,default=0)
    #parser.add_argument('--size_x','-x',type=int,default=1800)
    #parser.add_argument('--size_y','-y',type=int,default=3600)
    #parser.add_argument('--size_z','-z',type=int,default=512)
    

    args = parser.parse_args()
    datafolder=args.input
    datafiles=os.listdir(datafolder)
    datafiles=[file for file in datafiles if file.split(".")[-1]=="dat" or file.split(".")[-1]=="f32" or file.split(".")[-1]=="bin"]
    num_files=len(datafiles)

    #ebs=[1e-4,1e-31]
    ebs=[1e-4,1e-3,1e-2]
    num_ebs=len(ebs)

    c_speed=np.zeros((num_ebs),dtype=np.float32)
    d_speed=np.zeros((num_ebs),dtype=np.float32)
    #nrmse=np.zeros((num_ebs,num_files),dtype=np.float32)
    #overall_cr=np.zeros((num_ebs,1),dtype=np.float32)
    #overall_psnr=np.zeros((num_ebs,1),dtype=np.float32)
    #ssim=np.zeros((num_ebs,num_files),dtype=np.float32)
    #algo=np.zeros((num_ebs,num_files),dtype=np.int32)
    #overall_ssim=np.zeros((num_ebs,1),dtype=np.float32)
    pid=os.getpid()
    total_data_size=num_files
    for d in args.dims:
        total_data_size*=eval(d)
    total_data_size=total_data_size*4/(1024*1024)
    print(total_data_size)

    if args.blocksize>0:
        blocksize=args.blocksize
        algo="ALGO_INTERP_BLOCKED"
    else:
        blocksize=32 
        algo="ALGO_INTERP_LORENZO"
    
    tuning_target_dict={"rd":"TUNING_TARGET_RD","cr":"TUNING_TARGET_CR","ssim":"TUNING_TARGET_SSIM"}
    tuning_target=tuning_target_dict[args.tuning_target]

    configstr="[GlobalSettings]\nCmprAlgo = %s \ntuningTarget = %s \n[AlgoSettings]\nautoTuningRate = %f \npredictorTuningRate= %f \nlevelwisePredictionSelection = %d \nmaxStep = %d \ninterpBlockSize = %d \ntestLorenzo = %d \nlinearReduce = %d \nmultiDimInterp = %d \nsampleBlockSize = %d \nprofiling = %d \nfixBlockSize = %d \n" % \
    (algo,tuning_target,args.abtuningrate,args.predtuningrate,args.levelwise,args.maxstep,blocksize,args.lorenzo,args.linear_reduce,args.multidim,args.sample_blocksize,args.profiling,args.fixblock) 
    with open("%s.config" % pid,"w") as f:
        f.write(configstr)



    for i,eb in enumerate(ebs):
    
        for j,datafile in enumerate(datafiles):
            
            filepath=os.path.join(datafolder,datafile)

            
            comm="sz3_qoz -z -f -a -i %s -o %s.out -M REL %f -%d %s -c %s.config" % (filepath,pid,eb,args.dim," ".join(args.dims),pid)
            
            
            with os.popen(comm) as f:
                lines=f.read().splitlines()
                print(lines)
                ct=eval(lines[-12].split('=')[-1])
                dt=eval(lines[-2].split('=')[-1].split("s")[0])
                c_speed[i]+=ct
                d_speed[i]+=dt

                
                
           

            
                
                

            
            comm="rm -f %s.out" % pid
            os.system(comm)

            
    comm="rm -f %s.config" % pid
    os.system(comm)
    c_speed=total_data_size*np.reciprocal(c_speed)
    d_speed=total_data_size*np.reciprocal(d_speed)


   
    cs_df=pd.DataFrame(c_speed,index=ebs,columns=["Compression Speed (MB/s)"])
    ds_df=pd.DataFrame(d_speed,index=ebs,columns=["Decompression Speed (MB/s)"])
    
    
    cs_df.to_csv("%s_cspeed.tsv" % args.output,sep='\t')
    ds_df.to_csv("%s_dspeed.tsv" % args.output,sep='\t')
   

    