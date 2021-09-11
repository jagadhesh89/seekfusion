task DedupFastq {

	Int? ScatterNum
	String PYTHON
    String LD_LIBRARY_PATH
    String SAMPLE_ID
	String DEDUP_BIN
	String DEDUP_ENV_PROFILE
	String BASH_PREAMBLE
	Int? MBCLEN
	String input_R1_fastq
	String input_R2_fastq
	String QUEUE
    String MAIL

	String dollar = "$"

	command <<<
    source ${BASH_PREAMBLE}
	source ${DEDUP_ENV_PROFILE}

	${DEDUP_BIN} -k ${MBCLEN} -t 20 -p "${ScatterNum}" -a _${SAMPLE_ID} "${input_R1_fastq}" "${input_R2_fastq}" -c

	>>>

	output {
        File R1Deduped= "${SAMPLE_ID}_R1_untrimmed.fastq.gz.procNum${ScatterNum}.consensus.fq.gz"
		File R2Deduped= "${SAMPLE_ID}_R2_untrimmed.fastq.gz.procNum${ScatterNum}.consensus.fq.gz"
    }
	runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }

}
