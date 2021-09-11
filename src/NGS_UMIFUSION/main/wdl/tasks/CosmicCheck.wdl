task CosmicCheck
{
    String Script #input json / pipeline config
    String PYTHON #workflow / pipeline config
    String LD_LIBRARY_PATH #workflow / pipeline config

    String SAMPLE_ID

    String QUEUE
    String MAIL
    String CC_HVMEM
    String CC_CPU

    File allfusions
    File inframefile
    String CosmicFile

    command <<<
        set -xeuo pipefail

        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
        ${PYTHON} ${Script} \
            -i ${allfusions} \
            -f ${inframefile} \
            -c ${CosmicFile} \
            -o "${SAMPLE_ID}_report.tsv"
    >>>
    output {
        File report = "${SAMPLE_ID}_report.tsv"
    }


    runtime {
            sge_queue: "${QUEUE}"
            sge_mail: "${MAIL}"
            h_vmem: "${CC_HVMEM}"
            cpu: "${CC_CPU}"
    }
}