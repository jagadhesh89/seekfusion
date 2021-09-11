
task BWA_Index {
    File reference  # "reference.fa" --- fusion sequences produced by FUSION2VCF； with BWA index file at the same location

    String BWA
    String SAMTOOLS

    String QUEUE
    String MAIL

    command <<<
    set -euxo pipefail

    mv ${reference} .
    MYREF=$(basename ${reference})
    ${SAMTOOLS} faidx ./$MYREF
    ${BWA} index -6 $MYREF

    echo $MYREF > filename.txt
    >>>

    output {
        File ref_fa = read_string("filename.txt")
        File ref_fai = "${ref_fa}.fai"
        File ref_amb = "${ref_fa}.64.amb"
        File ref_ann = "${ref_fa}.64.ann"
        File ref_pac = "${ref_fa}.64.pac"
        File ref_bwt = "${ref_fa}.64.bwt"
        File ref_sa = "${ref_fa}.64.sa"
    }

    runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}
