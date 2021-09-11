import subprocess
import argparse
import logging
import collections


"""
Using All_Fusions.xls (In-Frame_Fusions.xls is just a subset) from FUSION2VCF, this script basically creates "reference.fa" whose sequences are fusion sequences from FUSION2VCF;
each fusion sequence is split into two parts by the breakpoint, one goes to gtf as one partner, the other also
goes to gtf as another partner;
one more column is added to the end of FilteredReport.tsv and output as igv_link_report.tsv.
At the same time, entries from the control fusions are also appended to the three output files.

Example of output:
reference.fa
>ZNF451:NM_015555:E1|FUS:NR_028388:E6_2_245
GGAAGCCCGGGAGTGAGAGAAAGCGGCTCCGGGGGCATAGCGGGCCAGTAAGGGCCGCTCCTCCTTTGAAGAGGTTTTGCGTCTCTTTCCGCCGGTGGCGTCGGCGCTCACGCAGGGG
CGGGTCCCGGTAGCGCCAGGCGGTGCAGGGCGGGAAGGGGATTCGTGGCGACGGCGGCGGCAGGGACAGCAGGAGCAGTGGTGCTGTCAGCGCGGCCGTCGGAGACATGGGAGACCCG
GGGTCGGAGTGGCGGCGGCGGCGGCGGCGGTGGTGGTTACAACCGCAGCAGTGGTGGCTATGAACCCAGAGGTCGTGGAGGTGGCCGTGGAGGCAGAGGTGGCATGGGGTAGGTGTC
TCATGAGCCAGGGAGTATCTTTGGTGGGGAGTGTGGAGGATTGCATGAATCTCCCTGAAGCCAGTCCCTAGTGCATGGTTTAGTATTCTTGT
note: 245 is the breakpoint

fusion.gtf
ZNF451:NM_015555:E1|FUS:NR_028388:E6_2_245	unknown	CDS	1	245	.	+	.gene_id "ZNF451";transcript_id "ZNF451:NM_015555:E1";
ZNF451:NM_015555:E1|FUS:NR_028388:E6_2_245	unknown	CDS	246	445	.	+	.gene_id "FUS";transcript_id "FUS:NR_028388:E6";

igv_link_report.tsv (note the added last column which is identical to the headers of fusion sequences in reference.fa)
General_Information					Exon_Information			Read_Information		Additional_Information						Fusion_coordinates
5'-3'Gene_Partners	Fusion_Location	Frame_Status	5'_Exon_Annotation	5'_Frame	3'_Exon_Annotation	3'_Frame	Unique Reads	Total Reads	Fusion_Annotation	Human_Tissues	Average_Expression	Tissue_Name	Chr_5'	Coordinate_5'	Chr_3'	Coordinate_3'	Distance_between_breakpoints	ExperienceDB_Status	Chimeric_Reference_Header
FLI1~EWSR1	Exon_Body-Exon_boundary	In-Frame	+|Body_E8|FLI1|NM_002017	3	+|Start_E7|EWSR1|NM_005243	1	100	100	Fusion-Candidate	NO	-	-chr11	128679073	chr22	29682912	-	EXPERIENCE_DB	FLI1:NM_002017:E8|EWSR1:NM_005243:E7_200


####### INPUT #######
1) Inframe directory that has filtered fusion report 
2) Fastq directory that has raw fastq files
3) Config file

###### LOGIC #######
1) This program iterates through each sample directory and looks for Filtered report.
2) Using filtered report it creates the custom reference and gtf file
3) It then takes the appropriate sample's fastq file from fastq directory 
4) It aligns the fastq reads to custom reference and creates bam, sorts bam and indexes it
5) A fusion report is created at this point with links added to bam. So this is now Filtered report + igv link added
6) it then calls the igv_report script. the igv_report script basically scans through the bam and counts reads that 
have only junction 20 bases (10 bases on each side).
7) The igv_report script creates a report where it replaces current unique mols and total read counts based on counts 
from above. The report is is called <SAMPLE>_tovcf.tsv
8) Finally the vcf conversion script is called
"""

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

chimera_delimiter = "|"
count_delimiter = "_"
gene_delimiter = "~"

class ConfigClass:
    pass


def main(input_args):

    # Makes GTF, custom reference and report file with igv_link
    make_gtf(input_args.filtered_report,
             input_args.output_report,
             input_args.output_ref,
             input_args.output_gtf,
             input_args.control_ref,
             input_args.control_gtf,
             input_args.control_fusions,
             input_args.all_fusions,
             input_args.basesreq,
             input_args.inframe_fusions)

    return


