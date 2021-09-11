#!/bin/bash

##################################################
#Default Values
##################################################

LOG_DIR=""
LOG_FILE=""
PIPELINE_NAME="UMIFUSION"


##################################################
#Usage
##################################################

read -r -d '' DOCS <<DOCS
\n
runFusion.sh usage: $0 options

OPTIONS:
    -h            [optional]  help, Show this message
    -d            [optional]  specifiying this flag enables debug.
    -i <file>     [required]  json file of the results to store in the run
    -o <dir>      [required]  output directory to store the files
    -R <run_id>   [optional]  run_id (if querying server for completion otherwise outputs.json is used)
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
if [[ ! -z "${POST_PROCESS_QSUB+x}" ]]; then
    SCRIPT="${POST_PROCESS_QSUB}"
fi

SCRIPT_DIR=$(dirname ${SCRIPT})
SCRIPT_NAME=$(basename ${SCRIPT})

# Using the hopefully real at this point script home to find the pipeline profile

_FIND_PATH=${SCRIPT_DIR}
while [[ ${_FIND_PATH} != "$(dirname ${_FIND_PATH})" && ! -f "${_FIND_RESULT:-}" ]];
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


MONITOR_WAIT=${umifusionMonitorWait:-1800} # default wait time between server polls
MONITOR_TIMEOUT=${umifusionMonitorTimeout:-345600} # default timeout (4 days)

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

while getopts ":hdi:o:r:R:" OPTION
do
    case $OPTION in
        h) logInfo "${DOCS}"; exit ${INF_OK} ;;
        d) set -o xtrace ;;
        o) OUTPUT_DIR="$(readlink -m ${OPTARG})" ;;
        i) SAMPLE_DIR="$(readlink -m ${OPTARG})" ;;
        r) RC_FILE="$(readlink -m ${OPTARG})" ;;
        R) RUN_ID="${OPTARG}" ;;
        \?) logInfo "Invalid option: ${OPTARG}"; exit ${ERR_GENERAL} ;;
        :) logInfo "Missing argument for ${OPTARG}"; exit ${ERR_GENERAL} ;;
        *) logInfo "Unexpected option ${OPTARG}"; exit ${ERR_GENERAL} ;;
    esac
done


##################################################
#VERIFY REQUIRED PARMS
##################################################

validateParm "OUTPUT_DIR" "Please specify a destination with option: -o"
validateDirectory "${OUTPUT_DIR}"

validateParm "SAMPLE_DIR" "Please specify a sample dir with option: -i"
validateDirectory "${SAMPLE_DIR}"

mkdir -p "${OUTPUT_DIR}/reports"
PIPELINE_RESULTS="${OUTPUT_DIR}/reports/pipeline_results.txt"


##################################################
#VARIABLE DEFINITIONS & DIRECTORY SETUP
##################################################

SAMPLE_SHEET="${SAMPLE_DIR}/SampleSheet.csv"
validateFile "${SAMPLE_SHEET}"

CONFIG_DIR="${OUTPUT_DIR}/configs"
LOG_DIR="${OUTPUT_DIR}/logs"
REPORTS_DIR="${OUTPUT_DIR}/reports"


LOG_FILE="${LOG_DIR}/main.log"

OUTPUT_JSON="${CONFIG_DIR}/outputs.json"
TIMING_RESULT="${LOG_DIR}/timings.html"         # Location for intermediate timings data
TIMINGS_DIR="${OUTPUT_DIR}/reports"             # Final timing result will be moved here

CONFIG_DIR="${OUTPUT_DIR}/configs"
JSON_INPUT="${CONFIG_DIR}/inputs.json"


OS_DIR="${SAMPLE_DIR}/ordered_service"
OS_CONFIG="${OS_DIR}/os.cfg"
OS_PIPELINE_DIR="${OS_DIR}/pipelines/${PIPELINE_NAME,,}"
PIPELINE_MAIN_INFO="${OS_PIPELINE_DIR}/main.info"


logInfo "Command run: $(basename $0) $*"

logInfo "***** Post execution validation*****"

function createPipelineResults
{
    local _piperesults=${1}
    local _state=${2}
    local _message=${3}

    local _date=`date '+%Y-%m-%dT%H:%M:%S'`

    printf "%s\t%s\t%s\n" "#TIME" "STATE" "COMMENT" > ${_piperesults}
    printf "%s\t%s\t" "${_date}" "${_state}" >> ${_piperesults}
    printf "${_message}\n" >> ${_piperesults}

}

