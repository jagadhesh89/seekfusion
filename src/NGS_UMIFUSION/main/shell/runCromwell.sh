
##################################################
#Usage
##################################################

read -r -d '' DOCS <<DOCS
\n
runCromwell.sh usage: $0 <rcfile> <java_cmd>

This is a wrapper script to set up the memory environment for java and invoke cromwell when submitted
to grid engine.

\n
DOCS


##################################################
#Bash handling
##################################################

set -euo pipefail

RC_FILE=$1
shift

function errhandler()
{
    MYSELF="$0"
    LINE="$1"
    ERRCODE="$2"
    echo "[ERROR] ${MYSELF}: Error ${ERRCODE} caught on line ${LINE}" 1>&2
    echo ${ERRCODE} > ${RC_FILE}
    sync
}

trap 'errhandler ${LINENO} $?' ERR

export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_TRIM_THRESHOLD_=131072
export MALLOC_TOP_PAD_=131072
export MALLOC_MMAP_MAX_=65536

${@}

echo $? > ${RC_FILE}
sync
