#!/bin/bash
PIPELINE_NAME="UMIFUSION"

##################################################
#Default Values
##################################################


LOG_DIR=""
LOG_FILE=""


##################################################
#Usage
##################################################

read -r -d '' DOCS <<DOCS
\n
runFusion.sh usage: $0 options

OPTIONS:
    -h            [optional]  help, Show this message
    -d            [optional]  specifiying this flag enables debug.
    -i <path>     [required]  input directory, full path to a sample-project folder
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
echo "***** Pipeline preprocessing *****"

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
LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log_$$"

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

DEBUG=""
while getopts ":hdi:" OPTION
do
    case ${OPTION} in
        h) logInfo "${DOCS}"; exit ${INF_OK} ;;
        d) set -o xtrace ; DEBUG="-d" ;;
        i) RUN_DIR="$(readlink -m ${OPTARG})" ;;
        \?) logInfo "Invalid option: ${OPTARG}"; exit ${ERR_GENERAL} ;;
        :) logInfo "Missing argument for ${OPTARG}"; exit ${ERR_GENERAL} ;;
        *) logInfo "Unexpected option ${OPTARG}"; exit ${ERR_GENERAL} ;;
    esac
done


##################################################
#VERIFY REQUIRED PARMS
##################################################

validateParm "RUN_DIR" "Please specify a run folder with option: -i"
validateDirectory "${RUN_DIR}"

## Get SampleSheet, Sanity Check

RunSampleSheet=$(find ${RUN_DIR} -maxdepth 1 -mindepth 1 -name "*.SampleSheet.csv")
if [[ ! -s ${RunSampleSheet:-} ]]; then
    logError "No *.SampleSheet.csv found in ${RUN_DIR}. Exiting."
    exit 1
fi

set +o pipefail
HEADER=$(head -n1 ${RunSampleSheet} | grep "^FCID" | wc -l)
HEADERS=$(cat ${RunSampleSheet} |grep "^FCID" |wc -l)
COUNT=$(cat ${RunSampleSheet} | grep -v "^FCID" | wc -l)
SampleID_In_Header=$(cat ${RunSampleSheet} | grep "^FCID" |grep "SampleID" | wc -l)
EMPTY_ROWS=$(cat ${RunSampleSheet} | grep "^$" |wc -l)

set -o pipefail

logInfo "${COUNT} samples appear in sample sheet."

if [[ ${HEADER} -ne 1 ]]; then
    logError "SampleSheet missing header row. Exiting."
    exit 1
fi

if [[ ${HEADERS} -gt 1 ]]; then
    logError "SampleSheet has multiple header rows."
    exit 1
fi

if [[ ${COUNT} -eq 0 ]]; then
    logError "SampleSheet has no samples. Exiting"
    exit 1
fi

if [[ ${SampleID_In_Header} -ne 1 ]]; then
    logError "No column labelled 'SampleID' found in header row."
    exit 1
fi

if [[ ${EMPTY_ROWS} -ne 0 ]]; then
    logError "Sample sheet contained empty rows. Exiting."
    exit 1
fi

LASTCHAR=$(tail -c 1 ${RunSampleSheet} )
if [[ ! -z ${LASTCHAR:-} ]]; then
    logError "SampleSheet ${RunSampleSheet} is missing terminal newline."
    exit 1
fi

SampleID_Column=$(getIndex "${RunSampleSheet}" "SampleID" | tail -1)

SAMPLE_LIST=""
logInfo "Checking presence and pristine state of sample folders."
PASS="TRUE"
for row in $(seq 2 $(( ${COUNT}+1 )) ); do
    my_row=$(head -n ${row} ${RunSampleSheet} | tail -n 1)
    SAMPLE_NAME=$(printf ${my_row} | cut -d, -f ${SampleID_Column})
    logInfo "Examining ${SAMPLE_NAME}"
    if [ ! -d "${RUN_DIR}/samples/${SAMPLE_NAME}" ]; then
        logInfo "Missing sample folder ${RUN_DIR}/samples/${SAMPLE_NAME}"
        PASS="FALSE"
    fi

    if [ -d "${RUN_DIR}/samples/${SAMPLE_NAME}/${PIPELINE_NAME}" ]; then
        logInfo "${PIPELINE_NAME} folder exists in ${SAMPLE_NAME} folder. Move or delete to correct."
        PASS="FALSE"
    fi
done

if [[ "${PASS}" == "FALSE" ]]; then
    exit ${ERR_GENERAL}
fi

logInfo "Tests passed. Launching individual sample executions."
for row in $(seq 2 $(( ${COUNT}+1 )) ); do
    my_row=$(head -n ${row} ${RunSampleSheet} | tail -n 1)
    SAMPLE_NAME=$(printf ${my_row} | cut -d, -f ${SampleID_Column})
    echo "Calling runFusion for ${SAMPLE_NAME}."
    ${SCRIPT_DIR}/runFusion.sh ${DEBUG} -i ${RUN_DIR}/samples/${SAMPLE_NAME}
done





