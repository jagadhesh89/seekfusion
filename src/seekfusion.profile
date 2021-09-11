PIPELINE_NAME="umifusion"
STAGE_NAME="prod"

#file locations
SOURCE_HOME="/pipeline/v2.00.00/src"
SCRIPT_HOME="/pipeline/v2.00.00/src/NGS_UMIFUSION/main"
TOOLS_HOME="/pipeline/v2.00.00/tools"
CONFIGS_HOME="/pipeline/v2.00.00/configs"
WORKFLOW_ZIP="/pipeline/v2.00.00/src/NGS_UMIFUSION/src.zip"
GD_HOME="/pipeline/v2.00.00"

#automation
AUTOMATION_RUN_HOME="/automation"
AUTOMATION_PROCESSED_PATH="/automation/processed"
PROCESSED_PATH="/automation/processed"

#reference data
REFERENCES="/reference/snapshot_v2"
INSTRUMENT_FILE="/reference/snapshot_v2/instrument_config.properties"
GENOME_REFERENCE="/reference/snapshot_v2/allchr.fa"
TRANSCRIPT_REFERENCE="/reference/snapshot_v2/transcript_reference/annotated_ref.fa"
BWA_REFERENCE="/reference/snapshot_v2/bwa/reference.fa"

#working folders
TEST_DEF_HOME="/testDefinition"
TEMP_LOG_SPACE="/logs/umifusion"
RUN_DATA="/runs"
CROMWELL_FOLDER="/temp/cromwell"
CROMWELL_LOGS="/logs/umifusion"
CROMWELL_JAR="/biotools/cromwell/cromwell-49.jar"

#metadata
EMAIL_ADDRESS="balan.jagadheshwar@mayo.edu"
EMAIL_ADDRESS_FROM="balan.jagadheshwar@mayo.edu"
#sge
QSUB_QUEUE="prod.q"
QSUB_TIMEOUT=86400
SGE_CELL="default"
SGE_EXECD_PORT=6445
SGE_QMASTER_PORT=6444
SGE_ROOT="/usr/local/biotools/oge/ge2011.11"
SGE_CLUSTER_NAME="p6444"
RUNFUSION_HVMEM="16G"
RUNFUSION_THREADS="16"
RUNFUSION_HSTACK="100M"
PP_HVMEM="16G"
JAVA_MEM_INIT="4G"
JAVA_MEM_MAX="8G"
JAVA_STACK="4M"
JAVA_MAXMETASPACE="8G"
CROMWELL_S_RT="47:55:00"
CROMWELL_H_RT="48:00:00"
CROMWELL_QSUB_OPTIONS="-l umi_fusion=1"
WDL_QSUB="/pipeline/v2.00.00/src/NGS_UMIFUSION/main/shell/runCromwell.sh"


# CROMWELL AS A SERVICE
CROMWELL_PORT=""
CROMWELL_HOST=""
CROMWELL_SERVER_LOCKOUT="/temp/cromwell/"

#pipeline tools
UTILITIES="/pipeline/v2.00.00/src/NGS_PIPELINE_UTILITIES"
ROQCM_API_SUBMITTER="submitMetric.sh"
CURL="/usr/bin/curl"
SAMTOOLS="/biotools/samtools-1.10/samtools"
BAMTOOLS="/biotools/bamtools/biotools/bamtools/bin"

BEDTOOLS="/biotools/bedtools2/bin"
CAP3="/biotools/CAP3/cap3"
BLAT="/biotools/blat"
PYTHON="/usr/bin/python3.6"
PYTHON3_PKG_PROFILE="/pipeline/v2.00.00/configs/PYTHON3_PKG_PROFILE"
LD_LIBRARY_PATH="/usr/local/lib64/python3.6/"
PERL="/usr/bin/perl"
JAVA_HOME="/usr/bin/"
JAVA="/usr/bin/java"
GIT="/usr/bin/git"
QSTAT="qstat"
QACCT="qacct"
QDEL="qdel"
QSUB="qsub"
GREP="/usr/bin/grep"
CAT="/usr/bin/cat"
ZIP_UTILITY="/usr/bin/zip"
GUNZIP="/usr/bin/gunzip"
BWA="/biotools/bwa/bwa"
VCFSORT="/biotools/vcftools_0.1.13/bin/vcf-sort"

## FUSION ANNOTATION
FUSION2VCF_PATH="/pipeline/FUSION2VCF/v1.02.01"
IDENTIFYANNOTATEFUSIONS_SCRIPT="/pipeline/FUSION2VCF/v1.02.01/src/NGS_FUSION2VCF/main/shell/identify_and_annotate_potential_fusions.sh"
ANNOT_THREADS="1"

# Tools

BGZIP="/usr/local/bin/bgzip"
FASTP="/biotools/fastp/fastp"
SEQTK="/biotools/seqtk/seqtk"
SENTIEON="/biotools/sentieon/201808.03"


# Environment Profiles
ALIGNMENT_ENVPROFILE="/pipeline/v2.00.00/configs/PYTHON3_PKG_PROFILE"
BASH_PREAMBLE="/pipeline/v2.00.00/src/NGS_UMIFUSION/main/shell/shell_preamble.sh"
BASH_SHARED_FUNCTIONS="/pipeline/v2.00.00/src/NGS_UMIFUSION/main/shell/shared_functions.sh"
DEDUP_ENV_PROFILE="/pipeline/v2.00.00/configs/PYTHON3_PKG_PROFILE"
DEDUP_BIN="/pipeline/dedup/fastq_umi_dedup/build/fastq_umi_dedup"
ALIGNMENT_SCRIPT="/pipeline/v2.00.00/src/NGS_UMIFUSION/main/shell/sentieon_bwa.sh"

# Memory and Threads
BLAT_READS_hvmem="16G"
BLAT_CONTIGS_hvmem="16G"
umifusionCap3mem="64G"
EACHFP_hvmem="16G"
SENTIEONTHREADS="32"
umifusionBWAmem="32G"
INFRAME_hvmem="20G"
PICARD_hvmem="40G"
PICARD_MEM="-Xmx7g"
trim_hvmem="50G"
VCF_hvmem="50G"


# ROQCM
ROQCM_API="/ROQCM_CLI/"

DELIVERY_DISPATCH="/pipeline/FILE_MANGEMENT/deliveryDispatcher.sh"