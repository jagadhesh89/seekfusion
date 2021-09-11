#!/bin/bash

# Set any required traps here. Cromwell 0.41+ will catch zombie scripts so trapping SIGUSR1 is superfluous

set -euxo pipefail

# this handles scripts that append to an unset library path
export PATH=${PATH-}
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH-}
export MANPATH=${MANPATH-}

echo PATH="${PATH-}"
echo LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
