task CatFastq {
	Array[File] input_R1_fastq_gz_arr
    Array[File] input_R2_fastq_gz_arr
	String SAMPLE_ID
	String QUEUE
    String MAIL
	String FASTP
	String GUNZIP
	String BGZIP


	command <<<

	for fq in ${sep=' ' input_R1_fastq_gz_arr}
	do
		if [[ $fq == *.gz ]]; then
			cat $fq >> ${SAMPLE_ID}_R1_untrimmed.fastq.gz
			fq=fq.tmp
		fi
	done

	for fq in ${sep=' ' input_R2_fastq_gz_arr}
	do
		if [[ $fq == *.gz ]]; then
			cat $fq >> ${SAMPLE_ID}_R2_untrimmed.fastq.gz
			fq=fq.tmp
		fi
	done

	${GUNZIP} ${SAMPLE_ID}_R1_untrimmed.fastq.gz

	${GUNZIP} ${SAMPLE_ID}_R2_untrimmed.fastq.gz

	${BGZIP} ${SAMPLE_ID}_R1_untrimmed.fastq

	${BGZIP} ${SAMPLE_ID}_R2_untrimmed.fastq

	${FASTP} -i ${SAMPLE_ID}_R1_untrimmed.fastq.gz -I ${SAMPLE_ID}_R2_untrimmed.fastq.gz

	mv fastp.json allread.json

	>>>

	output {
	File R1Combined= "${SAMPLE_ID}_R1_untrimmed.fastq.gz"
	File R2Combined= "${SAMPLE_ID}_R2_untrimmed.fastq.gz"
	File AllReadsJson = "allread.json"
	}
	runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }

}