def process_gene(eachline_split):
    # Below function ProcessGene returns Gene1,Gene2.
    # Some genes have - in them. Example it can be ASPM-1. Fusion line will be ASPM-1~ARX.
    # In this case we have to get genes accurately.
    # So this function checks for number of - in string and returns gene name accordingly.

    # Short circuit evaluation if we have a proper delimiter in this field
    if gene_delimiter in eachline_split[0]:
        return eachline_split[0].split(gene_delimiter)[0],  eachline_split[0].split(gene_delimiter)[1]
    else:
        raise RuntimeError("Delimiter {} not found in {}.".format(gene_delimiter, eachline_split[0]))

def truncateseq(sequence, basesreq, direction):
    modflag = 0
    if len(sequence) > int(basesreq):
        if direction == "left":
            sequence = sequence[-int(basesreq):]
            modflag = 1
        else:
            sequence = sequence[:int(basesreq)]
            modflag = 1
    return (sequence, modflag)

def getReferences(frame,References, BreakPointDict, basesreq):
    """

    :param frame:
    :param References:
    :param BreakPointDict:
    :return:
        References: {'nil:NA:NA|ACTB:NM_001101:E3|chrY:19869697-chr7:5568948':
        'GGGAGTAGCCCTCGTAGATGGGCACCGTGTGGGTGACCCTGTGTCCACAGTCCATGACAATGCCAGTGGTGCGCCCAAAGGCATAGAGGGACAGCACAT\
        CCCGGATGGCCACGTACATGGCCGGGGTATTGAAGGTCTCAAACATAATCTGAGTCATTTTCTCTCTGTTGTCCTTGGGGTTCAGTGGGTCCTCGGTCAGC\
        GTGGGGCAGCCCCGGGAGCGGGCGGGAGGCAAGGGCGCTTTCTCTGCACAGGAGCCTCCCGGTTTCCGGGGTGGGGGCTGCGCCCGTGCTCAGGGCTTCTTG\
        TCCTTTCCTTCCCAGGGCGTGATGGTGGGCATGGGTCAGAAGGATTCCTATGTGGGCGACGAGGCCCAGAGCAAGAGAGGCATCCTCACCCTGAAGTA'}
        key format: [gene1:transcrip_gene1:ex_gene1|gene2:transcrip_gene2:ex_gene2|Chr_Gene1:BP_Gene1-Chr_Gene2:BP_Gene2]
        value: the fusion sequence

        BreakPointDict: {'nil:NA:NA|ACTB:NM_001101:E3|chrY:19869697-chr7:5568948': '200'}
        same key as References, value is the position of the breakpoint in the fusion sequence
    """
    #print(basesreq)
    try:
        with open(frame, "r") as frameFile:
            LineCount = 0
            for each_line in frameFile:
                LineCount += 1
                if LineCount <= 2:
                    continue
                each_line_split = each_line.split("\t")

                Exon_Gene1 = ""
                Exon_Gene2 = ""
                if len(each_line_split[5]) < 5:
                    Tr_Gene1 = "NA"
                    Exon_Gene1 = "NA"
                else:
                    Tr_Gene1 = each_line_split[5].split("|")[3]
                    if "_" in each_line_split[5].split("|")[1]:
                        Exon_Gene1 = each_line_split[5].split("|")[1].split("_")[1]
                if len(each_line_split[7]) < 3:
                    Tr_Gene2 = "NA"
                    Exon_Gene2 = "NA"
                else:
                    Tr_Gene2 = each_line_split[7].split("|")[3]
                    if "_" in each_line_split[7].split("|")[1]:
                        Exon_Gene2 = each_line_split[7].split("|")[1].split("_")[1]

                Gene1, Gene2 = process_gene(each_line_split)
                Chr_Gene1 = each_line_split[17]
                BP_Gene1 = each_line_split[18]
                Chr_Gene2 = each_line_split[19]
                BP_Gene2 = each_line_split[20]
                Breakpoint = Chr_Gene1 + ":" + BP_Gene1 + "-" + Chr_Gene2 + ":" + BP_Gene2
                Gene1 = Gene1 + ":" + Tr_Gene1 + ":" + Exon_Gene1
                Gene2 = Gene2 + ":" + Tr_Gene2 + ":" + Exon_Gene2

                Identifier = Gene1 + chimera_delimiter + Gene2 + chimera_delimiter + Breakpoint
                Sequence = each_line_split[4]
                LocationofBP_in_sequence = Sequence.find("-")
                #Sequence = ATGTCTGATGTA-GCTGCAAATGCCC
                #LocationofBP = 15
                #Check if sequence left to the 15 is > N bases, say N=150, if > 150 is yes, truncate to 150. Similarly do it for the right. 
                LeftSequence = Sequence[:LocationofBP_in_sequence]
                RightSequence = Sequence[LocationofBP_in_sequence+1:]
                LeftSequence, modflag = truncateseq(LeftSequence,basesreq,"left")
                if modflag == 1:
                    LocationofBP_in_sequence = basesreq
                RightSequence, modflag = truncateseq(RightSequence,basesreq,"right")
                BP_Pos = str(LocationofBP_in_sequence)
                References[Identifier] = LeftSequence + RightSequence
                BreakPointDict[Identifier] = BP_Pos
            return References, BreakPointDict
    except IOError as ioerr:
        logger.error(ioerr.strerror)
        exit(1)


