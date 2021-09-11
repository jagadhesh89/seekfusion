task VCF_Convert {

    String SAMPLE_ID

    String BAMTOBED
    String SAMTOOLS
	String BEDTOOLS
    String VCFSORT
	String BWA
	String vcf_hvmem

    String? VCF_ReadThreshold
    String? VCF_TagThreshold

    String VCF_Script   # FUSION2VCF qiagen_fusion_make_vcf.py
    String IGV_Script   # igv_report.py
	String SPANCHECK_Script # filter_non_spanning.py
	String FF_Script
    String Metric_Script = ""

    File LinkReport
    File FastqR2
    File SampleBam
    File SampleBai
    File VCFHeader
    File GenomeFasta

	String ALIGNMENT_SCRIPT
	String ref_fa
    String tr_fa

    String Padding
    String HighGC
    String LowGC

	String PERL

    String QUEUE
    String MAIL
	String SEQTK

	File ALIGNMENT_ENVPROFILE
	File BASH_PREAMBLE

    command <<<
        source ${BASH_PREAMBLE}
        source ${ALIGNMENT_ENVPROFILE}

        python ${IGV_Script} \
            -i ${LinkReport} \
            -b ${SampleBam} \
            -o "${SAMPLE_ID}_tovcf.tsv" \
            -S ${SAMTOOLS} \
            -B ${BAMTOBED} \
            -m all \
            -t ${VCF_ReadThreshold} \
			-r ${SAMPLE_ID}_readid.txt \
			-R ${ref_fa} \
			-p ${Padding} \
			-u ${HighGC} \
			-l ${LowGC}

		# ${SAMPLE_ID}_readid_uniq.txt: uniq junctions reads IDs that meet certain criteria
        sort ${SAMPLE_ID}_readid.txt | uniq > ${SAMPLE_ID}_readid_uniq.txt

		${BEDTOOLS}/bamToFastq -i ${SampleBam} -fq allreads.fq

		# subset fastq to get only reads with the given read ids
        ${SEQTK} subseq allreads.fq ${SAMPLE_ID}_readid_uniq.txt > junctionreads.fastq

		# align junction fastq to transcriptom and index the resultant bam
        /bin/bash ${ALIGNMENT_SCRIPT} -i junctionreads.fastq -r ${tr_fa} -s ${SAMPLE_ID}np -n COORD -t ${SAMTOOLS} -b ${BWA}
		wait
		${SAMTOOLS} index ${SAMPLE_ID}np_junctions.bam

		# cigar string containing "S" means soft-clipping and non-perfect match;
        ${SAMTOOLS} view ${SAMPLE_ID}np_junctions.bam | ${PERL} -ne '@v = split; print if $v[5] =~ /S/ || !/NM:i:0/' > nonperfect.sam
		${SAMTOOLS} view -H ${SAMPLE_ID}np_junctions.bam > nonperfect_header.txt
		cat nonperfect_header.txt nonperfect.sam > nonperfect_reads.sam
		${SAMTOOLS} view -b nonperfect_reads.sam > nonperfect.bam

		${SAMTOOLS} sort -o nonperfect_sorted.bam nonperfect.bam
		${SAMTOOLS} index nonperfect_sorted.bam

		${BEDTOOLS}/bamToFastq -i nonperfect_sorted.bam -fq non_perfect_reads.fq
		${SEQTK} subseq non_perfect_reads.fq ${SAMPLE_ID}_readid_uniq.txt > break_span_reads.fq

		# mapping to custeom reference fasta using non-perfect reads
        /bin/bash ${ALIGNMENT_SCRIPT} -i break_span_reads.fq -r ${ref_fa} -s ${SAMPLE_ID} -n COORD -t ${SAMTOOLS} -b ${BWA}
		wait

		${SAMTOOLS} index ${SAMPLE_ID}_junctions.bam

		mv ${SAMPLE_ID}_junctions.bam ${SAMPLE_ID}_junctions_pair_not_spanning.bam
		mv ${SAMPLE_ID}_junctions.bam.bai ${SAMPLE_ID}_junctions_pair_not_spanning.bam.bai

		# only keep mapped reads (-F 4: excluding unmapped reads)
        ${SAMTOOLS} view -F 4 ${SAMPLE_ID}_junctions_pair_not_spanning.bam > mapped_reads.sam
		${SAMTOOLS} view -H ${SAMPLE_ID}_junctions_pair_not_spanning.bam > mapped_reads_header.txt

		python ${SPANCHECK_Script} \
			-i mapped_reads.sam \
			-o spanning_reads.sam \
			-p ${Padding}

		cat mapped_reads_header.txt spanning_reads.sam > ${SAMPLE_ID}_junctions.sam
		${SAMTOOLS} view -b ${SAMPLE_ID}_junctions.sam > ${SAMPLE_ID}_junctions.bam
		${SAMTOOLS} index ${SAMPLE_ID}_junctions.bam

        # the only differene of this command is the input bam file. Here uses the bam generated from non_perfect_reads.fq
        python ${IGV_Script} \
            -i ${SAMPLE_ID}_tovcf.tsv \
            -b ${SAMPLE_ID}_junctions.bam \
            -o "${SAMPLE_ID}_junctiontovcf.tsv" \
            -S ${SAMTOOLS} \
            -B ${BAMTOBED} \
            -r ${SAMPLE_ID}_readid.txt \
            -R ${ref_fa} \
            -p ${Padding} \
            -u ${HighGC} \
            -l ${LowGC} \
            -m junc \
            -t ${VCF_ReadThreshold}



        # script from FUSION2VCF module
        python ${VCF_Script} \
            -i "${SAMPLE_ID}_junctiontovcf.tsv" \
            -o "${SAMPLE_ID}.vcf" \
            -v ${VCFHeader} \
            -r ${GenomeFasta} \
            -V ${VCFSORT} \
            -S ${SAMTOOLS} \
            -t ${default="1" VCF_ReadThreshold} \
            -g ${default="1" VCF_TagThreshold} \
            -s "UMIFUSION"

		mv ${SAMPLE_ID}.vcf ${SAMPLE_ID}_noFF.vcf

		python ${FF_Script} \
			-i "${SAMPLE_ID}_noFF.vcf" \
			-j "${SAMPLE_ID}_junctions.bam" \
			-b ${SampleBam} \
			-s ${SAMTOOLS} \
			-o ${SAMPLE_ID}.vcf \
			-w ${Padding}


    >>>

    output {
        File tovcf = "${SAMPLE_ID}_tovcf.tsv"
		File junctiontovcf = "${SAMPLE_ID}_junctiontovcf.tsv"
        File vcf = "${SAMPLE_ID}.vcf"
		File juncbam = "${SAMPLE_ID}_junctions.bam"
		File juncbai = "${SAMPLE_ID}_junctions.bam.bai"
    }

    runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
		h_vmem: "${vcf_hvmem}"
    }
}
