## Seekfusion ##

Seekfusion is a fusion detection algorithm designed for analysis on targeted RNA assays such as Qiaseq and Archer. The pipeline is bundled in a [Docker image](https://hub.docker.com/repository/docker/jagadhesh89/seekfusion) and is available to run in a SGE mode or a local machine mode . This is a light weight pipeline and can run locally within a docker container on a single sample. The docker container contains all the tools installed required for running the pipeline. The various tools and config parameters used by pipeline can be viewed in the docker image under: pipeline/v2.00.00/src/umifusion.profile

Since the pipeline has several dependencies and reference files, a docker image would be the easy use access for users. The docker image comes with reference files and dependencies installed, so minimal work is required in set up of pipeline. If any issues are found with docker and processing samples in docker please report issue here or in docker hub. 

Once you download the container and run the container, the pipeline can be submitted using the following command:

`pipeline/v2.00.00/src/NGS_UMIFUSION/main/shell/runFusion.sh -i /pipeline/test_data/ -m local`

-i is the input sample folder that has example fastqs and example settings files. The pipeline expects all the other setting files as present in the test_data folder for each sample. 
-m is the mode . The pipeline can be run in server(SGE cromwell mode) or local mode. Values available for this option are either "local" or "server"

For using pipeline for your set of custom samples just provide a similar sample folder and just replace the example fastqs. 

The outputs are created in the input sample folder under a directory named umifusion. 
1. The vcf file with the fusion calls are located in input_folder/umifusion/reports.
2. The igv session files are located in input_folder/umifusion/reports/igv_session

### CUSTOMIZABLE OPTIONS ###

Here are some customizable options in the pipeline:

1.  Change minimum number of reads / UMIs supporting fusions - use the main.info under /pipeline/ordered_service/pipelines/umifusion/main.info and look for VCF_ReadThreshold and VCF_TagThreshold (UMI) 
2.  Change adapters to be trimmed - use the main.info under /pipeline/ordered_service/pipelines/umifusion/main.info and change the ADAPTER_FILE
3.  Change the regions that need to be looked at (change target genes)
    1.  Modify the target.bed in /pipeline/ordered_service/target.bed
    2.  Modify the genes.txt in /pipeline/ordered_service/pipelines/ for the new list of genes
    3.  Modify the reference and add the gene sequence with gene name as the contig name in reference/snapshot_v2/bwa/reference.fa and index the reference using bwa
4. Change the transcript variants that needs to be called (such as EGFR VIII): modify reference/snapshot_v2/transcript_variants.txt
5. If the pipeline needs to use deduping modify pipeline/test_data/ordered_service/os.cfg, specifically the fastqUmiDedup to yes. The fastq headers need to have the UMIs in their headers. (Similar to the format of bcl-convert software from illumina , v3.4.8)
6. Change the blocklist for noisy calls: modify reference/snapshot_v2/body_map_fusions.DB.RefSeq.txt

## CODE STRUCTURE
The source code is structured in src/NGS_UMIFUSION/main by the programming language. The wrapper script is in the shell directory, i.e runFusion.sh . This calls the cromwell wdl workflow. All wdl files are present in src/NGS_UMIFUSION/main/wdl directory. The python scripts called by the pipeline are in src/NGS_UMIFUSION/main/python directory. 

Within the docker container, the pipeline is present in the pipeline directory under the folder v2.0.0. 

## WORKFLOW OVERVIEW
![fusion dot](https://user-images.githubusercontent.com/18012162/132932345-8e6df3c3-80f0-4b4a-a0e5-8c5521fca6e1.png)

