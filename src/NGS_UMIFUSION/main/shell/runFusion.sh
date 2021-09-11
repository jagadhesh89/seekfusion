#!/bin/bash
SCRIPT_NAME="$(basename ${0})"
PIPELINE_NAME="UMIFUSION"

read -r -d '' MANIFEST <<MANIFEST
manifest
*******************************************
${SCRIPT_NAME}
call: ${0} ${*}
path: ${PWD}
real_call: `readlink -m ${0}` ${*}
real_path: $(pwd -P)
user: `whoami`
date: `date`
hostname: $(hostname)
*******************************************
MANIFEST
echo "Starting ${SCRIPT_NAME}"

umifusionPostHoldDelay="3600" # wait 3600 seconds before launching post-process in server mode - overridable anywhere

##################################################
#Usage
##################################################

read -r -d '' DOCS <<DOCS
\n
runFusion.sh usage: $0 options

OPTIONS:
    -h            [optional]  help, Show this message
    -d            [optional]  specifiying this flag enables debug.
    -i <path>     [required]  input directory, full path to a processed sample
\n
DOCS


##################################################
#Bash handling
##################################################

set -o errexit
set -o pipefail
set -o nounset


##################################################
#Source Pipeline Profile
##################################################

echo ""
echo " Pipeline preprocessing "

SCRIPT=$( readlink -m $( type -p $0 ))
SCRIPT_DIR=$(dirname ${SCRIPT})
SCRIPT_NAME=$(basename ${SCRIPT})

_FIND_PATH=${SCRIPT_DIR}
while [[ ${_FIND_PATH} != "$(dirname "${_FIND_PATH}" )" && ! -f "${_FIND_RESULT:-}" ]];
do
    _FIND_RESULT=$(find "${_FIND_PATH}" -maxdepth 1 -mindepth 1 -iname "${PIPELINE_NAME,,}.profile")
    _FIND_PATH="$(readlink -f "${_FIND_PATH}"/..)"
done

PIPELINE_PROFILE=${_FIND_RESULT}

if [[ ! -f "${PIPELINE_PROFILE}" ]]; then
    echo "$(basename ${PIPELINE_PROFILE}) was not found. Unable to continue: ${PIPELINE_PROFILE}"
    exit 1
fi

echo "Using configuration file at: ${PIPELINE_PROFILE}"
source "${PIPELINE_PROFILE}"

LOG_DIR="${TEMP_LOG_SPACE}"
LOG_NAME="${SCRIPT_NAME}.log_$$"

echo "${MANIFEST}" >> "${LOG_DIR}/${LOG_NAME}"


##################################################
#FUNCTIONS
##################################################

COMMON_FUNC="${UTILITIES}/src/main/bash/commonFunctions.sh"
if [[ ! -f ${COMMON_FUNC} ]]; then
    echo -e "\nERROR: The common UTILITIES do not appear to be installed: ${UTILITIES}\n"
    exit 1
fi

echo "Using common functions: ${COMMON_FUNC}"
source "${COMMON_FUNC}"

setupLogging "${LOG_DIR}" "${LOG_NAME}" "all"


reportError() {
    logError "Error occurred on line: ${BASH_LINENO} during execution" 50
    mailUser "${EMAIL_ADDRESS}" "${PIPELINE_NAME^^}: Unexpected error in ${SCRIPT_NAME}"  "See error log at: ${LOG_FILE:-undefined}"
}

trap 'reportError' ERR SIGHUP SIGINT SIGTERM


##################################################
#INPUT
##################################################

if [[ $# -eq 0 ]]
then
    logInfo "${DOCS}"
    exit ${ERR_GENERAL} 
fi
DEBUG_OPT=" "
while getopts ":hdi:" OPTION
do
    case $OPTION in
        h) logInfo "${DOCS}"; exit ${INF_OK} ;;
        d) set -o xtrace ; DEBUG_OPT="-d" ;;
        i) SAMPLE_DIR="$(readlink -m ${OPTARG})" ;;
        \?) logInfo "Invalid option: ${OPTARG}"; exit ${ERR_GENERAL} ;;
        :) logInfo "Missing argument for ${OPTARG}"; exit ${ERR_GENERAL} ;;
        *) logInfo "Unexpected option ${OPTARG}"; exit ${ERR_GENERAL} ;;
    esac
done


##################################################
#VERIFY REQUIRED PARMS
##################################################

validateParm "SAMPLE_DIR" "Please specify a sample dir with option: -i"
validateDirectory "${SAMPLE_DIR}"

OUTPUT_DIR="${SAMPLE_DIR}/${PIPELINE_NAME,,}"

if [[ -d ${OUTPUT_DIR} ]]; then
    logError "The process appears to have already been started, backup or remove the $(dirname ${OUTPUT_DIR}) directory to continue: ${OUTPUT_DIR}" "${ERR_GENERAL}"
    exit "${ERR_GENERAL}"
fi

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/logs"
LOG_DIR="${OUTPUT_DIR}/logs"
cp "${LOG_FILE}" "${LOG_DIR}/main.log"
LOG_FILE="${LOG_DIR}/main.log"

SAMPLE_SHEET="${SAMPLE_DIR}/SampleSheet.csv"
validateFile "${SAMPLE_SHEET}"

SAMPLE_SHEET_NAME=$(basename "${SAMPLE_SHEET}")

SPECIMEN_INFO="${SAMPLE_DIR}/Specimen.info"
validateFile "${SPECIMEN_INFO}"


