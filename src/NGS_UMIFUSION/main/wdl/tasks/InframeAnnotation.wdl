task InframeAnnotation {

    String IdentifyAnnotateFusionsScript        # Bash script which is called inside the WDL script
	String PERL #workflow                       #Full path to Perl executable
	String IdentifyAnnotateFusionsThreads       # Specifies the number of thread required per run
	String BashPreamble                           # Bash script that helps control zombie processes
	String BashSharedFunctions                    # Bash script that contains shared helpful functions
	String IdentifyAnnotateFusionsEnvProfile      # File containing the environmental profile variables
	String DebugMode                            # Flag to enable Debug Mode; "-d" or " "
	String STARFORMAT_REPORT_CREATOR
	String REFORMATTER
	String PYTHON #workflow
	File inframeFile
	String SAMPLE_ID
	String SAMPLE_TYPE = "case"
	String MAIL
    String QUEUE
	String ANNOT_STAR_TEMPLATE

    String REFERENCE_GENOME #inputs
    String REFERENCE_DICT # inputs
    String CLINICAL_GENE_LIST_CASE #inputs
    String CLINICAL_GENE_LIST_CONTROL #inputs
    String ALL_GENES_EXON_TRANSCRIPTS # inputs
    String EXON_FEATURES_START_CODON #inputs
    String EXON_FEATURES_STOP_CODON #inputs
    String EXON_START_LIST #inputs
    String EXON_END_LIST #inputs
    String EXON_BODY_LIST #inputs
    String EXON_CDS_FRAME #inputs
    String FALSE_FUSIONS_LIST #inputs
    String PRIORITY_FUSIONS_LIST #inputs
    String COSMIC_FUSIONS #inputs
    String INTRON_LENGTH #inputs
    String SUPPORTING_READS #inputs
    String EXON_PADDING #inputs
    String SCRIPT_PATH # Path to FUSION2VCF perl scripts folder
    String PYTHONSCRIPT_PATH
    String BEDTOOLS # Path to BEDTOOLS 2.26.0

    command <<<
        source ${BashPreamble} # Bash Defaults and Traps
        source ${IdentifyAnnotateFusionsEnvProfile} # Python3 and Perl Settings

		${PYTHON} ${STARFORMAT_REPORT_CREATOR} \
			-i ${inframeFile} \
			-t ${ANNOT_STAR_TEMPLATE} > star_format_inframe.tsv

		## Create Configuration File
		echo "OUT_DIR_NAME=default" > config.txt
        echo "SAMPLE_NAME=${SAMPLE_ID}" >> config.txt
        echo "SAMPLE_TYPE=${SAMPLE_TYPE}" >> config.txt
        echo "SCRIPT_PATH=${SCRIPT_PATH}" >> config.txt
        echo "BEDTOOLS=${BEDTOOLS}" >> config.txt

        echo "REFERENCE_GENOME=${REFERENCE_GENOME}" >> config.txt
        echo "REFERENCE_DICT=${REFERENCE_DICT}" >> config.txt
        echo "CLINICAL_GENE_LIST_CASE=${CLINICAL_GENE_LIST_CASE}" >> config.txt
        echo "CLINICAL_GENE_LIST_CONTROL=${CLINICAL_GENE_LIST_CONTROL}" >> config.txt
        echo "ALL_GENE_LIST=${ALL_GENES_EXON_TRANSCRIPTS}" >> config.txt
        echo "EXON_FEATURES_START_CODON=${EXON_FEATURES_START_CODON}" >> config.txt
        echo "EXON_FEATURES_STOP_CODON=${EXON_FEATURES_STOP_CODON}" >> config.txt
        echo "EXON_START_LIST=${EXON_START_LIST}" >> config.txt
        echo "EXON_END_LIST=${EXON_END_LIST}" >> config.txt
        echo "EXON_BODY_LIST=${EXON_BODY_LIST}" >> config.txt
        echo "EXON_CDS_FRAME=${EXON_CDS_FRAME}" >> config.txt
        echo "FALSE_FUSIONS_LIST=${FALSE_FUSIONS_LIST}" >> config.txt
        echo "COSMIC_FUSIONS=${COSMIC_FUSIONS}" >> config.txt
        echo "PRIORITY_FUSIONS_LIST=${PRIORITY_FUSIONS_LIST}" >> config.txt
        echo "INTRON_LENGTH=${INTRON_LENGTH}" >> config.txt
        echo "SUPPORTING_READS=${SUPPORTING_READS}" >> config.txt
        echo "EXON_PADDING=${EXON_PADDING}" >> config.txt
        echo "PYTHONSCRIPT_PATH=${PYTHONSCRIPT_PATH}" >> config.txt

        perl_path=$(dirname ${PERL})

		/bin/bash ${IdentifyAnnotateFusionsScript} \
		-P "$perl_path"          \
		-i star_format_inframe.tsv         \
		-c config.txt        \
		-t ${IdentifyAnnotateFusionsThreads} \
		-e ${IdentifyAnnotateFusionsEnvProfile} \
		-F ${BashSharedFunctions}   ${DebugMode}

		${PYTHON} ${REFORMATTER} -i default/${SAMPLE_ID}.In-Frame_Fusions.xls > ${SAMPLE_ID}.In-Frame_Fusions.xls
		${PYTHON} ${REFORMATTER} -i default/${SAMPLE_ID}.All_Fusions.xls > ${SAMPLE_ID}.All_Fusions.xls

    >>>

  output {
    File o_inframe = "${SAMPLE_ID}.In-Frame_Fusions.xls"
    File o_allfusions = "${SAMPLE_ID}.All_Fusions.xls"
	File o_default_inframe = "default/${SAMPLE_ID}.In-Frame_Fusions.xls"
	File o_default_all_fusions = "default/${SAMPLE_ID}.All_Fusions.xls"
  }

  runtime {
    cpu: "${IdentifyAnnotateFusionsThreads}"
    sge_queue: "${QUEUE}"
    sge_mail: "${MAIL}"
  }
}
