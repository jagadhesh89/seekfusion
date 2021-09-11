task SplitBamToGene {

    File DupRemoved_BAM
    File DupRemoved_BAI
    String GENE
    String SAMTOOLS
	String BEDTOOLS
    String RECIPE
    String SAMPLE_ID
	String RUN_NAME
	String BATCH_NAME
    String QUEUE
    String MAIL
    String dollar = "$"
	String Downsample
	String PYTHON
    String LD_LIBRARY_PATH
	String RemoveDups
	Int AllowedDups
	String SEQTK
	String REFERENCE
	String ALIGNMENT_SCRIPT
	String BWA
	String ALIGNMENT_ENVPROFILE
	String BASH_PREAMBLE
    String bwa_hvmem

	#bash tools
	String CUT
	String ECHO
	String HEAD
	String MV
	String PASTE
	String SED
	String SORT
	String TOUCH
	String TR
	String UNIQ
	String WC
	String CAT

    command <<<
		set -xeuo pipefail
        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}

		GENE_READS=`${SAMTOOLS} view ${DupRemoved_BAM} ${GENE} | ${CUT} -f1 | ${SORT} | ${UNIQ} | ${WC} -l`

		echo -e "UMIFUSION\tsample.primer_${GENE}_reads.count\tI\t$GENE_READS\t${SAMPLE_ID}_${RECIPE}\tsample\t${BATCH_NAME}\tBatch\t${RUN_NAME}\trun\n" > ${GENE}_metric.txt

		if [[ "$GENE_READS" -gt "${Downsample}" ]]; then
			# downsample bam if reads > N number of reads, sort and index

			${SAMTOOLS} view -b ${DupRemoved_BAM} ${GENE} > ${GENE}_req.bam
			${SAMTOOLS} view -c ${GENE}_req.bam > count.txt
			${BEDTOOLS}/bamToFastq -i ${GENE}_req.bam -fq ${GENE}_req.fq
			${SEQTK} sample -s100 ${GENE}_req.fq ${Downsample} > ${GENE}_subsampled.fastq

			source ${BASH_PREAMBLE}
			source ${ALIGNMENT_ENVPROFILE}
			/bin/bash ${ALIGNMENT_SCRIPT} -i ${GENE}_subsampled.fastq -r ${REFERENCE} -s ${SAMPLE_ID} -n COORD -t ${SAMTOOLS} -b ${BWA}
			wait

			${MV} ${SAMPLE_ID}_junctions.bam ${GENE}_sorted_nondeduped.bam
			${SAMTOOLS} index ${GENE}_sorted_nondeduped.bam

		else
			#sort and index bam
			${SAMTOOLS} view -bS ${DupRemoved_BAM} ${GENE} > ${GENE}_sorted_nondeduped.bam
			${SAMTOOLS} index ${GENE}_sorted_nondeduped.bam
			${SAMTOOLS} view -c ${GENE}_sorted_nondeduped.bam > count.txt
		fi

		#Convert bam to sam for python processing
		${SAMTOOLS} view ${GENE}_sorted_nondeduped.bam > nondeduped_alignments.sam
		${SAMTOOLS} view -H ${GENE}_sorted_nondeduped.bam > header.txt

		#Remove dups
		${PYTHON} ${RemoveDups} -i nondeduped_alignments.sam -o deduped_alignments.sam -n ${AllowedDups}

		#Combine header and deduped sam, convert to bam, sort and index
		${CAT} header.txt deduped_alignments.sam > alignments.sam
		${SAMTOOLS} view -bS alignments.sam > alignments.bam
		${SAMTOOLS} sort -o ${GENE}.bam alignments.bam
		${SAMTOOLS} index ${GENE}.bam

		#Convert bam to fasta for assembly
		${SAMTOOLS} view -b ${GENE}.bam ${GENE} | ${SAMTOOLS} bam2fq - | ${PASTE} - - - -  | ${CUT} -f 1,2 | ${SED} 's/^@/>/' | ${TR} "\t" "\n" > ${SAMPLE_ID}_${RECIPE}_${GENE}_1_R1.fa
		${TOUCH} ${SAMPLE_ID}_${RECIPE}_${GENE}_1_R2.fa


        count=$(head -n 1 ${SAMPLE_ID}_${RECIPE}_${GENE}_1_R1.fa)
        ${HEAD} -n 10 ${SAMPLE_ID}_${RECIPE}_${GENE}_1_R1.fa | wc -l > count.txt

        if [[ $count == "0" ]]; then
            ${ECHO} -e "No reads binned -- exiting."
            exit 1
        fi

        exit 0
    >>>

    output {
        Int count = read_int("count.txt")
        File R1_Bin = "${SAMPLE_ID}_${RECIPE}_${GENE}_1_R1.fa"
        File R2_Bin = "${SAMPLE_ID}_${RECIPE}_${GENE}_1_R2.fa"
		File GeneMetric = "${GENE}_metric.txt"
    }

    runtime {
    sge_queue: "${QUEUE}"
    sge_mail: "${MAIL}"
	h_vmem: "${bwa_hvmem}"
  }

}
