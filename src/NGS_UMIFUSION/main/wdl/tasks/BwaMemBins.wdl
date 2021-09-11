
task BwaMemBins {

    File input_R1_fastq
    File input_R2_fastq
    String SAMTOOLS
    String PLATFORM
    String CENTER
    String SAMPLE_ID
    String BWA
    String REFERENCE
	String ALIGNMENT_SCRIPT
    String GENELIST
    String bwa_hvmem
    String dollar = "$"
	String ALIGNMENT_ENVPROFILE
	String BASH_PREAMBLE


    String QUEUE
    String MAIL

    command <<<
	set -xeuo pipefail

	source ${BASH_PREAMBLE}
	source ${ALIGNMENT_ENVPROFILE}
	/bin/bash ${ALIGNMENT_SCRIPT} -i ${input_R1_fastq} -f ${input_R2_fastq} -r ${REFERENCE} -s ${SAMPLE_ID} -n COORD -t ${SAMTOOLS} -b ${BWA}
	wait

	mv ${SAMPLE_ID}.bam ${SAMPLE_ID}_genes.bam
	${SAMTOOLS} index ${SAMPLE_ID}_genes.bam

	cat ${GENELIST} | while read line; do  touch ${dollar}{line}_R1.fa;  touch ${dollar}{line}_R2.fa;  touch ${dollar}{line};  echo -e "${dollar}{line}_R1.fa\t${dollar}{line}_R2.fa\t${dollar}{line}\n" >> genefastq.txt; done
    sed -i '/^$/d' genefastq.txt

	touch "metrics.txt"

    >>>

    output {
        File SampleBAMFILE = "${SAMPLE_ID}_genes.bam"
        File SampleBAIFILE = "${SAMPLE_ID}_genes.bam.bai"
		File Read_Metrics = "metrics.txt"
        Array[Array[File]] genefiles = read_tsv("genefastq.txt")
    }

    runtime {
        h_vmem: "${bwa_hvmem}"
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}
