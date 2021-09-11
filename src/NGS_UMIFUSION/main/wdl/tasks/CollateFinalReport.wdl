task Collate_Final_Report
{
    File inframe_report
    String SAMPLE_ID

    String dollar = "$"

    String QUEUE
    String MAIL

    command <<<
        set -xeuo pipefail

        set +e
        cat ${inframe_report} | grep -v "BLACKLIST" > "${SAMPLE_ID}_FinalReport.tsv"
        set -e

    >>>

    output {
        File FinalReport = "${SAMPLE_ID}_FinalReport.tsv"
    }


    runtime {
            sge_queue: "${QUEUE}"
            sge_mail: "${MAIL}"
    }
}