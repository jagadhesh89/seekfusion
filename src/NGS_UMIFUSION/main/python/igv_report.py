#
import subprocess
import argparse
import logging
import collections


# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)


def main(inp_args):
    process_final_reports(inp_args.igvlinkreport, inp_args.bam, inp_args.out, inp_args.samtools,
                          inp_args.bamtobed, inp_args.readid, inp_args.reference, inp_args.padding,
                           inp_args.gchigh, inp_args.gclow, inp_args.mode, inp_args.threshold)

def GetGCPercent(sequence):
    gc_count = sequence.count("g") + sequence.count("c") + sequence.count("G") + sequence.count("C")
    gc_fraction = float(gc_count) / len(sequence)
    return 100 * gc_fraction

def get_read_count(bam_file, locus, samtools, bam_to_bed, reference,paddingreq,chimlenreq,gchigh,gclow,seq_locus):
    """

    :param bam_file:
    :param locus:   'NAB2:NM_005967:E6|STAT6:NM_001178078:E16_16_192'
    :param samtools: '/biotools8/biotools/samtools/1.3.1/samtools'
    :param bam_to_bed: '/biotools8/biotools/bedtools/2.26.0/bin/bamToBed'
    :param reference: 'reference.fa'
    :param paddingreq: 20
    :param chimlenreq: breakpoint position
    :param gchigh: 91
    :param gclow: 9
    :return:
        number of valid junction reads: e.g., 143

        FusionReads:
        OrderedDict of reads (keys are the read id, e.g., "UMI14504444:Group2:Size1_20-WFYQD-A-02-00")
    """
    try:
        paddingreq = int(paddingreq)
    except:
        logger.exception("Input padding not an integer")
        exit(1)
    try:
        chimlenreq = int(chimlenreq)
    except:
        logger.exception("Input chimlen not an integer")
        exit(1)

    #chimeric reference is 150 basepairs on each side of breakpoint
    #We need reads that span X bases on each side of breakpoint, X=padding 
    #Use BAM to bed format to retrieve reads that span the Breakpoint +/- Padding bases
    LeftPad = chimlenreq - paddingreq
    RightPad = chimlenreq + paddingreq
    if chimlenreq < paddingreq:
        LeftPad = 0
    if len(seq_locus) - chimlenreq < paddingreq:
        RightPad = len(seq_locus)
    ReadsPad = str(LeftPad) + "-" + str(RightPad)
    Command = samtools + " view -b " + bam_file + " \'" + locus + ":" + ReadsPad + "\' | " + bam_to_bed + " -cigar"

    p = subprocess.Popen(Command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print(Command)
    ReadsinVarPos, err2 = p.communicate()
    ReadsinVarPos = ReadsinVarPos.decode().split("\n")

    #logger.info("reads: {}".format(ReadsinVarPos))
    FusionReads = collections.OrderedDict()
    for eachRead in ReadsinVarPos:
        # example read:
        #NAB2:NM_005967:E6|STAT6:NM_001178078:E16_16_192	75	203	UMI11854389:Group1:Size23_20-WFYQD-A-02-00/2	23	+	11S128M
        eachRead_split = eachRead.split("\t")
        if len(eachRead_split) < 3:
            continue
        Start = eachRead_split[1]
        Stop = eachRead_split[2]
        ReadID = eachRead_split[3].split("/")[0]
        #Check if the read started before the LeftPad and extended beyond RightPad of breakpoint
        #We need spanning reads
        if int(Start) < LeftPad and int(Stop) > RightPad:
            FusionReads[ReadID] = 1
    return len(FusionReads), FusionReads


def GCDeterminator(reference,paddingreq,gchigh,gclow):
    with open(reference, "r") as ReferenceFile:
        LocustoIgnore = {}
        Locus = ""
        for eachLine in ReferenceFile:
            if ">" in eachLine[0]:
                Locus = eachLine[1:].strip()
                chimlenreq = Locus.split("_")[-1]
                chimlenreq = int(chimlenreq)
            else:
                LeftPad = chimlenreq - paddingreq
                RightPad = chimlenreq + paddingreq
                if chimlenreq < paddingreq:
                    LeftPad = 0
                if len(eachLine) - chimlenreq < paddingreq:
                    RightPad = len(eachLine)

                LSequence = eachLine[LeftPad:chimlenreq]
                RSequence = eachLine[chimlenreq:RightPad]
                #print(Locus,chimlenreq,LeftPad,eachLine,LSequence,RSequence,"XXXXXXXXXxx")

                LGCPercent = GetGCPercent(LSequence)
                RGCPercent = GetGCPercent(RSequence)

                RGCFail = 1
                LGCFail = 1
                try:
                    gchigh = int(gchigh)
                except:
                    logger.exception("Input gc high threshold not an integer")
                    exit(1)
                try:
                    gclow = int(gclow)
                except:
                    logger.exception("Input gc low threshold not an integer")
                    exit(1)
                #Check if Left Junction and Right Junction sequence are within GC thresholds
                if LGCPercent < gchigh and LGCPercent > gclow:
                    LGCFail = 0
                if RGCPercent < gchigh and RGCPercent > gclow:
                    RGCFail = 0

                if LGCFail == 1 or RGCFail == 1:
                    LocustoIgnore[Locus] = 1
    return LocustoIgnore


def load_reference(referenceFile):
    """

    :param referenceFile:
    :return: dictionary
        'ZNF451:NM_015555:E1|FUS:NR_028388:E6_2_245': 'GGAAGCCCGGGAGTGAGAGAAAGCGGCTCCGGGGGCATAGCGGGCCAGTAAGGGCCGCTCC
        TCCTTTGAAGAGGTTTTGCGTCTCTTTCCGCCGGTGGCGTCGGCGCTCACGCAGGGGCGGGTCCCGGTAGCGCCAGGCGGTGCAGGGCGGGAAGGGGATTCGTGGCGA
        CGGCGGCGGCAGGGACAGCAGGAGCAGTGGTGCTGTCAGCGCGGCCGTCGGAGACATGGGAGACCCGGGGTCGGAGTGGCGGCGGCGGCGGCGGCGGTGGTGGTTACA
        ACCGCAGCAGTGGTGGCTATGAACCCAGAGGTCGTGGAGGTGGCCGTGGAGGCAGAGGTGGCATGGGGTAGGTGTCTCATGAGCCAGGGAGTATCTTTGGTGGGGAGT
        GTGGAGGATTGCATGAATCTCCCTGAAGCCAGTCCCTAGTGCATGGTTTAGTATTCTTGT'}
        key: fasta headers
        value: fasta sequences
    """
    ref_dict = {}
    with open(referenceFile, "r") as ReferenceFile:
        Locus = ""
        for eachLine in ReferenceFile:
            if ">" in eachLine[0]:
                Locus = eachLine[1:].strip()
            else:
                ref_dict[Locus] = eachLine.strip()
    return ref_dict
            
           
# ToTSV file  (untidy: number of columns are not consistent)
#
# 0 - 5'-3'Gene_Partners
# 1 - Fusion_Location
# 2 - Frame_Status
# 3 - 5'_Exon_Annotation
# 4 - 5'_Frame
# 5 - 3'_Exon_Annotation
# 6 - 3'_Frame
# 7 - Unique_Reads
# 8 - Total_Reads
# 9 - Fusion_Annotation
# 10 - Human_Tissues
# 11 - Average_Expression
# 12 - Tissue_Name
# 13 - Chr_5'
# 14 - Coordinate_5'
# 15 - Chr_3'
# 16 - Coordinate_3'
# 17 - Distance_between_breakpoints
def process_final_reports(igv_link_file, bam_file, output_file, samtools, bam_to_bed,
                          readid, reference, padding, gchigh, gclow, mode, threshold):
    """

    :param igv_link_file:
    :param bam_file:
    :param output_file:
    :param samtools:
    :param bam_to_bed:
    :param readid:
    :param reference:
    :param padding:
    :param gchigh:
    :param gclow:
    :param mode:
    :param threshold:
    :return:
        "tovcf.tsv": igv_link_file with updated  "Unique Reads" and	"Total Reads" columns
        "readid.txt": read IDs that cover the breakpoints and extend to both sides by 'padding' bps
    """
    try:
        with open(igv_link_file, "r") as IGVLINKReportFile, open(output_file, "w") as ToVCFFile, open(readid, "w") as ReadIDFile:

            MBCDict={}
            LineCount = 0
            FilteredLocus = GCDeterminator(reference, int(padding), gchigh, gclow)
            VisitedBP = []
            ref_dict = load_reference(reference)
            for eachLine in IGVLINKReportFile:
                LineCount += 1

                # Write the header verbatim
                if LineCount < 3:
                    ToVCFFile.write(eachLine)
                    continue

                Locus = eachLine.split("\t")[-1].strip()
                if Locus in FilteredLocus:
                    #print("Locus " + Locus + " filtered")
                    continue
                    
                Fusion = eachLine.split("\t")[0]
                if "nil~" in Fusion or "~nil" in Fusion:
                    continue
                
                bps = eachLine.split("\t")[13] + ":" + eachLine.split("\t")[14] + "-" + eachLine.split("\t")[15] + ":" \
                    + eachLine.split("\t")[16]
                
                if bps in VisitedBP:
                    if bps != "chr1:1-chr2:1":
                        continue
                else:
                    VisitedBP.append(bps)
                    
                if mode == "junc":
                    if int(eachLine.split("\t")[8]) < int(threshold):
                        #print(eachLine)
                        continue
                
                chimlen = Locus.split("_")[-1]  # this is the breakpoint position
                seq_locus = ref_dict[Locus]
                FusionReadCount, FusionReads = get_read_count(bam_file, Locus, samtools, bam_to_bed, reference,
                                                              int(padding), int(chimlen), gchigh, gclow, seq_locus)
                
                for eachReadID in FusionReads:
                    ReadIDFile.write(eachReadID+"\n")
                
                eachLine = eachLine.strip()
                eachLine_split = eachLine.split("\t")
                logger.debug(eachLine)
                ReqStr = ""
                for i in range(0, len(eachLine_split)):
                    if i == 0:
                        ReqStr = eachLine_split[i]
                        continue
                    if i == 7:  # "Unique Reads" field
                        ReqStr = ReqStr + "\t" + str(FusionReadCount)
                        continue
                    if i == 8:   # "Total Reads" field
                        ReqStr = ReqStr + "\t" + str(FusionReadCount)
                        continue
                    ReqStr = ReqStr + "\t" + eachLine_split[i]
                ToVCFFile.write(ReqStr + "\n")
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='IGV to VCF Mediator')
    parser.add_argument("-i", "--igvlinkfile",
                        dest="igvlinkreport",
                        help="the IGV link report",
                        required=True)
    parser.add_argument("-b", "--Bamfile",
                        dest="bam",
                        help="The path to the custom bam",
                        required=True)
    parser.add_argument("-o", "--outFile",
                        dest="out",
                        help="The outputFile \"sample_tovcf.tsv\"",
                        required=True)
    parser.add_argument("-r", "--readIDFile",
                        dest="readid",
                        help="The outputFile \"read ID\"",
                        required=True)
    parser.add_argument("-R", "--referenceFile",
                        dest="reference",
                        help="The reference file ",
                        required=True)
    parser.add_argument("-m", "--modeReq",
                        dest="mode",
                        help="The mode \"\"",
                        required=True)
    
    parser.add_argument("-t", "--readTHreshold",
                        dest="threshold",
                        help="The threshold \"\"",
                        required=True)
                        
    parser.add_argument("-S", "--SAMTOOLS", dest="samtools", help="Samtools executable", required=True)
    parser.add_argument("-B", "--BAMTOBED", dest="bamtobed", help="BamToBed executable", required=True)
    parser.add_argument("-p", "--PADDINGPARAM", dest="padding", help="padding param required", required=True)
    parser.add_argument("-u", "--UPPERGCLIMIT", dest="gchigh", help="Highest_allowed_GC", required=True)
    parser.add_argument("-l", "--LOWERGCLIMIT", dest="gclow", help="Lowest_allowed_GC", required=True)

    inpArgs = parser.parse_args()
    main(inpArgs)
