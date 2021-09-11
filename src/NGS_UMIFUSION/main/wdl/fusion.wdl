import "NGS_UMIFUSION/main/wdl/tasks/BwaMemBins.wdl" as BWAMEMBINS
import "NGS_UMIFUSION/main/wdl/tasks/SplitBamToGene.wdl" as SPLITBAM
import "NGS_UMIFUSION/main/wdl/tasks/BlatFilterAssemble.wdl" as BLAT
import "NGS_UMIFUSION/main/wdl/tasks/AggregateInframe.wdl" as AGGREGATEINFRAME
import "NGS_UMIFUSION/main/wdl/tasks/CosmicCheck.wdl" as COSMIC
import "NGS_UMIFUSION/main/wdl/tasks/ControlMetrics.wdl" as CONTROLMETRICS
import "NGS_UMIFUSION/main/wdl/tasks/FilterReport.wdl" as FILTERREPORT
import "NGS_UMIFUSION/main/wdl/tasks/InframeAnnotation.wdl" as INFRAME
import "NGS_UMIFUSION/main/wdl/tasks/MakeGTF.wdl" as MAKEGTF
import "NGS_UMIFUSION/main/wdl/tasks/BWAIndex.wdl" as BWAINDEX
import "NGS_UMIFUSION/main/wdl/tasks/CustomRef.wdl" as CUSTOMREF
import "NGS_UMIFUSION/main/wdl/tasks/VCFConvert.wdl" as VCFCONVERT
import "NGS_UMIFUSION/main/wdl/tasks/CatFastq.wdl" as CATFASTQ
import "NGS_UMIFUSION/main/wdl/tasks/DedupFastq.wdl" as DEDUPFASTQ
import "NGS_UMIFUSION/main/wdl/tasks/GeneMetric.wdl" as GENEMETRIC
import "NGS_UMIFUSION/main/wdl/tasks/AggDedup.wdl" as AGGDEDUP
import "NGS_UMIFUSION/main/wdl/tasks/TrimFastq.wdl" as TRIMFQ
import "NGS_UMIFUSION/main/wdl/tasks/Delivery.wdl" as DELIVERY

