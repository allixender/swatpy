#!/bin/bash

#The job should run on the testing partition
#SBATCH -p main

#The name of the job is test_job
#SBATCH -J swat_preprocessing

#number of different compute nodes required by the job
#SBATCH -N 1

#number of tasks to run, ie number of instances of your command executed in parallel
#SBATCH --ntasks=1

#The job requires tasks per node
#SBATCH --ntasks-per-node=1
 
# CPUs per task
#SBATCH --cpus-per-task=1
 
#memory required per node (MB, but alternatively eg 64G)
#SBATCH --mem=2GB
 
#The maximum walltime of the job is x minutes/hours
#SBATCH -t 00:15:00
 
#Notify user by email when certain events BEGIN,END,FAIL, REQUEUE, and ALL
#SBATCH --mail-type=ALL

#he email address where to send the notifications.
#SBATCH --mail-user=alexander.kmoch@ut.ee

#working directory of the job
#SBATCH --chdir=/gpfs/hpc/home/kmoch/swat

#Here we call to launch the command in parallel

module load python-3.7.1

# source activate daskgeo2020a

for i in pori3 hwsd isric10km isric5km isric1km isric250m; do
    $HOME/.conda/envs/daskgeo2020a/bin/python run_for.py -m $i
done
