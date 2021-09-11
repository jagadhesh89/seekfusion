#!/bin/bash
set -x

read -r -d '' DOCS <<DOCS
usage: $0 options

# This script acts as a wrapper for the sentieon bwa.
## @input param -i <R1.fastq> (Required parameter).
## @input param -f <R2.fastq> (Required parameter).
## @input param -r <REFERENCE> (Required parameter).
## @input param -s <SAMPLEID> (Required parameter).
## @input param -n <SORTMODE>, sorting mode of bam file by coordinate or read ID, values: COORD/NAME
## @input param -t <SAMTOOLS PATH>
## @input param -b <BWA mem>
#
DOCS


while getopts "hi:f:r:s:n:t:b:" OPTION
do
	case $OPTION in
		h) echo "${DOCS}" ; exit ;;
		i) declare -r R1File=`readlink -f "$OPTARG"` ;;
		f) declare -r R2File=`readlink -f "$OPTARG"` ;;
		r) declare -r REFERENCE=`readlink -f "$OPTARG"` ;;
		s) declare -r SampleName=`readlink -f "$OPTARG"` ;;
		n) declare -r SortFlag="$OPTARG" ;;
		t) declare -r SAMTOOLS="$OPTARG" ;;
		b) declare -r BWAMEM="$OPTARG" ;;
		?) usage ; exit ;;
	esac
done

if [[ -n "${R2File}" ]]; then
	echo "Using $R1File $R2File and $REFERENCE for $SampleName $LaneName"

    ${BWAMEM} mem -R "@RG\tID:${SampleName}\tPU:ILLUMINA\tSM:${SampleName}\tPL:ILLUMINA\tLB:LIB\tCN:CGSL" -K 10000000 -t 32 ${REFERENCE} ${R1File} ${R2File} | ${SAMTOOLS} view -bS > ${SampleName}_unsorted.bam

	if [[ "${SortFlag}" = "NAME" ]]; then
		${SAMTOOLS} sort -n -o ${SampleName}.bam ${SampleName}_unsorted.bam
	else
		${SAMTOOLS} sort -o ${SampleName}.bam ${SampleName}_unsorted.bam
	fi

else
	${BWAMEM} mem -R "@RG\tID:${SampleName}\tPU:ILLUMINA\tSM:${SampleName}\tPL:ILLUMINA\tLB:LIB\tCN:CGSL" -K 10000000 -t 32 ${REFERENCE} ${R1File} | ${SAMTOOLS} view -bS > ${SampleName}_junctions_unsorted.bam
	${SAMTOOLS} sort -o ${SampleName}_junctions.bam ${SampleName}_junctions_unsorted.bam

fi