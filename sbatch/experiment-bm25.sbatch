#!/bin/bash
#SBATCH -Jlongeval-bm25 --account=paceship-dsgt_clef2025
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=24 --mem-per-cpu=6G
#SBATCH -t600 -qinferno -oReport-%j.out
#SBATCH --mail-type=END,FAIL,SUCCESS --mail-user=acmiyaguchi@gatech.edu
#SBATCH --array=0-3%4
set -xeu

apptainer exec \
    --writable-tmpfs \
    --cleanenv \
    --env SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID \
    --cwd ~/scratch/longeval/app \
    ~/scratch/longeval/app.sif \
    bash << 'EOF'
set -xeu
hostname
source ~/scratch/longeval/app/.venv/bin/activate
python -m pyserini.index.lucene -options

project_dir=/storage/coda1/p-dsgt_clef2025/0/shared/longeval
scratch_dir=$(realpath ~/scratch/longeval)

export PYSPARK_DRIVER_CORES=24
export PYSPARK_DRIVER_MEMORY=$(($PYSPARK_DRIVER_CORES*6-4))g
export SPARK_LOCAL_DIR=${TMPDIR:-/tmp}/spark-tmp
python -m longeval.experiment.bm25.workflow \
    $project_dir/2025/parquet \
    $project_dir/2025/bm25 \
    --scratch-path $scratch_dir/bm25 \
    --parallelism $PYSPARK_DRIVER_CORES \
    --workers 12 \
    --num-sample-ids 4 \
    --sample-id $SLURM_ARRAY_TASK_ID
EOF