def make_gtf(filtered_report_file, igv_report, igv_reference, igv_gtf, sampleref, control_gtf,
             control_fusions, all_fusions, basesreq, inframe_fusions):

    # Reads control file and writes it to reference file. this chemistry has some control fusions in it.
    #  These always need alignments and should be there in report.
    # the control files are stored in config and is appended to every fusion report.

    FusionDict = collections.OrderedDict()
    LineCount = 0
    with open(filtered_report_file, "r") as filtered_report, \
            open(igv_report, "w") as IGVReport, \
            open(igv_reference, "w") as IGV_reference, \
            open(igv_gtf, "w") as IGV_GTF:

        # IGV_reference: reference.fa
        # IGV_gtf:

        # copy control reference to output file, e.g., reference.fa
        with open(sampleref, "r") as sample_reference:
            for eachLine in sample_reference:
                IGV_reference.write(eachLine)

        # copy control GTF to output gtf, e.g., 'fusion.gtf'
        with open(control_gtf, "r") as sample_gtf:
            for eachLine in sample_gtf:
                IGV_GTF.write(eachLine)

        VisitedBP = {}
        ChimericReferences = {}
        Breakpoints = {}
        ChimericReferences, Breakpoints = getReferences(all_fusions, ChimericReferences, Breakpoints, basesreq)
        ChimericReferences, Breakpoints = getReferences(inframe_fusions, ChimericReferences, Breakpoints, basesreq)

        for eachLine in filtered_report:
            LineCount += 1
            if LineCount == 1:
                IGVReport.write(eachLine)
                continue
            if LineCount == 2:
                # add one column, the header is "Chimeric_Reference_Header"
                IGVReport.write(eachLine.strip() + "\t" + "Chimeric_Reference_Header" + "\n")
                continue
            else:
                # Example Line QKI~NTRK2	Exon-Exon_boundary	In-Frame	+|End_E6|QKI|NM_006775	2
                # +|Start_E15|NTRK2|NM_006180	3	1718	2959	Fusion-Candidate	-	-	-	chr6
                # 163984751	chr9	87475955	76508796
                # http://localhost:60151/goto?locus=QKI:NM_006775:E6-NTRK2:NM_006180:E15
                # Get all gene, transcript, exon , strand info
                Exon_Gene1 = ""
                Exon_Gene2 = ""
                eachLine_split = eachLine.split("\t")
                if len(eachLine_split[3]) < 3:
                    Tr_Gene1 = "NA"
                    Exon_Gene1 = "NA"
                else:
                    Tr_Gene1 = eachLine_split[3].split("|")[3]
                    if "_" in eachLine_split[3].split("|")[1]:
                        Exon_Gene1 = eachLine_split[3].split("|")[1].split("_")[1]
                if len(eachLine_split[5]) < 3:
                    Tr_Gene2 = "NA"
                    Exon_Gene2 = "NA"
                else:
                    Tr_Gene2 = eachLine_split[5].split("|")[3]
                    if "_" in eachLine_split[5].split("|")[1]:
                        Exon_Gene2 = eachLine_split[5].split("|")[1].split("_")[1]
                Gene1, Gene2 = process_gene(eachLine_split)
                Gene1 = Gene1 + ":" + Tr_Gene1 + ":" + Exon_Gene1
                Gene2 = Gene2 + ":" + Tr_Gene2 + ":" + Exon_Gene2

                Chr_Gene1 = eachLine_split[13]
                BP_Gene1 = eachLine_split[14]
                Chr_Gene2 = eachLine_split[15]
                BP_Gene2 = eachLine_split[16]
                Breakpoint = Chr_Gene1 + ":" + BP_Gene1 + "-" + Chr_Gene2 + ":" + BP_Gene2

                Identifier = Gene1 + chimera_delimiter + Gene2 + chimera_delimiter + Breakpoint

                ChimericReference = ChimericReferences[Identifier]
                BreakpointStr = Breakpoints[Identifier]
                Header = ">" + Gene1 + "|" + Gene2


                logger.debug("Gene1 {} Gene2 {}".format(Gene1,Gene2))
                ChimericReference_Header = Header
                ReqHeader = ChimericReference_Header
                if ChimericReference_Header not in FusionDict:
                    FusionDict[ChimericReference_Header] = 1
                    ReqHeader = ReqHeader + "_" + BreakpointStr
                else:
                    # This adds numbers for multiple entries
                    ReqHeader = ChimericReference_Header + count_delimiter + str(FusionDict[ChimericReference_Header]) \
                                + "_" + BreakpointStr

                    FusionDict[ChimericReference_Header] += 1
                IGV_reference.write(ReqHeader + "\n" + ChimericReference + "\n")

                End = len(ChimericReference)

                # Write GTF to load up in session xml file
                GTF_ID = ReqHeader.replace(">", "") + "\tunknown\tCDS\t"
                GTF_Line1 = "1\t" + BreakpointStr +"\t.\t+" + '\t.\tgene_id "' + Gene1.split(":")[0] + '";transcript_id "' + Gene1 + '";'
                GTF_Line2 = str(int(BreakpointStr) + 1) + "\t" + str(End) + "\t.\t+" + '\t.\tgene_id "' + Gene2.split(":")[0] + '";transcript_id "' + Gene2 + '";'
                GTF_Str = GTF_ID + GTF_Line1 + "\n" + GTF_ID + GTF_Line2 + "\n"
                IGV_GTF.write(GTF_Str)

                IGVReport.write(eachLine.strip() + "\t" + ReqHeader.replace(">", "") + "\n")

        with open(control_fusions, "r") as ControlFusions:
            for eachLine in ControlFusions:
                IGVReport.write(eachLine)

        IGVReport.close()
        IGVReport.close()
        IGVReport.close()

    return


