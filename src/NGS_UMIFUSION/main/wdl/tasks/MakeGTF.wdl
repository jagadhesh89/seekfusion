# this task creates custom gtf and custom reference genenomee (based on fusion sequencers from FUSION2VCF)

task Make_GTF {
    String PYTHON
    String LD_LIBRARY_PATH
    String Script   # igv_vcf.py

    ## The filtered, final inframe tsv
    File FilteredReport

    ## The folowing are references=
    String ControlReference
    String ControlGTF
    String ControlFusions
	String all_frame_file
	String in_frame_file
	String BASESREQ

    File XMLTemplate

    String SAMPLE_ID

    String QUEUE
    String MAIL

    command <<<
    set -exuo pipefail

    export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
    ${PYTHON} ${Script} \
        -i \
        ${FilteredReport} \
        -t \
        ${ControlReference} \
        -g \
        ${ControlGTF} \
        -c \
        ${ControlFusions} \
        -o1 \
        ${SAMPLE_ID}_igv_link_report.tsv \
        -o2 \
        reference.fa \
        -o3 \
        fusion.gtf \
		-a \
		${all_frame_file} \
		-f \
		${in_frame_file} \
		-b \
		${BASESREQ}
        2> >(tee ${SAMPLE_ID}.makegtf.log >&2)


        sed -e 's/FILLERBAM/${SAMPLE_ID}.bam/g' ${XMLTemplate} > igv_session.xml
		sed -i 's/JUNCTIONBAM/${SAMPLE_ID}_junctions.bam/g' igv_session.xml

        ## reference.fa, fusion.gtf go to folder igv_session
    >>>

    output {
        File IGV_Report = "${SAMPLE_ID}_igv_link_report.tsv"
        File ReferenceFasta = "reference.fa"
        File IGV_GTF = "fusion.gtf"
        File logfile = "${SAMPLE_ID}.makegtf.log"
        File IGV_Session = "igv_session.xml"
    }

    runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}
