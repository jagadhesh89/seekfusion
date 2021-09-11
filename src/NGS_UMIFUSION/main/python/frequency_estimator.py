#!/usr/bin/python
import sys
import re
import argparse
import logging
import os
import subprocess

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

def GetLocus(eachLine_split):
    info = eachLine_split[7]
    info_split = info.split(";")
    #print(info_split)
    locus = ""
    for eachInfo in info_split:
        if eachInfo.split("=")[0] == "IGV_ID":
            locus = eachInfo.split("=")[1]
            break
    return locus

    
def CountFusionSupportingReads(samtools, junctionsbam, locus):
    # junctionsbam has applied with “filter_non_spanning.py”; no window is needed here
    Command = samtools + " view " + junctionsbam + " \'" + locus + "\' | cut -f1,6 | sort | uniq | wc -l"
    p = subprocess.Popen(Command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(Command)
    ReadsSupportingFusion, err2 = p.communicate()
    
    return ReadsSupportingFusion
    
    
def GetAllReads(samtools, allbam, locus, Left, Right):
    Command = samtools + " view " + allbam + " \'" + locus + ":" + str(Left) + "-" + str(Right) + "\' | cut -f1,6 | sort | uniq | wc -l"
    p = subprocess.Popen(Command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(Command)
    AllReads, err2 = p.communicate()
    
    return AllReads
    
  
def calculateFrequency(locus, allbam, junctionsbam, samtools, window):
    #samtools view -b test.bam 'EWSR1:NM_005243:E12|NR4A3:NM_006981:E3_130:129-131'
    #print(locus)
    BreakPoint = int(locus.split("_")[-1])
    window = int(window)
    
    Left = BreakPoint-window
    if Left < 0:
        Left = 0
    Right = BreakPoint + window
    
    FusionSupportingReads = CountFusionSupportingReads(samtools, junctionsbam, locus)
    AllReads = GetAllReads(samtools, allbam, locus, Left, Right)
    
    if float(FusionSupportingReads) > float(AllReads):
        FusionSupportingReads = AllReads
    
    Frequency = round((float(FusionSupportingReads) / float(AllReads)),2)
    
    return str(Frequency)
  

def main(inpArgs):
    VCFFile = inpArgs.vcf
    junctionsbam = inpArgs.junctions
    allbam = inpArgs.bam
    samtools = inpArgs.samtools
    window = inpArgs.window
    try:
        with open(VCFFile, "r") as vcffilereq, open(os.path.abspath(inpArgs.output), "w") as outputfile:
            Header = ""
            VariantLines = ""
            FreqDict = {}
            for eachLine in vcffilereq:
                if eachLine[0] == "#":
                    Header += eachLine
                    continue
                eachLine_split = eachLine.split("\t")
                locus = GetLocus(eachLine_split)
                if len(locus) < 1:
                    continue
                chr = eachLine_split[0]
                pos = eachLine_split[1]
                id = eachLine_split[2]
                ref = eachLine_split[3]
                alt = eachLine_split[4]
                qual = eachLine_split[5]
                filter = eachLine_split[6]
                info = eachLine_split[7]
                format = eachLine_split[8]
                format += ":FF"
                value = eachLine_split[9].strip()
                
                Freq = "0"
                if locus in FreqDict:
                    Freq = FreqDict[locus]
                else:
                    Freq = calculateFrequency(locus,allbam,junctionsbam,samtools,window)
                    FreqDict[locus] = Freq
                value += ":" + Freq + "\n"
                VariantLines += chr + "\t" + pos + "\t" + id + "\t" + ref + "\t" + alt + "\t" + qual + "\t" + filter + "\t" + info + "\t" + format + "\t" + value
            outputfile.write(Header + VariantLines)

    except IOError as ex:
        logger.exception(ex.strerror)
        exit(ex.errno)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", "--vcffile",
                        dest="vcf",
                        help="the sample vcf file",
                        required=True)
    parser.add_argument("-j", "--junc_bam",
                        dest="junctions",
                        help="junctions bam file",
                        required=True)
    parser.add_argument("-b", "--all_bam",
                        dest="bam",
                        help="all reads bam file",
                        required=True)
    parser.add_argument("-s", "--samtoolsFile",
                        dest="samtools",
                        help="path to samtools",
                        required=True)
    parser.add_argument("-o", "--freq_vcffile",
                        dest="output",
                        help="vcffile with Frequency of fusions supporting reads within a specified window",
                        required=True)
    parser.add_argument("-w", "--windwvalue",
                        dest="window",
                        help="window on each side of the breakpoint",
                        required=True)
    inpArgs = parser.parse_args()
    main(inpArgs)
