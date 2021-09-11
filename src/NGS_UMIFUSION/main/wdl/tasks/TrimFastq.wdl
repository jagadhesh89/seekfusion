
task TrimFastq {
	String LD_LIBRARY_PATH
	String PYTHON
    String R1Fastq
	String R2Fastq
    String SAMPLE_ID
    String GUNZIP
    String CAT

    String QUEUE
    String MAIL
	String FASTP
	String ADAPTER_FILE
	String trim_hvmem

    command <<<
        set -euxo pipefail
		export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}

		${FASTP} -i ${R1Fastq} -I ${R2Fastq} -o ${SAMPLE_ID}_R1.fastq.gz -O ${SAMPLE_ID}_R2.fastq.gz --adapter_fasta ${ADAPTER_FILE}
		mv fastp.json trimmed.json

        >>>

    output {
        File output_R1_fastq = "${SAMPLE_ID}_R1.fastq.gz"
        File output_R2_fastq = "${SAMPLE_ID}_R2.fastq.gz"
		File TrimmedJson = "trimmed.json"
    }

    runtime {
		h_vmem: "${trim_hvmem}"
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}
