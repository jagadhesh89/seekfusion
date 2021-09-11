# this task takes all reads belonging to a partucular gene, assembly them as a contig sequence and then uses blat to search for hits againtst
# a

task BlatFilterAssemblePP {

    String dollar = "$"

    # Tool Settings
    String BLAT
    String BLATFILTER
    String PYTHON
    String LD_LIBRARY_PATH
    String CAP3

    String QUEUE
    String MAIL
    String cap3_hvmem
    String SAMPLE_ID
    String RECIPE
    String GENE
	String ENSSTART # inputs
	String ENSEND # inputs
	String COMMONSEQ #inputs
	String REFGENOME # workflow
	String GENEBED # workflow
	String SParam = SAMPLE_ID + "_"+RECIPE
    String Script  # EachFP.py


    # Inputs
    File R1path
    File R2path
    String mergebins_command_line



    ## Blat Parameters
    Int StepSize
    Int RepMatch
    Int MinScore
    Int MinIdentity
    String BlatOut = "blast8"
    File GenomeFasta

    # BLAT Filter Settings
    File BedFile

    # Contig PostProcess
    String BlatContigPPScript # was BlatContigPostProcess.script (deprecated), now ContigBlatHandler.py
    String ExonCoords
    String ExonStart
    String ExonEnd
    String HGNC
	String SAMTOOLS
	Int UniqueBasesThreshold



    String binName = SAMPLE_ID+"_"+ RECIPE +"_"+ GENE+"_1"
    String pp_outFile=binName+".fa.filtered.blat"
	String outFile = binName + ".fa.filtered.blat"


    command <<<
        set -xeuo pipefail
        export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}



        stderr_log=${binName}.blat_assemble.log
        touch ${dollar}{stderr_log}

        function generateEmptyOutputs {
            touch ${dollar}{stderr_log}
            touch ${binName}.contigs
            touch ${pp_outFile}
        }

        # Merge R1 and R2 Files
        ${PYTHON} ${mergebins_command_line} -r1 ${R1path} -r2 ${R2path} \
            -o $(pwd) -l $(pwd)/${binName}.mergeBins.log -t mergefile.txt \
            2> >(tee ${binName}.mergeR1R2bins.stderr.log >&2)

        InputFile=$(cat mergefile.txt)
		blat_contigs_outname=${dollar}(basename ${dollar}{InputFile} .fa).contigs.blat
		##Remove dups more than N times


        # CAP3 Assembly

        if [[ -s "${binName}.fa" ]]
        then
            ${CAP3} "${binName}.fa" \
                2> >(tee ${dollar}{stderr_log} >&2)
        else
            echo "${binName}.fa is empty." >> ${dollar}{stderr_log}
            generateEmptyOutputs
			touch "${binName}.fa.cap.contigs"
			touch ${pp_outFile}
			touch ${outFile}.final_inframe
			sort ${outFile}.final_inframe | uniq > ${outFile}.final_inframe_unique
			touch ${dollar}{blat_contigs_outname}
            exit 0
        fi

        touch "${binName}.fa.cap.contigs"
        mv "${binName}.fa.cap.contigs" "${binName}.contigs"

        # Blat Contigs
        if [[ -s "${binName}.contigs" ]]; then
            ${BLAT} -stepSize=${StepSize} \
                -repMatch=${RepMatch} \
                -minScore=${MinScore} \
                -minIdentity=${MinIdentity} \
                -out=${BlatOut} \
                ${GenomeFasta} \
                ${binName}.contigs \
                ${dollar}{blat_contigs_outname} \
                2> >(tee ${dollar}{stderr_log} >&2)
        else
            echo ${binName}.contigs was empty after assembly / blat not performed. >> ${dollar}{stderr_log}
            generateEmptyOutputs
			touch "${binName}.fa.cap.contigs"
			touch ${dollar}{blat_contigs_outname}
			touch ${pp_outFile}
			touch ${outFile}.final_inframe
			sort ${outFile}.final_inframe | uniq > ${outFile}.final_inframe_unique
            exit 0
        fi
        touch ${dollar}{blat_contigs_outname}

        # BlatContigPost-process: inclduing filtering results, e.g., remove hits from blat that are not on chromosome 1-22, or X or Y
        ${PYTHON} ${BlatContigPPScript} -i ${dollar}{blat_contigs_outname} -g ${GENEBED} -G ${GENE} -b ${UniqueBasesThreshold} -o ${pp_outFile} \
            2> >(tee ${dollar}{stderr_log} >&2)
        touch ${pp_outFile}



		${PYTHON} ${Script} \
             -i ${pp_outFile} \
             -t ${binName}.contigs \
             -e1 ${ENSSTART} \
             -e2 ${ENSEND} \
             -g ${GENEBED} \
             -s ${SAMTOOLS} \
             -r ${REFGENOME} \
             -S ${SParam} \
             -G ${GENE}_1
         touch ${outFile}.final_inframe

		sort ${outFile}.final_inframe | uniq > ${outFile}.final_inframe_unique
    >>>

    output {
        File inframe = "${outFile}.final_inframe_unique"
    }

    runtime {
        h_vmem: "${cap3_hvmem}"
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}