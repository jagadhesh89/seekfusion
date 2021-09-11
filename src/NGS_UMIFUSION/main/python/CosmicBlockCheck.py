import os
import argparse
import collections
from enum import IntEnum

#######################################################################################################
'''This program filters False Positives and produces final report

Usage: python CosmicCheck.py -i <AllFusionsFile> -f <inFrameFile> -c <cosmicFile>

'''

#######################################################################################################

gene_delimiter = '~'
blockword = 'BLACKLIST'


class AllFusionCols(IntEnum):
    P5_P3GENE_PARTNERS = 0
    FUSION_LOCATION = 1
    FRAME_STATUS = 2
    P5_EXON_ANNOTATION = 3
    P5_FRAME = 4
    P3_EXON_ANNOTATION = 5
    P3_FRAME = 6
    UNIQUE_READS = 7
    TOTAL_READS = 8
    FUSION_ANNOTATION = 9
    HUMAN_TISSUES = 10
    AVERAGE_EXPRESSION = 11
    TISSUE_NAME = 12
    CHR_P5 = 13
    COORDINATE_P5 = 14
    CHR_P3 = 15
    COORDINATE_P3 = 16
    DISTANCE_BETWEEN_BREAKPOINTS = 17


def main(input_args):
    cosmic_fusion_dict = process_cosmic_fusions(os.path.abspath(input_args.cosmic))
    process_final_output(input_args.allfusion,
                         cosmic_fusion_dict,
                         os.path.abspath(input_args.inframe),
                         input_args.outpath)


def process_final_output(all_fusions_file, cosmic_fusion_dict, inframe_file, outpath):
    with open(outpath, "w") as final_report:

        written_fusion = {}
        
        with open(all_fusions_file, "r") as all_file_stream:
            line_count = 0
            header = ""

            for eachLine in all_file_stream:
                line_count += 1
                if line_count < 3:
                    if line_count == 2:
                        # Add ExperienceDB column to header row 2
                        header = header + eachLine.strip('\n') + "\tExperienceDB_Status\n"
                    else:
                        header = header + eachLine
                    continue
                if line_count == 3:
                    final_report.write(header)
                if blockword in eachLine:
                        continue

                if "Fused_End-to-End" in eachLine or "Fused_Start-to-Start" in eachLine:
                    continue

                each_line_split = eachLine.split("\t")

                # make each fusion Unique according to annotation example -
                # EWSR1-CREB3L1:chr22:29684775:chr11:46332668+|End_E8|EWSR1|NM_001163285+|Body_E5|CREB3L1|NM_052854
                fusion = "{0}:{1}:{2}:{3}:{4}{5}{6}".format(each_line_split[AllFusionCols.P5_P3GENE_PARTNERS].strip(),
                                                            each_line_split[AllFusionCols.CHR_P5].strip(),
                                                            each_line_split[AllFusionCols.COORDINATE_P5].strip(),
                                                            each_line_split[AllFusionCols.CHR_P3].strip(),
                                                            each_line_split[AllFusionCols.COORDINATE_P3].strip(),
                                                            each_line_split[AllFusionCols.P5_EXON_ANNOTATION].strip(),
                                                            each_line_split[AllFusionCols.P3_EXON_ANNOTATION].strip())

                each_fusion_reqd = fusion.split(":")[0]
                if each_fusion_reqd in cosmic_fusion_dict:
                    final_report.write(eachLine.strip() + "\tEXPERIENCE_DB\n")
                    written_fusion[fusion] = 1


        with open(inframe_file, "r") as inframe_file_stream:
            line_count = 0
            for eachLine in inframe_file_stream:
                line_count += 1
                if line_count < 3:
                    continue
                if blockword in eachLine:
                    continue
                if "Fused_End-to-End" in eachLine or "Fused_Start-to-Start" in eachLine:
                    continue
                each_line_split = eachLine.split("\t")
                # make each fusion Unique according to annotation example -
                # EWSR1-CREB3L1:chr22:29684775:chr11:46332668+|End_E8|EWSR1|NM_001163285+|Body_E5|CREB3L1|NM_052854
                fusion = "{0}:{1}:{2}:{3}:{4}{5}{6}".format(each_line_split[AllFusionCols.P5_P3GENE_PARTNERS].strip(),
                                                            each_line_split[AllFusionCols.CHR_P5].strip(),
                                                            each_line_split[AllFusionCols.COORDINATE_P5].strip(),
                                                            each_line_split[AllFusionCols.CHR_P3].strip(),
                                                            each_line_split[AllFusionCols.COORDINATE_P3].strip(),
                                                            each_line_split[AllFusionCols.P5_EXON_ANNOTATION].strip(),
                                                            each_line_split[AllFusionCols.P3_EXON_ANNOTATION].strip())
                #IF fusion (exact 5'chr:5'bp - 3'chr:3'bp is already printed by the all fusions iteration do not print it here
                if fusion not in written_fusion:
                    final_report.write(eachLine.strip() + "\tNOT_EX_DB\n")

        

def process_cosmic_fusions(cosmic_file):
    cosmic_file = open(cosmic_file, "r")
    cosmic_dict = {}
    for each_line in cosmic_file:
        each_line_split = each_line.split("\t")
        if len(each_line_split) < 1:
            continue
        gene1 = each_line_split[0].strip()
        gene2 = each_line_split[1].strip()
        fusion_str = gene1 + gene_delimiter + gene2
        cosmic_dict[fusion_str] = 1
        fusion_str = gene2 + gene_delimiter + gene1
        cosmic_dict[fusion_str] = 1
    return cosmic_dict


if __name__ == '__main__':
    usage = "python CosmicCheck.py -i <AllFusionsFile> -f <inFrameFile> -c <cosmicFile>"
    parser = argparse.ArgumentParser(description='GSP Fusion Pipeline')

    parser.add_argument("-i", "--FusionFile",
                        dest="allfusion",
                        required=True,
                        help="The path to the all fusion file")
    parser.add_argument("-f", "--InFrameFile",
                        dest="inframe",
                        required=True,
                        help="The path to the inframe file")
    parser.add_argument("-c", "--CosmicFile",
                        dest="cosmic",
                        required=True,
                        help="The path to the cosmic file")
    parser.add_argument("-o", "--outputFile",
                        dest="outpath",
                        required=True,
                        help="Path/Filename to send tab-delimited report to")
    inpArgs = parser.parse_args()
    main(inpArgs)
