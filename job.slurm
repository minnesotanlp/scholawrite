#!/bin/bash -l        

#SBATCH --time=23:00:00
#SBATCH -N 1
#SBATCH --ntasks=8
#SBATCH --mem=100g
#SBATCH --tmp=10g
#SBATCH --mail-type=BEGIN,END,FAIL  
#SBATCH --mail-user=volko032@umn.edu 
#SBATCH -o slurm_output/%j.out
#SBATCH -e slurm_output/%j.err
#SBATCH -p interactive-gpu
#SBATCH --gres=gpu:a40:1

module load conda
conda info --envs
source /users/0/volko032/.bashrc
source activate /users/0/volko032/miniconda3/envs/sw

conda list
pip freeze

cd /users/0/volko032/scholawrite
which python
which python3
/users/0/volko032/miniconda3/envs/sw/bin/python3 src/intention_classifier.py > slurm_output/out.txt