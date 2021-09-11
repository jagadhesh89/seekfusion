# this script aligns the sample fastq files (trimmed) to 'fusion.fa' (whose sequences are from FUSION2VCF)
# produces a custom bam file

task Generate_Custom_Reference {
    File fastq_R1
    File fastq_R2

    String BWA
    String SAMTOOLS

    String SAMPLE_ID
    String PLATFORM
    String CENTER

    String BamName = "${SAMPLE_ID}.bam"

    String ref_fa

    String QUEUE
    String MAIL
	String bwa_hvmem

	File ALIGNMENT_ENVPROFILE
	File ALIGNMENT_SCRIPT
	String SENTIEONTHREADS          # Specifies the number of thread required per run
	File BASH_PREAMBLE               # Bash script that helps control zombie processes
	File BASH_SHARED_FUNCTIONS        # Bash script that contains shared helpful functions

    command <<<

		source ${BASH_PREAMBLE}
		source ${ALIGNMENT_ENVPROFILE}
		/bin/bash ${ALIGNMENT_SCRIPT} -i ${fastq_R1} -f ${fastq_R2} -r ${ref_fa} -s ${SAMPLE_ID} -n COORD -t ${SAMTOOLS} -b ${BWA}
		wait
        ${SAMTOOLS} index ${SAMPLE_ID}.bam

    >>>

    output {
        File ReferenceBAM = "${SAMPLE_ID}.bam"
        File ReferenceBAI = "${SAMPLE_ID}.bam.bai"
    }

    runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
		h_vmem: "${bwa_hvmem}"
    }

}
