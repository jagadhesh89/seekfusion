import argparse
import logging
import os
import collections

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

def main(inp_args):
    process_report(inp_args.frame)



def process_report(frame):
    """
    This function removes these fields from the input file:
        IGV_link Fusion_Sequence In_COSMIC? COSMIC_Histology
    It also renames fields:
        "Spanning"   ------>   "Unique Reads"
        "Split"      ------>    "Total Reads"
    :param frame: <sample>.All_Fusions.xls or <sample>.In-Frame_Fusions.xls (outputs of identify_and_annotate_potential_fusions.sh
    from FUSION2VCF)
    :return: massaged input
    """
    try:
        with open(frame, "r") as frameFile:
            req_header = ""
            fusion_lines = ""
            line_count = 0
                    
            for each_line in frameFile:
                each_line_split = each_line.split("\t")

                if line_count == 0:
                    firstheader = each_line
                    print(firstheader.strip())
                    line_count += 1
                    continue

                if line_count == 1:
                    field_count = 0

                    for each_field in each_line_split:
                        if field_count == 3 or field_count == 4 or field_count == 12 or field_count == 13:
                            req_header = req_header
                        else:
                            if "Spanning" in each_field:
                                each_field = "Unique Reads"
                            if "Split" in each_field:
                                each_field = "Total Reads"
                            req_header = req_header + each_field + "\t"
                        field_count += 1

                    print(req_header.strip())
                    line_count += 1
                    req_header = ""
                    continue

                field_count = 0
                
                
                for each_field in each_line_split:
                    if field_count == 3 or field_count == 4 or field_count == 13 or field_count == 14:
                        fusion_lines = fusion_lines
                    else:
                        fusion_lines = fusion_lines + each_field + "\t"
                    field_count += 1
                    
                   
                print(fusion_lines.strip())
                fusion_lines = ""
                
                '''FusionDict = collections.OrderedDict()
                Gene1, Gene2 = process_gene(each_line_split)
                Gene1 = Gene1 + ":" + Tr_Gene1 + ":" + Exon_Gene1
                Gene2 = Gene2 + ":" + Tr_Gene2 + ":" + Exon_Gene2
                ChimericReference_Header = ">" + Gene1 + chimera_delimiter + Gene2
                ReqHeader = ChimericReference_Header
                if ChimericReference_Header not in FusionDict:
                    FusionDict[ChimericReference_Header] = 1
                else:
                    # This adds numbers for multiple entries
                    ReqHeader = ChimericReference_Header + count_delimiter + str(FusionDict[ChimericReference_Header])
                    FusionDict[ChimericReference_Header] += 1
                Sequence = each_line_split[4]
                LocationofBP_in_sequence = Sequence.find("-")
                BP_Pos = str(LocationofBP_in_sequence)    '''        
                

    except IOError as ex:
        logger.exception(ex.strerror)
        exit(ex.errno)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", "--frameFile",
                        dest="frame",
                        help="the frame file",
                        required=True)

    inpArgs = parser.parse_args()
    main(inpArgs)
