
task Aggregate_dedup {

	Array[File]? R1Deduped
	Array[File]? R2Deduped
	String FASTP

    String SAMPLE_ID

    String QUEUE
    String MAIL

    command <<<
    set -euxo pipefail

    for R1Deduped in ${sep=' ' R1Deduped} ; do
        /bin/cat $R1Deduped >> ${SAMPLE_ID}_deduped_R1.fastq.gz
    done

	for R2Deduped in ${sep=' ' R2Deduped} ; do
        /bin/cat $R2Deduped >> ${SAMPLE_ID}_deduped_R2.fastq.gz
    done

	${FASTP} -i ${SAMPLE_ID}_deduped_R1.fastq.gz -I ${SAMPLE_ID}_deduped_R2.fastq.gz

	mv fastp.json deduped.json

    >>>

    output {
        File R1Fastq = "${SAMPLE_ID}_deduped_R1.fastq.gz"
		File R2Fastq = "${SAMPLE_ID}_deduped_R2.fastq.gz"
		File DedupedJson = "deduped.json"
    }


    runtime {
            sge_queue: "${QUEUE}"
            sge_mail: "${MAIL}"
    }
}
