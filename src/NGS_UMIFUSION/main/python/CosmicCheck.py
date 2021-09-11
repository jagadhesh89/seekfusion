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
    all_fusions_dict, header = process_all_fusions(os.path.abspath(input_args.allfusion))
    cosmic_fusion_dict = process_cosmic_fusions(os.path.abspath(input_args.cosmic))
    process_final_output(all_fusions_dict,
                         cosmic_fusion_dict,
                         os.path.abspath(input_args.inframe),
                         header,
                         input_args.outpath)


def process_final_output(all_fusions_dict, cosmic_fusion_dict, inframe_file, header, outpath):
    """
        It combines uniq entries in both <sample>.All_Fusions.xls
        and <sample>.In-Frame_Fusions.xls, and then label each entry as "EXPERIENCE_DB" or "NOT_EX_DB"

    :param all_fusions_dict:
    :param cosmic_fusion_dict:
    :param inframe_file:
    :param header:
    :param outpath:
    :return:
    """
    with open(outpath, "w") as final_report:
        final_report.write(header)

        for eachFusion in all_fusions_dict:
            each_fusion_reqd = eachFusion.split(":")[0]
            if each_fusion_reqd in cosmic_fusion_dict:
                final_report.write(all_fusions_dict[eachFusion].strip() + "\tEXPERIENCE_DB\n")

        inframe_file_stream = open(inframe_file, "r")
        line_count = 0
        for eachLine in inframe_file_stream:
            line_count += 1
            if line_count < 3:
                continue
            final_report.write(eachLine.strip() + "\tNOT_EX_DB\n")


def process_cosmic_fusions(cosmic_file):
    """

    :param cosmic_file: CosmicFusionExport.tsv
        KMT2A	ARHGEF12
        NFATC1	EWSR1
    :return: dictionary
        {'NFATC1~EWSR1': 1, 'ARHGEF12~KMT2A': 1, 'EWSR1~NFATC1': 1, 'KMT2A~ARHGEF12': 1}
    """
    with open(cosmic_file, "r") as cosmic_file:
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


def process_all_fusions(all_fusion_file):
    """

    :param all_fusion_file:  <sample>.All_Fusions.xls
        General_Information					Exon_Information			Read_Information		Additional_Information						Fusion_coordinates
        5'-3'Gene_Partners	Fusion_Location	Frame_Status	5'_Exon_Annotation	5'_Frame	3'_Exon_Annotation	3'_Frame	Unique Reads	Total Reads	Fusion_Annotation	Human_Tissues	Average_Expression	Tissue_Name	Chr_5'	Coordinate_5'	Chr_3'	Coordinate_3'	Distance_between_breakpoints
        nil~HEY1	Intron-Exon_Body	Promoter_Swap	NA	NA	-|Body_E4|HEY1|NM_001040708	2	100	100	Potential_Fusion-Candidate	NO	-	-	chr10100920601	chr8	80678937	-
    :return: all_fusions_dict, header
            (OrderedDict([('nil~HEY1:chr10:100920601:chr8:80678937NA-|Body_E4|HEY1|NM_001040708', 'nil~HEY1\tIntron-Exon_Body\tPromoter_Swap\tNA\tNA\t-|Body_E4|HEY1|NM_001040708\t2\t100\t100\tPotential_Fusion-Candidate\tNO\t-\t-\tchr10\t100920601\tchr8\t80678937\t-\n')])
            "General_Information\t\t\t\t\tExon_Information\t\t\t\tRead_Information\t\tAdditional_Information\t\t\t\t\t\tFusion_coordinates\n5'-3'Gene_Partners\tFusion_Location\tFrame_Status\t5'_Exon_Annotation\t5'_Frame\t3'_Exon_Annotation\t3'_Frame\tUnique Reads\tTotal Reads\tFusion_Annotation\tHuman_Tissues\tAverage_Expression\tTissue_Name\tChr_5'\tCoordinate_5'\tChr_3'\tCoordinate_3'\tDistance_between_breakpoints\tExperienceDB_Status\n"
    """
    with open(all_fusion_file, "r") as all_fusion_file:
        line_count = 0
        all_fusions_dict = collections.OrderedDict()
        header = ""
        for eachLine in all_fusion_file:
            line_count += 1
            if line_count < 3:
                if line_count == 2:
                    # Add ExperienceDB column to header row 2
                    header = header + eachLine.strip('\n') + "\tExperienceDB_Status\n"
                else:
                    header = header + eachLine
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
            all_fusions_dict[fusion] = eachLine
    return all_fusions_dict, header


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