#################################################
#check if ordered service folder exists under the sample directory
#################################################
ORDERED_SERVICE="${SAMPLE_DIR}/ordered_service"
CHECK_MODE="normal" #default is to check RECIPE if ordered services folder does not exist
if [[ -d ${ORDERED_SERVICE} ]]; then
    CHECK_MODE="cgo";
    logInfo "Ordered service folder is in the sample directory and used as configuration";
fi

##################################################
#VARIABLE DEFINITIONS & DIRECTORY SETUP
##################################################

RECIPE=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "Recipe")'}' ${SAMPLE_SHEET} | tail -1)
PROJECT_NAME=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "SampleProject")'}' ${SAMPLE_SHEET} | tail -1)
SAMPLE_TYPE=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "Control")'}' ${SAMPLE_SHEET} | tail -1)
if [[ ${SAMPLE_TYPE^^} == "Y" ]]; then
    SAMPLE_TYPE="control"
else
    SAMPLE_TYPE="case"
fi
SAMPLE_ID=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "SampleID")'}' ${SAMPLE_SHEET} | tail -1)
LANE=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "Lane")'}' ${SAMPLE_SHEET} | tail -1)
SAMPLE_PROJECT=$(awk -F"," '{print $'$(getIndex "${SAMPLE_SHEET}" "SampleProject")'}' ${SAMPLE_SHEET} | tail -1)
BATCH_NAME=$(echo ${SAMPLE_PROJECT} | cut -d_ -f2)

############################cgo incorporation######################
if [[ "${CHECK_MODE}" == "normal" ]]; then
    echo "Ordered service folder is not in the sample directory and RECIPE is checked"
    if [[ -z "${RECIPE}" ]]; then
        logError "Could not find recipe in sample sheet: ${SAMPLE_SHEET}"
        exit ${ERR_GENERAL}
    fi
    validateDirectory "${TEST_DEF_HOME}"
    OS_DIR="${TEST_DEF_HOME}/${RECIPE}"
else    #the "cgo" mode
    OS_DIR="${ORDERED_SERVICE}"
fi
###################################################################

OS_CONFIG="${OS_DIR}/os.cfg"
OS_PIPELINE_DIR="${OS_DIR}/pipelines/${PIPELINE_NAME,,}"
PIPELINE_MAIN_INFO="${OS_PIPELINE_DIR}/main.info"


CONFIG_DIR="${OUTPUT_DIR}/configs"
mkdir "${CONFIG_DIR}"
JSON_INPUT="${CONFIG_DIR}/inputs.json"
JSON_CONFIG="${CONFIG_DIR}/configs.json"

SAMPLE_NAME=$(basename ${SAMPLE_DIR})

logInfo "Command run: $(basename $0) ${*}"

logInfo " Pre execution validation "

validateFile "${OS_CONFIG}"
cp ${OS_CONFIG} "${CONFIG_DIR}/os.cfg"
OS_CONFIG="${CONFIG_DIR}/os.cfg"

validateFile "${PIPELINE_MAIN_INFO}"
cp "${PIPELINE_MAIN_INFO}" "${CONFIG_DIR}/main.info"
PIPELINE_MAIN_INFO="${CONFIG_DIR}/main.info"

validateFile "${SPECIMEN_INFO}"
source "${SPECIMEN_INFO}"

# /dlmp/misc-data/pipelinedata/deployments/instrumentation/instrument_config.properties

validateFile "${INSTRUMENT_FILE}"
source "${INSTRUMENT_FILE}"

DEVICE_NAME=$(echo ${RUN_DIR_BASE} | cut -d "_" -f 2)
SEQUENCER="$(readOption ${INSTRUMENT_FILE} "${DEVICE_NAME}_TYPE")"
PLATFORM="$(readOption ${INSTRUMENT_FILE} "${DEVICE_NAME}_COMPANY")"
CENTER="$(readOption ${INSTRUMENT_FILE} "${DEVICE_NAME}_CENTER")"


if [[ ${SEQUENCER} == "" ]]; then
    logError "Unable to identify sequencer from device type: ${DEVICE_NAME} in ${INSTRUMENT_FILE}" ${ERR_GENERAL}
    exit ${ERR_GENERAL}
fi

if [[ ${PLATFORM} == "" ]]; then
    logError "Unable to identify company from device type: ${DEVICE_NAME} in ${INSTRUMENT_FILE}" ${ERR_GENERAL}
    exit ${ERR_GENERAL}
fi

if [[ ${CENTER} == "" ]]; then
    logWarn "Unable to identify center from device type: ${DEVICE_NAME} in ${INSTRUMENT_FILE}. Defaulting to CGSL."
    CENTER="CGSL"
fi

source "${PIPELINE_MAIN_INFO}"
source "${OS_CONFIG}"

MASTER_PANEL="$(readOption ${OS_CONFIG} "masterPanel")"
RUN_UMIDEDUP="$(readOption ${OS_CONFIG} "fastqUmiDedup")"

RESOURCES_HOME="${SCRIPT_HOME}/resources"

SGE_CONFIG="${CONFIGS_HOME}/sge.conf"
validateFile "${SGE_CONFIG}"

FQ_R1_ARR=( $(find ${SAMPLE_DIR} -maxdepth 1 -name "*_R1*fastq*") )
FQ_R2_ARR=( $(find ${SAMPLE_DIR} -maxdepth 1 -name "*_R2*fastq*") )

