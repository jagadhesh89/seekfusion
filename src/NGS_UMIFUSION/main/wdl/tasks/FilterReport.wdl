task Filter_Final_Report {
    String Script #input json / pipeline config
    String PYTHON #workflow / pipeline config
    String LD_LIBRARY_PATH #workflow / pipeline config

    String SAMPLE_ID

    File PreferredTranscripts
    File FinalReport
    File TranscriptVariants

    String QUEUE
    String MAIL

    command <<<
        set -xeuo pipefail

        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
        ${PYTHON} ${Script} \
            -i ${FinalReport} \
            -p ${PreferredTranscripts} \
            -t ${TranscriptVariants} \
            -o "${SAMPLE_ID}_FilteredReport.tsv"
    >>>

    output {
        File FilteredReport = "${SAMPLE_ID}_FilteredReport.tsv"
    }

    runtime {
            sge_queue: "${QUEUE}"
            sge_mail: "${MAIL}"
    }
}