if __name__ == '__main__':
    usage = "python igv_session.py "+ \
            "-i <final_filtered_report.tsv> " + \
            "-t <sample_ref_template> " + \
            "-g <gtf_template> " + \
            "-c <control_fusions> " + \
            "-a <all_fusions.tsv> " + \
            "-f <inframe_fusions.tsv> " + \
            "-o1 <output_report> " + \
            "-o2 <output_reference_fa " + \
            "-o3 <output_gtf> "

    parser = argparse.ArgumentParser(description='igv_vcf.py usage')
    parser.add_argument("-i", "--input", dest="filtered_report", required=True, help="Final Filtered Report File")
    parser.add_argument("-t", "--ref_template", dest="control_ref", required=True, help="Control Ref Template")
    parser.add_argument("-g", "--gtf_template", dest="control_gtf", required=True, help="GTF Template")
    parser.add_argument("-a", "--all_fusions_tsv", dest="all_fusions", required=True, help="all fusion file")
    parser.add_argument("-f", "--inframe_fusions_tsv", dest="inframe_fusions", required=True, help="inframe fusion file")
    parser.add_argument("-c", "--control_fusions", dest="control_fusions", required=True, help="Control Fusions")
    parser.add_argument("-o1", "--output_report", dest="output_report", required=True,
                        help="Output Report Filename (sampleName_igv_link_report.tsv)")
    parser.add_argument("-o2", "--output_ref", dest="output_ref", required=True,
                        help="Output Reference Filename (reference.fa)")
    parser.add_argument("-o3", "--output_gtf", dest="output_gtf", required=True,
                        help="Output GTF Filename (fusion.gtf)")
    parser.add_argument("-b", "--breakpoint_bases", dest="basesreq", required=True,
                        help="Bases required for reference on each side")

    inpArgs = parser.parse_args()
    main(inpArgs)