workflow UMIFUSION {
    String OUTPUT_DIR
    String QUEUE
    String MAIL
	Array[Int] scatter_range = [1, 2, 3, 4, 5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
    String CAP3
    String PYTHON
    String LD_LIBRARY_PATH
    String MERGEBINS
    String BLATFILTER
    String BLAT
    String SAMTOOLS
    String BEDTOOLS
    String PERL
    String GUNZIP
	String BGZIP
    String CAT
    String BWA
    String VCFSORT

    String BAMTOBED = "${BEDTOOLS}/bamToBed"

    String ref_primers

    String SAMPLE_ID
    String RECIPE
    String RUN_NAME
    String SAMPLE_PROJECT
    String BATCH_NAME
    String SAMPLE_TYPE # "case" or "control"
    String PLATFORM
    String CENTER
    File GENELIST
	String FASTP
    String REFERENCE
    String TRANSCRIPT_REFERENCE
    String JAVA
	String SEQTK
	
	File ALIGNMENT_ENVPROFILE
	File ALIGNMENT_SCRIPT


	String SENTIEON                 # Path to Sentieon
	String SENTIEONTHREADS          # Specifies the number of thread required per run
	File BASH_PREAMBLE               # Bash script that helps control zombie processes
	File BASH_SHARED_FUNCTIONS        # Bash script that contains shared helpful functions
	String ALIGN_CHUNK_SIZE_BASES         # The -K option for BWA MEM
	String BWA_EXTRA_OPTIONS  

    # File SampleSheet

    Array[File] sample_R1_fastq_gz_arr
    Array[File] sample_R2_fastq_gz_arr
    File panel_bed

    File GenomeFasta

    Boolean UMIDedup

	call CATFASTQ.CatFastq as CatFastq {
		input: 
			input_R1_fastq_gz_arr = sample_R1_fastq_gz_arr,
			input_R2_fastq_gz_arr=sample_R2_fastq_gz_arr,
			MAIL=MAIL,
			QUEUE=QUEUE,
			FASTP = FASTP,
			GUNZIP = GUNZIP,
			BGZIP = BGZIP,
			SAMPLE_ID=SAMPLE_ID
	}

	if (UMIDedup) {
        scatter(i in scatter_range)
        {
          call DEDUPFASTQ.DedupFastq as DedupFastq {
            input:
                PYTHON = PYTHON,
                LD_LIBRARY_PATH = LD_LIBRARY_PATH,
                SAMPLE_ID = SAMPLE_ID,
                input_R1_fastq = CatFastq.R1Combined,
                input_R2_fastq = CatFastq.R2Combined,
                ScatterNum = i,
                MAIL=MAIL,
                QUEUE=QUEUE
                }
        }

        call AGGDEDUP.Aggregate_dedup as Aggregate_dedup {
            input:
                SAMPLE_ID = SAMPLE_ID,
                R1Deduped = DedupFastq.R1Deduped,
                R2Deduped = DedupFastq.R2Deduped,
                QUEUE = QUEUE,
                FASTP = FASTP,
                MAIL = MAIL
        }
    } # if UMIDedup is true

    File R1Fastq = select_first([Aggregate_dedup.R1Fastq, CatFastq.R1Combined])
    File R2Fastq = select_first([Aggregate_dedup.R2Fastq, CatFastq.R2Combined])


    call TRIMFQ.TrimFastq as TrimFastq {
        input:
			PYTHON = PYTHON,
			LD_LIBRARY_PATH = LD_LIBRARY_PATH,
            SAMPLE_ID = SAMPLE_ID,
            QUEUE=QUEUE,
			FASTP = FASTP,
            R1Fastq = R1Fastq,
            R2Fastq = R2Fastq,
            GUNZIP=GUNZIP,
            CAT=CAT,
            MAIL=MAIL
    }
	
	File sample_R1_fastq = TrimFastq.output_R1_fastq
    File sample_R2_fastq = TrimFastq.output_R2_fastq
	
	call BWAMEMBINS.BwaMemBins as BwaMemBins {
        input:
            input_R1_fastq = sample_R1_fastq,
            input_R2_fastq = sample_R2_fastq,
            SAMTOOLS = SAMTOOLS,
            PLATFORM = PLATFORM,
            CENTER = CENTER,
            SAMPLE_ID = SAMPLE_ID,
            BWA = BWA,
            QUEUE = QUEUE,
            MAIL = MAIL,
            GENELIST = GENELIST,
            REFERENCE = REFERENCE,
			ALIGNMENT_ENVPROFILE = ALIGNMENT_ENVPROFILE,
			ALIGNMENT_SCRIPT = ALIGNMENT_SCRIPT,
			BASH_PREAMBLE = BASH_PREAMBLE
    }
	
	scatter ( gene in BwaMemBins.genefiles ) {

        call SPLITBAM.SplitBamToGene as SplitBamToGene {
            input:
                DupRemoved_BAM = BwaMemBins.SampleBAMFILE,
                DupRemoved_BAI = BwaMemBins.SampleBAIFILE,
                GENE = basename(gene[2]),
                SAMTOOLS = SAMTOOLS,
				BEDTOOLS = BEDTOOLS,
                SAMPLE_ID = SAMPLE_ID,
				RECIPE = RECIPE,
				BATCH_NAME = BATCH_NAME,
				RUN_NAME = RUN_NAME,
                QUEUE = QUEUE,
				PYTHON = PYTHON,
				LD_LIBRARY_PATH = LD_LIBRARY_PATH,
				REFERENCE = REFERENCE,
				BWA = BWA,
				ALIGNMENT_ENVPROFILE = ALIGNMENT_ENVPROFILE,
				ALIGNMENT_SCRIPT = ALIGNMENT_SCRIPT,
				BASH_PREAMBLE = BASH_PREAMBLE,
				SEQTK = SEQTK,
                MAIL = MAIL,
                CAT = CAT
        }
		
		call BLAT.BlatFilterAssemblePP as BlatFilterAssemblePP {
			input:
				R1path = SplitBamToGene.R1_Bin,
				R2path = SplitBamToGene.R2_Bin,
				GENE = basename(gene[2]),
				mergebins_command_line = MERGEBINS,
				BLAT = BLAT,
				BLATFILTER = BLATFILTER,
				PYTHON = PYTHON,
				LD_LIBRARY_PATH = LD_LIBRARY_PATH,
				CAP3 = CAP3,
				QUEUE = QUEUE,
				MAIL = MAIL,
				SAMTOOLS = SAMTOOLS,
				GENEBED = panel_bed,
				REFGENOME = GenomeFasta,

				# Primary Blat Inputs
				SAMPLE_ID = SAMPLE_ID,
				RECIPE = RECIPE,
				GenomeFasta = GenomeFasta,
				BedFile = panel_bed
		}
        
        
    }
	
	call GENEMETRIC.Aggregate_GeneMetric as Aggregate_GeneMetric {
		input:
			GeneMetrics = SplitBamToGene.GeneMetric,
			SAMPLE_ID = SAMPLE_ID,
			QUEUE = QUEUE,
			MAIL = MAIL
	
	}

    call AGGREGATEINFRAME.AggregateInframe as AggregateInframe {
        input:
            SAMPLE_ID = SAMPLE_ID,
            inframe = BlatFilterAssemblePP.inframe,
            QUEUE = QUEUE,
            MAIL = MAIL
    }

    call INFRAME.InframeAnnotation as InframeAnnotation {
        input:
            PYTHON = PYTHON,
            SAMPLE_ID = SAMPLE_ID,
            inframeFile = AggregateInframe.out_inframe,
            QUEUE = QUEUE,
            MAIL = MAIL
    } 

    call COSMIC.CosmicCheck as CosmicCheck {
        input:
            PYTHON = PYTHON,
            LD_LIBRARY_PATH = LD_LIBRARY_PATH,
            inframefile = InframeAnnotation.o_inframe,
            allfusions = InframeAnnotation.o_allfusions,
            SAMPLE_ID = SAMPLE_ID,
            QUEUE = QUEUE,
            MAIL = MAIL
    }

    call FILTERREPORT.Filter_Final_Report as Filter_Final_Report {
        input:
        PYTHON = PYTHON,
        LD_LIBRARY_PATH = LD_LIBRARY_PATH,
        SAMPLE_ID = SAMPLE_ID,
        FinalReport = CosmicCheck.report,
        QUEUE = QUEUE,
        MAIL = MAIL
    }

    # create custom fasta and gtf using fusion sequences from FUSION2VCF
    call MAKEGTF.Make_GTF as Make_GTF {
        input:
            PYTHON = PYTHON,
            LD_LIBRARY_PATH = LD_LIBRARY_PATH,
            SAMPLE_ID = SAMPLE_ID,
            FilteredReport = Filter_Final_Report.FilteredReport,
			all_frame_file = InframeAnnotation.o_default_all_fusions,
			in_frame_file = InframeAnnotation.o_default_inframe,
            QUEUE = QUEUE,
            MAIL = MAIL
    }

    call BWAINDEX.BWA_Index as BWA_Index {
        input:
            SAMTOOLS = SAMTOOLS,
            BWA = BWA,
            reference = Make_GTF.ReferenceFasta,
            QUEUE = QUEUE,
            MAIL = MAIL
    }

    # create custom bam
    call CUSTOMREF.Generate_Custom_Reference as Generate_Custom_Reference {
        input:
            SAMTOOLS = SAMTOOLS,
            BWA = BWA,
            SAMPLE_ID = SAMPLE_ID,
            fastq_R1 = sample_R1_fastq,
            fastq_R2 = sample_R2_fastq,
            PLATFORM = PLATFORM,
            CENTER = CENTER,
            ref_fa = BWA_Index.ref_fa, # contains path to task instance with ref.fa, fai, amb, etc...
            QUEUE = QUEUE,
            MAIL = MAIL,
			ALIGNMENT_ENVPROFILE = ALIGNMENT_ENVPROFILE,
			ALIGNMENT_SCRIPT = ALIGNMENT_SCRIPT,
			SENTIEONTHREADS = SENTIEONTHREADS,
			BASH_PREAMBLE = BASH_PREAMBLE,
			BASH_SHARED_FUNCTIONS = BASH_SHARED_FUNCTIONS

    }

    call VCFCONVERT.VCF_Convert as VCF_Convert {
        input:
            BAMTOBED = BAMTOBED,
            SAMTOOLS = SAMTOOLS,
            VCFSORT = VCFSORT,
			BWA = BWA,
            SAMPLE_ID = SAMPLE_ID,
            LinkReport = Make_GTF.IGV_Report,
            GenomeFasta = GenomeFasta,
            FastqR2 = sample_R2_fastq,
            SampleBam = Generate_Custom_Reference.ReferenceBAM,
            SampleBai = Generate_Custom_Reference.ReferenceBAI,
			ref_fa = BWA_Index.ref_fa,
			tr_fa = TRANSCRIPT_REFERENCE,
            QUEUE = QUEUE,
			SEQTK = SEQTK,
			BEDTOOLS = BEDTOOLS,
			ALIGNMENT_SCRIPT = ALIGNMENT_SCRIPT,
			ALIGNMENT_ENVPROFILE = ALIGNMENT_ENVPROFILE,
			BASH_PREAMBLE = BASH_PREAMBLE,
			PERL = PERL,
            MAIL = MAIL
    }

    call CONTROLMETRICS.Control_Metrics as Control_Metrics {
        input:
            PYTHON = PYTHON,
            LD_LIBRARY_PATH = LD_LIBRARY_PATH,
            SAMPLE_ID = SAMPLE_ID,
            BATCH_NAME = BATCH_NAME,
            RUN_NAME = RUN_NAME,
            SAMPLE_PROJECT = SAMPLE_PROJECT,
            RECIPE = RECIPE,
            ToTSV = VCF_Convert.tovcf,
            Read_Metrics = Aggregate_GeneMetric.Read_Metrics,
			DedupJSON = Aggregate_dedup.DedupedJson,
			AllReadJSON = CatFastq.AllReadsJson,
            MAIL = MAIL,
            QUEUE = QUEUE
    }

    call DELIVERY.Deliver as Deliver_Reports
    {
        input:
            FilesToDeliver = select_all([
                Filter_Final_Report.FilteredReport,
                VCF_Convert.vcf,
                VCF_Convert.tovcf,
                VCF_Convert.junctiontovcf ,
                CatFastq.AllReadsJson,
                TrimFastq.TrimmedJson,
                Aggregate_dedup.DedupedJson ] ),
            OutputFolder = OUTPUT_DIR + "/reports"
    }

    call DELIVERY.Deliver as DeliverIGV
    {
        input:
            FilesToDeliver = [
                BWA_Index.ref_fa,
                BWA_Index.ref_fai,
                VCF_Convert.juncbam,
                VCF_Convert.juncbai,
                BwaMemBins.SampleBAMFILE,
                BwaMemBins.SampleBAIFILE,
                Generate_Custom_Reference.ReferenceBAM,
                Generate_Custom_Reference.ReferenceBAI,
                Make_GTF.IGV_Session,
                Make_GTF.IGV_GTF
            ],
            OutputFolder = OUTPUT_DIR + "/reports/igv_session"

    }

    call DELIVERY.Deliver as DeliverMetrics
    {
        input:
            FilesToDeliver = [
                Control_Metrics.metrics
            ],
            OutputFolder = OUTPUT_DIR + "/metrics"
    }

    call DELIVERY.SubmitMetrics as SubmitMetrics
    {
        input:
            METRIC_FILES = [ Control_Metrics.metrics ]
    }



    output {
        File REPORT = Filter_Final_Report.FilteredReport
        File RoqcmMetrics = Control_Metrics.metrics
        File ToVCF = VCF_Convert.tovcf
		File JunctionToVCF = VCF_Convert.junctiontovcf
        File VCF = VCF_Convert.vcf
        File IGV_Fasta = BWA_Index.ref_fa
        File IGV_FAI = BWA_Index.ref_fai
        File IGV_GTF = Make_GTF.IGV_GTF
        File IGV_Session = Make_GTF.IGV_Session
        File SampleBAM = Generate_Custom_Reference.ReferenceBAM
        File SampleBAI = Generate_Custom_Reference.ReferenceBAI
		File JuncBAM = VCF_Convert.juncbam
		File JuncBAI = VCF_Convert.juncbai
		File GeneBAM = BwaMemBins.SampleBAMFILE
		File GeneBAI = BwaMemBins.SampleBAIFILE
		File AllReadsJson = CatFastq.AllReadsJson
		File TrimmedJson = TrimFastq.TrimmedJson
		File? DedupedJson = Aggregate_dedup.DedupedJson
    }		

} # End UMIFUSION Pipeline


