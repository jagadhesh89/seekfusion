task AggregateInframe {
    Array[File]? inframe

    String SAMPLE_ID

    String QUEUE
    String MAIL

    command <<<
    set -euxo pipefail

    for inframe in ${sep=' ' inframe} ; do
        /bin/cat $inframe >> ${SAMPLE_ID}_Inframe.txt
    done

    >>>

    output {
        File out_inframe = "${SAMPLE_ID}_Inframe.txt"
    }


    runtime {
            sge_queue: "${QUEUE}"
            sge_mail: "${MAIL}"
    }
}