# usage: check_status()
# runID, CROMWELL_HOST, CROMWELL_PORT must be set
# http response code will be in _result
# status will be in _status
# file will be created in OUTPUT_DIR/logs/monitor_result.json.PID

function check_status()
{

    # Status of Workflow
    #  curl -X GET \
    #  "http://dlmpcim02.mayo.edu:8091/api/workflows/v1/04494039-889f-4847-858f-7b29b0ca4195/status" \
    #  -H "accept: application/json" -o result.json
    #
    # Results
    # 200 / 404 (Not Found) / 400,500 malformed or internal error
    #
    #{
    #  "id": "e442e52a-9de1-47f0-8b4f-e6e565008cf1",
    #  "status": "Submitted" # "Running", "Aborting", "Aborted", "Succeeded" ...
    #}

    _monitor_result="${OUTPUT_DIR}/logs/monitor_result.json.$$"
    set +o errexit
    _result=$( ${CURL} -s \
        -X GET "http://${CROMWELL_HOST}:${CROMWELL_PORT}/api/workflows/v1/${RUN_ID}/status" \
        -w "%{http_code}" \
        -o "${_monitor_result}" )
    set -o errexit
    logInfo "Curl returned ${_result}"

    _status="Unknown"
    if [[ "${_result}" == "200" ]]; then
        _status=$(grep \"status\": ${OUTPUT_DIR}/logs/monitor_result.json.$$ |cut -d: -f2 |cut -d, -f1 |tr -d \")
        logInfo "Run Status: ${_status}"
    fi

    if [[ ! "${DEBUG_OPT:-}" == "-d" ]]; then
        rm -f "${_monitor_result}"
    fi
}

function fetch_timings
{

  # http://dlmpcim04.mayo.edu:8092/api/workflows/v1/204c2715-ee72-4f7b-a945-687de7a44bb7/timing

  set +o errexit
  _result=$( ${CURL} -s \
        -X GET "http://${CROMWELL_HOST}:${CROMWELL_PORT}/api/workflows/v1/${RUN_ID}/timing" \
        -w "%{http_code}" \
        -o "${TIMING_RESULT}" )
  set -o errexit
  logInfo "Curl returned ${_result}."

  if [[ "${_result}" == "200" ]]; then
        logInfo "Timings sent to ${TIMING_RESULT}"
  fi

}

function fetch_json()
{
    #GET /api/workflows/version/id/outputs
    json_result="${OUTPUT_JSON}".tmp
    set +o errexit
    _result=$( ${CURL} -s \
        -X GET "http://${CROMWELL_HOST}:${CROMWELL_PORT}/api/workflows/v1/${RUN_ID}/outputs" \
        -w "%{http_code}" \
        -o "${json_result}" )
    set -o errexit
    logInfo "Curl returned ${_result} on output API query"

    if [[ "${_result}" != "200" ]]; then
        logInfo "Retrieving output json failed with http code ${_result}."
        rm "${json_result}"
    else
        mv "${json_result}" "${OUTPUT_JSON}"
    fi
}

EXIT_CODE=1 # Assume failure


## If we have not been given a run ID, and OUTPUT_JSON is missing, cromwell aborted

OUTPUT_JSON="${CONFIG_DIR}/outputs.json"

# this only becomes true if we enter a wait loop and
# the wait loop exits without resetting it due to a succesful completion
waited_too_long="false"



if [[ ! -n ${RUN_ID-} && -n ${RC_FILE-} && ! -f ${RC_FILE} ]]; then
    # Not server mode, RC file check requested, but file missing
    createPipelineResults ${PIPELINE_RESULTS} FAILED "Cromwell exited prematurely."
    exit 1
fi

if [[ ! -n ${RUN_ID-} && -n ${RC_FILE-} ]]; then
    # Not Server Mode, RC_FILE exists
    EXIT_CODE=$(cat "${RC_FILE}")
elif [[ ! -n ${RUN_ID-} ]]; then # manual invocation (just run secondary tasks)
    EXIT_CODE=NA
else # Sever Mode
    echo "Querying server periodically for status of run ${RUN_ID}."
    ## Set exit code here based on polling
    waited_too_long="true"
    while ((${SECONDS} < ${MONITOR_TIMEOUT}))
    do
        check_status
        echo Check status returned code ${_result}, status ${_status}
        if [[ "${_status}" == "Succeeded" ]]; then
            logInfo "Cromwell indicates successful pipeline completion."
            logInfo "Recovering json outputs"
            fetch_json
            EXIT_CODE=0
            echo ${EXIT_CODE} > "${RC_FILE}"
            waited_too_long="false"
            fetch_timings # update timings one last time
            break
        fi

        if [[ "${_status}" =~ "Abort" ]]; then
            logError "Detected parent job ${RUN_ID} was manually aborted."
            logError "Post-process self-terminates."
            exit 1
        fi

        if [[ "${_status}" != "Running" && "${_status}" != "Submitted" && "${_status}" != "Unknown" ]]; then
            logInfo "Cromwell returned ${_status}. Post-process treating this as run failure."
            EXIT_CODE=1
            echo ${EXIT_CODE} > "${RC_FILE}"
            waited_too_long="false"
            break
        fi

        ### fetch timings for running job
        logInfo "Updating timings for running job."
        fetch_timings

        echo "Sleeping ${MONITOR_WAIT} seconds."
        sleep ${MONITOR_WAIT}
    done

    if [[ -f ${TIMING_RESULT} ]]; then
      logInfo "Moving ${TIMING_RESULT} to ${TIMINGS_DIR}"
      mkdir -p "${TIMINGS_DIR}"
      mv "${TIMING_RESULT}" "${TIMINGS_DIR}"
    fi
fi


if [[ "${waited_too_long}" == "true" ]]; then
    logError "${SCRIPT_NAME} timed out after exceeding ${MONITOR_TIMEOUT} seconds, exiting."
    logError "Last cromwell HTTP result code was ${_result}."
    logError "Last status of ${RUN_ID} was ${_status}."
    logError "PostProcess will not be run automatically."
    logError "Invoke postProcess.sh manually once the pipeline completes or has been aborted."
    exit 1
fi

# Fail if cromwell reports an error, if NA we were run manually and should just run delivery
if [[ ! "${EXIT_CODE}" == "NA" && ! "${EXIT_CODE}" == "0" ]]; then
    logError "Cromwell reported a pipeline failure (${EXIT_CODE})."
    createPipelineResults "${PIPELINE_RESULTS}" FAILED "Cromwell returned non-zero exit code ${EXIT_CODE}."
    if [[ ! -z ${DELIVERY_DISPATCH-} ]]; then
        logError "Calling \${DELIVERY_DISPATCH} as failure"
        ${DELIVERY_DISPATCH} -s "${SAMPLE_SHEET}" -f
    fi
    exit 1
fi


# At this point we should have an OUTPUT_JSON or we exited above

SAMPLE_NAME=$(basename $(dirname ${OUTPUT_DIR}))

##################################################
#NOTIFICATION
##################################################

logInfo "$(cat <<EOM
Pipeline Run Details

******************* DETAILS *********************

SAMPLE_NAME:            ${SAMPLE_NAME}

** SCRIPT DATA **
SCRIPT_HOME:            ${SCRIPT_HOME}
SOURCE_HOME:            ${SOURCE_HOME}
TOOLS_HOME:             ${TOOLS_HOME}
CONFIGS_HOME:           ${CONFIGS_HOME}
REFERENCES:             ${REFERENCES}
TEMP_LOG_SPACE:         ${TEMP_LOG_SPACE}

** WDL DATA **
JSON_INPUT:             ${JSON_INPUT}
OUTPUT_JSON:            ${OUTPUT_JSON}

** RESULTS **
OUTPUT_DIR:             ${OUTPUT_DIR}
CONFIG_DIR:             ${CONFIG_DIR}

************************************************\n
EOM
)"

if [[ ! -f "${PIPELINE_RESULTS}" ]]; then
  createPipelineResults "${PIPELINE_RESULTS}" "COMPLETED" "UMIFusion run successful."
  if [[ ! -z ${DELIVERY_DISPATCH+x} ]]; then
      echo Calling "${DELIVERY_DISPATCH}" as success.
      ${DELIVERY_DISPATCH} -s "${SAMPLE_SHEET}"
  fi
fi

exit ${INF_OK}
