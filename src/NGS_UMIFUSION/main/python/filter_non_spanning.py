#!/usr/bin/python
import sys
import re
import argparse
import logging
import os

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

def main(inpArgs):
    SpanningReads = GetSpanningReads(inpArgs.sam, inpArgs.padding)
    OutputFile = open(os.path.abspath(inpArgs.output), "w")
    OutputFile.write(SpanningReads)
    OutputFile.close()
    
def CheckSpan(BreakPoint,StartPos,SeqLen,padding):
    ####          SEQ1 - BR - SEQ2 
    SpanFlag = 1
    if int(StartPos) >= int(BreakPoint) - int(padding):
        SpanFlag = 0
    if int(StartPos) + SeqLen <= int(BreakPoint) + int(padding):
        SpanFlag = 0
    return SpanFlag
    
def GetSpanningReads(sam,padding):
    try:
        with open(sam, "r") as samfilereq:
            SpanReads = ""
            for eachLine in samfilereq:
                # eachLine example:
                # UMI3996914:Group1:Size1_20-WFYQD-A-02-00
                # 16
                # UBE3Cex18_UBE3Cex19_150   (fake chromosome name; in custom fusion.)
                # 94
                # 60
                # 101M11S
                # *
                # 0
                # 0
                # CTTGTGGGAGATTCTTTTGCCAGACATTACTACTTCCTAGGCAGAATGCTTGGAAAGGCTCTCTATGAGAACATGCTGGTGGAGCTGCCCTTTGCAGGCTTAGGACTCCAAT
                # HHGHHHHHHHHHGHHHGHGHHHHHHHHHHHHHHHHHHHHHHHHHHHHGHHHHHHHHHHGHHHHHHHHHHHHHHHHHHHHHHHHGGGGGHHHHHHHHHHGHHHGGGGGGGGGG
                # NM:i:0
                # MD:Z:101
                # AS:i:101
                # XS:i:0
                # RG:Z:/dlmp/dev/scripts/sources/teamwork/shengbing/temp/UMIFUSION/call-VCF_Convert/20-WFYQD-A-02-00
                eachLine_split = eachLine.split("\t")
                ContigName = eachLine_split[2]
                BreakPoint = ContigName.split("_")[-1]
                StartPos = eachLine_split[3]
                Cigar = eachLine_split[5]
                SeqLen = len(eachLine_split[9])
                SpanFlag = CheckSpan(BreakPoint, StartPos, SeqLen, padding)
                if SpanFlag == 1:
                    SpanReads += eachLine
            return SpanReads
        samfilereq.close()
                
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(ex.errno)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", "--samfile",
                        dest="sam",
                        help="the junction sam file",
                        required=True)
    parser.add_argument("-p", "--padfile",
                        dest="padding",
                        help="the padding req",
                        required=True)
    parser.add_argument("-o", "--filteredBAMfile",
                        dest="output",
                        help="spanning only reads junctions bam file",
                        required=True)
    inpArgs = parser.parse_args()
    main(inpArgs)