if [[ ${#FQ_R1_ARR[@]} -lt 1 ]]; then
    logError "No valid R1 fastq's were found for processing"
    exit ${ERR_GENERAL}
fi

if [[ ${#FQ_R2_ARR[@]} -lt 1 ]]; then
    logError "No valid R2 fastq's were found for processing"
    exit ${ERR_GENERAL}
fi

OUTPUT_JSON="${CONFIG_DIR}/outputs.json"

## Parse fastqUmiDedup option

UMIDEDUP_FLAG="false"

# strip single and double quotes from RUN_UMIDEDUP
RUN_UMIDEDUP=$(echo ${RUN_UMIDEDUP} | sed -e 's|["'\'']||g' )
if [[ "${RUN_UMIDEDUP,,}" == "yes" ]]; then
    UMIDEDUP_FLAG="true"
    logInfo "fastqUmiDedup option in os.cfg is \'yes\' - calling Fastq UMI Dedup task."
else
    logInfo "fastqUmiDedup option in os.cfg is not \'yes\' - UMI based read deduplication will not be done."
fi

##################################################
#NOTIFICATION
##################################################

logInfo "$(cat <<EOM
Pipeline Run Details

SAMPLE_NAME:            ${SAMPLE_NAME}

SCRIPT DATA

SCRIPT_HOME:            ${SCRIPT_HOME}
SOURCE_HOME:            ${SOURCE_HOME}
TOOLS_HOME:             ${TOOLS_HOME}
CONFIGS_HOME:           ${CONFIGS_HOME}
REFERENCES:             ${REFERENCES}
TEMP_LOG_SPACE:         ${TEMP_LOG_SPACE}
RESOURCES_HOME:         ${RESOURCES_HOME}

SGE DATA

QSUB_QUEUE:             ${QSUB_QUEUE}
QSUB_TIMEOUT:           ${QSUB_TIMEOUT}
CROMWELL S_RT:          ${CROMWELL_S_RT-}
CROMWELL H_RT:          ${CROMWELL_H_RT-}
CROMWELL QSUB OPTIONS:  ${CROMWELL_QSUB_OPTIONS-}

SAMPLE DATA

SAMPLE_DIR:             ${SAMPLE_DIR}
SAMPLE_TYPE:            ${SAMPLE_TYPE}
SAMPLE_SHEET:           ${SAMPLE_SHEET}
SPECIMEN_INFO:          ${SPECIMEN_INFO}
SAMPLE_SHEET_NAME:      ${SAMPLE_SHEET_NAME}
BATCH_NAME:             ${BATCH_NAME}
SAMPLE_PROJECT:         ${SAMPLE_PROJECT}
RUN_DIR_BASE:           ${RUN_DIR_BASE}
SAMPLE_ID:              ${SAMPLE_ID}
SEQUENCER:              ${SEQUENCER}
PLATFORM: (company)     ${PLATFORM}
CENTER:                 ${CENTER}
FASTQ ARRAYS:
FQ_R1_ARR:
$(for fq in "${FQ_R1_ARR[@]}"; do echo -e " - $fq"; done)
FQ_R2_ARR:
$(for fq in "${FQ_R2_ARR[@]}"; do echo -e " - $fq"; done)

ORDERED SERVICE DATA

TEST_DEF_HOME:          ${TEST_DEF_HOME}
RECIPE:                 ${RECIPE}
MASTER_PANEL:           ${MASTER_PANEL}
PROJECT_NAME:           ${PROJECT_NAME}
OS_CONFIG:              ${OS_CONFIG}
OS_PIPELINE_DIR:        ${OS_PIPELINE_DIR}

WDL DATA

JSON_INPUT:             ${JSON_INPUT}
JSON_CONFIG:            ${JSON_CONFIG}
CROMWELL_FOLDER:        ${CROMWELL_FOLDER}
CROMWELL_LOGS:          ${CROMWELL_LOGS}
SGE_CONFIG:             ${SGE_CONFIG}
OUTPUT_JSON:            ${OUTPUT_JSON}

RESULTS

OUTPUT_DIR:             ${OUTPUT_DIR}
CONFIG_DIR:             ${CONFIG_DIR}
DEVICE_NAME:            ${DEVICE_NAME}

\n
EOM
)"


##################################################
#BEGIN PROCESSING
##################################################

logInfo " Beginning processing "

FQ1_STR="[ \"${FQ_R1_ARR[0]}\""
for i in "${FQ_R1_ARR[@]:1}"
do
    FQ1_STR="${FQ1_STR}, \"${i}\""
done
FQ1_STR="${FQ1_STR} ]"

FQ2_STR="[ \"${FQ_R2_ARR[0]}\""
for i in "${FQ_R2_ARR[@]:1}"
do
    FQ2_STR="${FQ2_STR}, \"${i}\""
done
FQ2_STR="${FQ2_STR} ]"

#build json
cat << EOF > "${JSON_INPUT}"
{
  "UMIFUSION.sample_R1_fastq_gz_arr": ${FQ1_STR},
  "UMIFUSION.sample_R2_fastq_gz_arr": ${FQ2_STR},
  "UMIFUSION.UMIDedup": ${UMIDEDUP_FLAG},
  
  "UMIFUSION.TRANSCRIPT_REFERENCE" : "${TRANSCRIPT_REFERENCE}",
  
  "UMIFUSION.RECIPE" : "${RECIPE}",
  "UMIFUSION.OUTPUT_DIR": "${OUTPUT_DIR}",
  "UMIFUSION.SAMPLE_TYPE": "${SAMPLE_TYPE}",
  "UMIFUSION.SAMPLE_SHEET": "${SAMPLE_SHEET}",
  "UMIFUSION.SAMPLE_ID": "${SAMPLE_ID}",
  "UMIFUSION.RUN_NAME": "${RUN_DIR_BASE}",
  "UMIFUSION.SAMPLE_PROJECT": "${SAMPLE_PROJECT}",
  "UMIFUSION.BATCH_NAME": "${BATCH_NAME}",

  "UMIFUSION.QUEUE": "${QSUB_QUEUE}",
  "UMIFUSION.MAIL": "${EMAIL_ADDRESS}",
  "UMIFUSION.PLATFORM": "${PLATFORM}",
  "UMIFUSION.CENTER": "${CENTER}",
  
  "UMIFUSION.FASTP": "${FASTP}",
  "UMIFUSION.TrimFastq.ADAPTER_FILE": "${OS_PIPELINE_DIR}/adapters.fa",
  

  "UMIFUSION.CAP3" : "${CAP3}",
  "UMIFUSION.PYTHON" : "${PYTHON}",
  "UMIFUSION.LD_LIBRARY_PATH" : "${LD_LIBRARY_PATH}",
  "UMIFUSION.BLAT" : "${BLAT}",
  "UMIFUSION.SAMTOOLS" : "${SAMTOOLS}",
  "UMIFUSION.BEDTOOLS" : "${BEDTOOLS}",
  "UMIFUSION.PERL": "${PERL}",
  "UMIFUSION.GUNZIP": "${GUNZIP}",
  "UMIFUSION.BGZIP": "${BGZIP}",
  "UMIFUSION.CAT": "${CAT}",
  "UMIFUSION.BWA": "${BWA}",
  "UMIFUSION.VCFSORT": "${VCFSORT}",
  "UMIFUSION.JAVA": "${JAVA}",

  "UMIFUSION.BlatReads.blat_hvmem" : "${BLAT_READS_hvmem}",
  "UMIFUSION.BlatContigs.blat_hvmem" : "${BLAT_CONTIGS_hvmem}",
 "UMIFUSION.BwaMemBins.bwa_hvmem" : "${umifusionBWAmem:-32G}",
  "UMIFUSION.InframeAnnotation.inframe_hvmem" : "${INFRAME_hvmem}",
  "UMIFUSION.VCF_Convert.vcf_hvmem" : "${VCF_hvmem}",
  "UMIFUSION.Generate_Custom_Reference.bwa_hvmem" : "${umifusionBWAmem:-32G}",
  "UMIFUSION.TrimFastq.trim_hvmem" : "${trim_hvmem}",
  "UMIFUSION.DedupFastq.MBCLEN" : "${MBCLEN}",

  "UMIFUSION.MERGEBINS" : "${SCRIPT_HOME}/python/MergeBins.py",
  "UMIFUSION.BLATFILTER" : "${SCRIPT_HOME}/python/ReadBlat.py",
  "UMIFUSION.Filter_Final_Report.Script": "${SCRIPT_HOME}/python/ReportFilter.py",
  "UMIFUSION.InframeAnnotation.CosmicScript": "${SCRIPT_HOME}/python/CosmicBlockCheck.py",
  "UMIFUSION.VCF_Convert.VCF_Script": "${DEPLOYED_FUSION2VCF_REPO}/main/python/qiagen_fusion_make_vcf.py",
  "UMIFUSION.VCF_Convert.IGV_Script": "${SCRIPT_HOME}/python/igv_report.py",
  "UMIFUSION.VCF_Convert.SPANCHECK_Script": "${SCRIPT_HOME}/python/filter_non_spanning.py",
  "UMIFUSION.VCF_Convert.FF_Script": "${SCRIPT_HOME}/python/frequency_estimator.py",
  "UMIFUSION.Make_GTF.Script": "${SCRIPT_HOME}/python/igv_vcf.py",
  "UMIFUSION.ReadCount_Metrics.Script": "${SCRIPT_HOME}/python/read_count_metric.py",
  "UMIFUSION.DedupFastq.FQDEDUP": "${SCRIPT_HOME}/shell/fastq_dedup.sh",

  "UMIFUSION.BlatFilterAssemblePP.cap3_hvmem": "${umifusionCap3mem:-64G}",
  "UMIFUSION.BlatFilterAssemblePP.BlatContigPPScript": "${SCRIPT_HOME}/python/ContigBlatHandler.py",
  "UMIFUSION.BlatFilterAssemblePP.Script": "${SCRIPT_HOME}/python/EachFP.py",
  "UMIFUSION.BlatFilterAssemblePP.MinIdentity": ${BlatReads_MinIdentity},
  "UMIFUSION.BlatFilterAssemblePP.RepMatch": ${BlatReads_RepMatch},
  "UMIFUSION.BlatFilterAssemblePP.StepSize": ${BlatReads_StepSize},
  "UMIFUSION.BlatFilterAssemblePP.MinScore": ${BlatReads_MinScore},
  "UMIFUSION.BlatFilterAssemblePP.UniqueBasesThreshold": ${BlatContigPP_UniqueBasesThreshold},

  "UMIFUSION.GenomeFasta": "${GENOME_REFERENCE}",
  "UMIFUSION.ref_primers": "${OS_PIPELINE_DIR}/primers.bed",
  "UMIFUSION.REFERENCE": "${BWA_REFERENCE}",
  "UMIFUSION.GENELIST": "${OS_PIPELINE_DIR}/genes.txt",
  "UMIFUSION.panel_bed" : "${OS_DIR}/target.bed",
  "UMIFUSION.BlatFilterAssemblePP.ExonStart": "${REFERENCES}/Homo_sapiens.GRCh37.75.Exon_Start.15bases_up_down_exon.bed",
  "UMIFUSION.BlatFilterAssemblePP.ExonEnd": "${REFERENCES}/Homo_sapiens.GRCh37.75.Exon_End.15bases_up_down_exon.bed",
  "UMIFUSION.BlatFilterAssemblePP.ExonCoords": "${REFERENCES}/ExonCoordinates.txt",
  "UMIFUSION.BlatFilterAssemblePP.HGNC": "${REFERENCES}/HGNC_Genes.txt",
  "UMIFUSION.BlatFilterAssemblePP.ENSSTART": "${REFERENCES}/Homo_sapiens.GRCh37.75.Exon_Start.15bases_up_down_exon.bed",
  "UMIFUSION.BlatFilterAssemblePP.ENSEND": "${REFERENCES}/Homo_sapiens.GRCh37.75.Exon_End.15bases_up_down_exon.bed",
  "UMIFUSION.BlatFilterAssemblePP.COMMONSEQ": "${RESOURCES_HOME}/8mer.txt",
  "UMIFUSION.BlatFilterAssemblePP.REFGENOME": "${GENOME_REFERENCE}",

  "UMIFUSION.InframeAnnotation.REFERENCE_GENOME": "${GENOME_REFERENCE}",
  "UMIFUSION.InframeAnnotation.REFERENCE_DICT": "${GENOME_REFERENCE}.dict",
  "UMIFUSION.InframeAnnotation.Ref_CosmicFile": "${REFERENCES}/CosmicFusionExport.tsv",
  "UMIFUSION.InframeAnnotation.ALL_GENES_EXON_TRANSCRIPTS": "${REFERENCES}/All_Genes.exons.transcripts.bed",
  "UMIFUSION.InframeAnnotation.CLINICAL_GENE_LIST_CASE": "${REFERENCES}/Clinical_Genes.bed",
  "UMIFUSION.InframeAnnotation.CLINICAL_GENE_LIST_CONTROL": "${REFERENCES}/Clinical_Genes.for_controls.bed",
  "UMIFUSION.InframeAnnotation.EXON_FEATURES_START_CODON": "${REFERENCES}/Start_Codons.Exons.txt",
  "UMIFUSION.InframeAnnotation.EXON_FEATURES_STOP_CODON": "${REFERENCES}/Stop_Codons.Exons.txt",
  "UMIFUSION.InframeAnnotation.EXON_START_LIST": "${REFERENCES}/Exon_Start.15bases_up_down_exon.bed",
  "UMIFUSION.InframeAnnotation.EXON_END_LIST": "${REFERENCES}/Exon_End.15bases_up_down_exon.bed",
  "UMIFUSION.InframeAnnotation.EXON_BODY_LIST": "${REFERENCES}/Exon_Body.bed",
  "UMIFUSION.InframeAnnotation.EXON_CDS_FRAME": "${REFERENCES}/frame_per_CDS.txt",
  "UMIFUSION.InframeAnnotation.COSMIC_FUSIONS": "${REFERENCES}/COSMIC_fusions.with_histology.txt",
  "UMIFUSION.InframeAnnotation.FALSE_FUSIONS_LIST": "${REFERENCES}/body_map_fusions.DB.RefSeq.txt",
  "UMIFUSION.InframeAnnotation.PRIORITY_FUSIONS_LIST": "${REFERENCES}/White_list.txt",
  "UMIFUSION.InframeAnnotation.INTRON_LENGTH": "${INTRON_LENGTH}",
  "UMIFUSION.InframeAnnotation.SUPPORTING_READS": "${SUPPORTING_READS}",
  "UMIFUSION.InframeAnnotation.EXON_PADDING": "${EXON_PADDING:-5}",
  "UMIFUSION.InframeAnnotation.SCRIPT_PATH": "${DEPLOYED_FUSION2VCF_REPO}/main/perl",
  "UMIFUSION.InframeAnnotation.BEDTOOLS": "${BEDTOOLS}",
  "UMIFUSION.InframeAnnotation.IdentifyAnnotateFusionsEnvProfile" : "${PYTHON3_PKG_PROFILE}",
  "UMIFUSION.InframeAnnotation.IdentifyAnnotateFusionsScript" : "${IDENTIFYANNOTATEFUSIONS_SCRIPT}",
  "UMIFUSION.InframeAnnotation.PERL" : "${PERL}",
  "UMIFUSION.InframeAnnotation.IdentifyAnnotateFusionsThreads" : "${ANNOT_THREADS}",
  "UMIFUSION.InframeAnnotation.BashPreamble" : "${SCRIPT_HOME}/shell/shell_preamble.sh",
  "UMIFUSION.InframeAnnotation.BashSharedFunctions" : "${BASH_SHARED_FUNCTIONS}",
  "UMIFUSION.InframeAnnotation.STARFORMAT_REPORT_CREATOR" : "${SCRIPT_HOME}/python/ReportCreator.py",
  "UMIFUSION.InframeAnnotation.ANNOT_STAR_TEMPLATE" : "${RESOURCES_HOME}/star_template.tsv",
  "UMIFUSION.InframeAnnotation.REFORMATTER" : "${SCRIPT_HOME}/python/Formatter.py",
  "UMIFUSION.InframeAnnotation.DebugMode" : "${DEBUG_OPT}",
  "UMIFUSION.InframeAnnotation.PYTHONSCRIPT_PATH": "${DEPLOYED_FUSION2VCF_REPO}/main/python",

  "UMIFUSION.CosmicCheck.Script": "${SCRIPT_HOME}/python/CosmicBlockCheck.py",
  "UMIFUSION.CosmicCheck.CosmicFile": "${REFERENCES}/CosmicFusionExport.tsv",
  "UMIFUSION.CosmicCheck.CC_HVMEM": "${umifusionCosmicHVMem:-8G}",
  "UMIFUSION.CosmicCheck.CC_CPU": "${umifusionCosmicCpu:-1}",

  "UMIFUSION.DedupFastq.DEDUP_BIN": "${DEDUP_BIN}",
  "UMIFUSION.DedupFastq.DEDUP_ENV_PROFILE": "${DEDUP_ENV_PROFILE}",
  "UMIFUSION.DedupFastq.BASH_PREAMBLE": "${BASH_PREAMBLE}",

  "UMIFUSION.Filter_Final_Report.PreferredTranscripts": "${OS_PIPELINE_DIR}/transcripts.txt",
  "UMIFUSION.Filter_Final_Report.TranscriptVariants": "${REFERENCES}/transcript_variants.txt",
  "UMIFUSION.Make_GTF.GeneStrand": "${REFERENCES}/GeneStrand.txt",
  "UMIFUSION.Make_GTF.ControlReference": "${REFERENCES}/control_reference.fa",
  "UMIFUSION.Make_GTF.ControlGTF": "${RESOURCES_HOME}/GTF_temp.txt",
  "UMIFUSION.Make_GTF.ControlFusions": "${REFERENCES}/control_fusions.txt",
  "UMIFUSION.Make_GTF.XMLTemplate": "${RESOURCES_HOME}/igv_session.xml",

  "UMIFUSION.SplitBamToGene.bwa_hvmem" : "${umifusionBWAmem:-32G}",
  "UMIFUSION.SplitBamToGene.Downsample" : "${Downsample}",
  "UMIFUSION.SplitBamToGene.RemoveDups": "${SCRIPT_HOME}/python/RemoveDups.py",
  "UMIFUSION.SplitBamToGene.AllowedDups": "${AllowedDups}",
  "UMIFUSION.SplitBamToGene.CUT": "${CUT}",
  "UMIFUSION.SplitBamToGene.ECHO": "${ECHO}",
  "UMIFUSION.SplitBamToGene.HEAD": "${HEAD}",
  "UMIFUSION.SplitBamToGene.MV": "${MV}",
  "UMIFUSION.SplitBamToGene.PASTE": "${PASTE}",
  "UMIFUSION.SplitBamToGene.SED": "${SED}",
  "UMIFUSION.SplitBamToGene.SORT": "${SORT}",
  "UMIFUSION.SplitBamToGene.TOUCH": "${TOUCH}",
  "UMIFUSION.SplitBamToGene.TR": "${TR}",
  "UMIFUSION.SplitBamToGene.UNIQ": "${UNIQ}",
  "UMIFUSION.SplitBamToGene.WC": "${WC}",
  "UMIFUSION.Make_GTF.BASESREQ": "${ChimericLen}",

  "UMIFUSION.VCF_Convert.VCFHeader": "${REFERENCES}/VCF_header",

  "UMIFUSION.VCF_Convert.VCF_ReadThreshold": "${VCF_ReadThreshold}",
  "UMIFUSION.VCF_Convert.VCF_TagThreshold": "${VCF_TagThreshold}",
  "UMIFUSION.VCF_Convert.Padding": "${Padding}",
  "UMIFUSION.VCF_Convert.HighGC": "${HighGC}",
  "UMIFUSION.VCF_Convert.LowGC": "${LowGC}",

  "UMIFUSION.Control_Metrics.Script" : "${SCRIPT_HOME}/python/control_metric.py",
  
  "UMIFUSION.ALIGNMENT_SCRIPT": "${ALIGNMENT_SCRIPT}",
  "UMIFUSION.ALIGNMENT_ENVPROFILE": "${ALIGNMENT_ENVPROFILE}",
  "UMIFUSION.SENTIEON" : "${SENTIEON}",
  "UMIFUSION.SENTIEONTHREADS" : "${SENTIEONTHREADS}",
  "UMIFUSION.BASH_PREAMBLE" : "${BASH_PREAMBLE}",
  "UMIFUSION.BASH_SHARED_FUNCTIONS" : "${BASH_SHARED_FUNCTIONS}",
  "UMIFUSION.ALIGN_CHUNK_SIZE_BASES" : "${ALIGN_CHUNK_SIZE_BASES}",
  "UMIFUSION.BWA_EXTRA_OPTIONS" : "${BWA_EXTRA_OPTIONS}",
  "UMIFUSION.SEQTK" : "${SEQTK}",

  "UMIFUSION.SubmitMetrics.ROQCM_API": "${ROQCM_API}",
  
  "COMMACATCHCAUSEIMFORGETFUL": ""
}
EOF

cat << EOF > "${JSON_CONFIG}"
{
  "final_workflow_log_dir": "${LOG_DIR}",
  "final_call_logs_dir": "${LOG_DIR}"
}
EOF

# Check for presence of cromwell service
# If this exists, we will submit a script to query periodically after a set delay
# to determine whether we can run post_process. Otherwise, fail over to stand-alone script

CROMWELL_SERVICE="false"
if [[ -n ${CROMWELL_HOST:-} && -n ${CROMWELL_PORT:-} ]]; then
    ## Check whether the lockout tag is present in cromwell temp folder
    if [[ ! -f "${CROMWELL_SERVER_LOCKOUT}" ]]; then
        set +o errexit
        result=$( ${CURL} \
            -s \
            -o /dev/null \
            -w "%{http_code}" \
            -X GET "http://${CROMWELL_HOST}:${CROMWELL_PORT}/engine/v1/status" ) || true
        # We swallow errors so we don't email if the server is not present
        set -o errexit
        if [[ "${result}" != "200" ]]; then
            logInfo "Cromwell server not found querying ${CROMWELL_HOST}:${CROMWELL_PORT}."
            logInfo "Using standalone submission."
        else
            logInfo "Cromwell found on ${CROMWELL_HOST}:${CROMWELL_PORT}"
            CROMWELL_SERVICE="true"
        fi # service availability check
    else
        logInfo "Cromwell server is locked for maintenance by ${CROMWELL_SERVER_LOCKOUT}."
        logInfo "Using standalone submission."
    fi # service lockout check
fi


WORKFLOW="${SCRIPT_HOME}/wdl/fusion.wdl"
PP_SCRIPT="${SCRIPT_HOME}/shell/postProcess.sh"
POST_QSUB="${CONFIG_DIR}/postProcess.qsub"
RC_FILE=${LOG_DIR}/cromwell.rc

if [[ ${CROMWELL_SERVICE} == "false" ]]; then

  ## Standalone Service
  # WDL_QSUB set by installer to main/shell/runCromwell.sh
  DEPSTRING=""
  if [[ -n ${WORKFLOW_ZIP:-} ]]; then
      DEPSTRING="-p ${WORKFLOW_ZIP}"
  fi


  JAVA_CMD="${JAVA} \
    -Dbackend.providers.SGE.config.root=${CROMWELL_FOLDER} \
    -Dworkflow-options.workflow-log-dir=${CROMWELL_LOGS} \
    -Dconfig.file=${SGE_CONFIG} \
    -Xmx${JAVA_MEM_MAX} \
    -Xms${JAVA_MEM_INIT} \
    -Xss${JAVA_STACK} \
    -jar ${CROMWELL_JAR} \
    run ${WORKFLOW} \
    ${DEPSTRING} \
    -i ${JSON_INPUT} \
    -o ${JSON_CONFIG} \
    -m ${OUTPUT_JSON} | tee -a ${LOG_FILE} "


  if [[ ! -z ${CROMWELL_H_RT:+x} ]]; then
      RUNFUSION_RT="-l h_rt=${CROMWELL_H_RT}"
  fi

  if [[ ! -z ${CROMWELL_S_RT:+x} ]]; then
      RUNFUSION_ST="-l s_rt=${CROMWELL_S_RT}"
  fi

  QSUB_CMD="${QSUB} \
    -terse -wd \"${LOG_DIR}\" \
    -N "UMIFU_CROMWELL_${SAMPLE_ID}" \
    -q ${QSUB_QUEUE} \
    -l h_vmem=${RUNFUSION_HVMEM} \
    -l h_stack=${RUNFUSION_HSTACK} \
    ${RUNFUSION_RT-} \
    ${RUNFUSION_ST-} \
    ${CROMWELL_QSUB_OPTIONS-} \
    -pe threaded ${RUNFUSION_THREADS} \
    -m a \
    -M ${EMAIL_ADDRESS} \
    ${WDL_QSUB} \
    ${RC_FILE} \
    ${JAVA_CMD}"


  logInfo "Running Command: \n"
  logInfo "${QSUB_CMD}\n"
  set +o errexit
  export SGE_ROOT SGE_CELL SGE_EXECD_PORT SGE_QMASTER_PORT SGE_ROOT SGE_CLUSTER_NAME
  JOB_ID=$(eval "${QSUB_CMD}")
  EXIT_VAL=$?
  set -o errexit
  if [[ ${EXIT_VAL} -ne 0 ]]; then
    logError "QSUB submission failed with error ${EXIT_VAL}, exiting."
    exit 1;
  fi
  logInfo "Submitted cromwell job: ${JOB_ID}"
  echo "${JOB_ID}" > "${LOG_DIR}/cromwell.jobid"


  PP_SCRIPT_OPTIONS="-o ${OUTPUT_DIR} -i ${SAMPLE_DIR} -r \"${RC_FILE}\" ${DEBUG_OPT}"
  POST_CMD="${PP_SCRIPT} ${PP_SCRIPT_OPTIONS}"

  QSUB_ENV_OPTIONS="-v POST_PROCESS_QSUB=${PP_SCRIPT}"

  logInfo "Building post process qsub: ${POST_QSUB}"
  echo "${POST_CMD}" >> "${POST_QSUB}"

  QSUB_CMD="${QSUB} \
    -terse \
    -wd ${LOG_DIR} \
    -N "UMIFU_PP_${SAMPLE_ID}" \
    -q ${QSUB_QUEUE} \
    -l h_vmem=${PP_HVMEM}  \
    -m a -M ${EMAIL_ADDRESS} \
    -hold_jid ${JOB_ID} \
    ${QSUB_ENV_OPTIONS} \
    ${POST_QSUB}"

  logInfo "Running Command: ${QSUB_CMD}\n"

  set +o errexit
  export SGE_ROOT SGE_CELL SGE_EXECD_PORT SGE_QMASTER_PORT SGE_ROOT SGE_CLUSTER_NAME
  JOB_ID=$(eval "${QSUB_CMD}")
  EXIT_VAL=$?
  set -o errexit

  if [[ ${EXIT_VAL} -ne 0 ]]; then
    logError "QSUB PostProcess submission failed with error ${EXIT_VAL}, exiting."
    exit 1;
  fi

  logInfo "Submitted post process job: ${JOB_ID}"
  echo "${JOB_ID}" > "${LOG_DIR}/postprocess.jobid"
  exit ${INF_OK}

fi

if [[ "${CROMWELL_SERVICE}" == "true" ]]; then
    logInfo "Submitting workflow to server"

    # POST /api/workflows/v1
    # workflowDependencies ${WORKFLOW_ZIP}
    # workflowInputs ${JSON_INPUT}
    # workflowOptions ${JSON_CONFIG}
    # workflowSource ${WORKFLOW}
    # workflowType WDL
    # workflowTypeVersion v1.0
    DEPSTRING=""
    if [[ -n ${WORKFLOW_ZIP:-} ]]; then
      DEPSTRING="-F workflowDependencies=@${WORKFLOW_ZIP}"
    fi

    SERVER_CMD="${CURL} -s \
        -X POST http://${CROMWELL_HOST}:${CROMWELL_PORT}/api/workflows/v1 \
        ${DEPSTRING:-} \
        -F workflowInputs=@${JSON_INPUT} \
        -F workflowOptions=@${JSON_CONFIG} \
        -F workflowType=WDL \
        -F workflowSource=@${WORKFLOW} \
        -F workflowTypeVersion=draft-2 \
        -w %{http_code} \
        -o ${OUTPUT_DIR}/logs/curl.json "
    logInfo "${SERVER_CMD}"

    set +o errexit
    result=$( ${CURL} -s \
        -X POST "http://${CROMWELL_HOST}:${CROMWELL_PORT}/api/workflows/v1" \
        ${DEPSTRING:-} \
        -F workflowInputs="@${JSON_INPUT}" \
        -F workflowOptions="@${JSON_CONFIG}" \
        -F workflowType=WDL \
        -F workflowSource="@${WORKFLOW}" \
        -F workflowTypeVersion=draft-2 \
        -w "%{http_code}" \
        -o "${OUTPUT_DIR}/logs/curl.json" )
    EXIT_VAL=$?
    logInfo "Curl returned ${result}"

    if [[ ${EXIT_VAL} -ne 0 ]]; then
      logError "Cromwell Server POST request failed with error ${EXIT_VAL}, exiting."
      exit 1;
    fi

    ## Parse out run_id

    run_ID=$(grep \"id\": ${OUTPUT_DIR}/logs/curl.json |cut -d: -f2 |cut -d, -f1 |tr -d \")
    logInfo "RunID: ${run_ID}"
    echo "${run_ID}" > ${LOG_DIR}/workflow.runID
    set -o errexit

    PP_SCRIPT_OPTIONS="-o ${OUTPUT_DIR} -i ${SAMPLE_DIR} -r \"${RC_FILE}\" -R \"${run_ID}\" ${DEBUG_OPT}"
    POST_CMD="${PP_SCRIPT} ${PP_SCRIPT_OPTIONS}"
    logInfo "Building post process qsub: ${POST_QSUB}"
    echo "${POST_CMD}" >> "${POST_QSUB}"

    QSUB_ENV_OPTIONS="-v POST_PROCESS_QSUB=${PP_SCRIPT}"
    TIME_DELAY="$(date -d "+${umifusionPostHoldDelay} seconds" +%Y%m%d%H%M.%S)"

    ## QSUB MGC Post Process
    # -a date_time value must conform to  [[CC]]YY]MMDDhhmm[.SS],

    QSUB_CMD="${QSUB} \
        -terse \
        -wd ${LOG_DIR} \
        -N "UMIFU_PP_${SAMPLE_ID}" \
         -q ${QSUB_QUEUE} \
         -l h_vmem=${PP_HVMEM} \
         -m a \
         -M ${EMAIL_ADDRESS} \
         -a ${TIME_DELAY} \
         ${QSUB_ENV_OPTIONS} \
         ${POST_QSUB}"

    logInfo "Running Command: \n"
    logInfo "${QSUB_CMD}\n"
    set +o errexit
    export SGE_ROOT SGE_CELL SGE_EXECD_PORT SGE_QMASTER_PORT SGE_ROOT SGE_CLUSTER_NAME
    JOB_ID=$(eval "${QSUB_CMD}")
    EXIT_VAL=$?
    set -o errexit

    if [[ ${EXIT_VAL} -ne 0 ]]; then
      logError "QSUB PostProcess submission failed with error ${EXIT_VAL}, exiting."
      exit 1;
    fi

    logInfo "Submitted post process job: ${JOB_ID}"
    echo "${JOB_ID}" > "${LOG_DIR}/postprocess.jobid"

fi

logInfo "Run script completed successfully."
exit "${INF_OK}"

