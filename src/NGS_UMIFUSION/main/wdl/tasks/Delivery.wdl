task Deliver
{
    String OutputFolder
    Array[String] FilesToDeliver

    command <<<
        set -xeuo pipefail
        mkdir -p "${OutputFolder}"

        for file in ${sep=' ' FilesToDeliver}; do
            cp -f "$file" "${OutputFolder}/"
            echo ${OutputFolder}/$(basename $file) >> delivery.manifest
        done
    >>>

    output {
        Array[File] delivered_files = read_lines("delivery.manifest")
    }

}

#@metrics. Utility functions. Submit metrics files to ROQCM.
task SubmitMetrics
{
    String ROQCM_API
    Array[File] METRIC_FILES
    command <<<
    set -xeuo pipefail
    for i in ${sep=' ' METRIC_FILES} ; do
        ${ROQCM_API}/submitMetric.sh -i "$i"
    done
    >>>
}