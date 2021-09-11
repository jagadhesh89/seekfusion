import sys
import argparse
import logging
import collections

"""
This programs filters reports for preferred transcripts and Exon1-2 events

******* Preferred transcript logic ************
Logic is to see if genes have preferred transcripts in the transcript file
If preferred transcript is listed in transcript file, get lines from fusion report that are only 
having preferred transcript and pass it to filtered report
If preferred transcript is not listed in the transcript file, pass the fusion line to filtered report

****** Same gene filtering logic **************
Some lines in fusion report have same gene events
Example: PTPRZ1-PTPRZ1    Exon-Exon_boundary    In-Frame    +|End_E1|PTPRZ1|NM_001206838    
2    +|Start_E2|PTPRZ1|NM_001206838    3    34269    67246    Read-Through    -    -    -    
chr7    121513611    chr7    121568210    54599
These are exon splicing events and not exactly fusion events. 
Check for lines where there are same genes and exon differs by 1.
In above example it is E1 and E2. Events like these have to be filtered, if it is E1, E3 leave it behind.

Usage: python ReportFilter.py -i <inFrameDir>

"""

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

gene_delimiter = '~'


def main(input_args):
    preferred_transcripts = get_preferred_transcripts(input_args.pref)
    allowed_tr_vars = get_allowed_tr_variants(input_args.trvars)
    process_final_reports(input_args.ifile, preferred_transcripts, input_args.ofile, allowed_tr_vars)


def reduce_next_exon_splicing(final_report_file, allowed_tr_vars):
    """
    ****** Same gene filtering logic **************
    Some lines in fusion report have same gene events
    Example: PTPRZ1-PTPRZ1    Exon-Exon_boundary    In-Frame    +|End_E1|PTPRZ1|NM_001206838
    2    +|Start_E2|PTPRZ1|NM_001206838    3    34269    67246    Read-Through    -    -    -    chr7
    121513611    chr7    121568210    54599
    These are exon splicing events and not exactly fusion events.
    Check for lines where there are same genes and exon differs by 1.
    In above example it is E1 and E2. Events like these have to be filtered,
    if it is E1, E3 leave it behind.

    :param allowed_tr_vars:
    :param final_report_file:
    :return:
    """
    line_count = 0
    lines_req = ""
    for eachLine in final_report_file:
        # Example line:
        # KIAA1549-BRAF    Exon-Exon_boundary    In-Frame    -|End_E15|KIAA1549|NM_001164665    \
        # 1    -|Start_E9|BRAF|NM_004333    2    271    523    Fusion-Candidate    -    -    -    \
        # chr7    138552721    chr7    140487384    1934663
        line_count += 1
        # Skip first two lines that are header
        if line_count < 3:
            lines_req = lines_req + eachLine
            continue

        each_line_split = eachLine.split("\t")
        if len(each_line_split) < 3:
            continue

        if "Homologs" in eachLine:
            continue

        gene1, gene2 = process_gene(each_line_split)

        if gene1 == gene2:
            # check if chr are  same
            if each_line_split[13] != each_line_split[15]:
                continue
            break_point = each_line_split[13] + ":" + each_line_split[14] + "-" + each_line_split[16].strip()
            if break_point not in allowed_tr_vars:
                continue
            # Non canonical fusion with no annotation of transcript
            # Example: QKI-RAF1    Intron-Exon_boundary    Promoter_Swap    NA    NA    -|Start_E7|RAF1|NM_002880
            #     1    619    1401    -    -    -    -    chr6    163836270    chr3    12645788    151190482
            # The annotation says NA
            if "NA" == each_line_split[3] or "NA" == each_line_split[5]:
                lines_req = lines_req + eachLine
                continue

                # Get Exon numbers
            exon_gene1 = int(each_line_split[3].split("|")[1].split("_")[1].replace("E", ""))
            exon_gene2 = int(each_line_split[5].split("|")[1].split("_")[1].replace("E", ""))

            # Get difference between exon numbers. If it is same gene and exon 12-13,
            # difference will be 1 and we do not require this line.
            if abs(exon_gene1 - exon_gene2) < 2:
                continue
            else:
                lines_req = lines_req + eachLine
        else:
            lines_req = lines_req + eachLine
    return lines_req


def get_allowed_tr_variants(tr_vars_file):
    """

    :param tr_vars_file:  transcript_variants.txt
        GLI1	GLI1	chr12	57854337	57858456
        GLI1	GLI1	chr12	57857574	57858485
    :return:
        OrderedDict([('chr12:57854337-57858456', 'GLI1-GLI1'), ('chr12:57857574-57858485', 'GLI1-GLI1')])
    """
    try:
        with open(tr_vars_file, "r") as AllowedTranscriptVarFile:
            allowed_tr_vars = collections.OrderedDict()
            for eachLine in AllowedTranscriptVarFile:
                each_line_split = eachLine.split("\t")
                tr_var = each_line_split[0] + "-" + each_line_split[1]
                break_point = each_line_split[2] + ":" + each_line_split[3] + "-" + each_line_split[4].strip()
                allowed_tr_vars[break_point] = tr_var

    except IOError as ex:
        logger.exception(ex.strerror)
        sys.exit(1)

    return allowed_tr_vars


def get_preferred_transcripts(pref_file):
    """

    :param pref_file:  ordered_service/pipelines/umifusion/transcripts.txt
        NRF1	NM_001293163
        ATG7	NM_006395
        EGFR	NM_005228

    :return:
        OrderedDict([('NRF1', 'NM_001293163'), ('ATG7', 'NM_006395'), ('EGFR', 'NM_005228')])

    """
    try:
        with open(pref_file, "r") as PrefTranscriptFile:
            pref_transcripts_dict = collections.OrderedDict()
            for eachLine in PrefTranscriptFile:
                each_line_split = eachLine.split("\t")
                if len(each_line_split) > 1:
                    gene = each_line_split[0]
                    transcript = each_line_split[1].strip()
                    pref_transcripts_dict[gene] = transcript

    except IOError as ex:
        logger.exception(ex.strerror)
        sys.exit(1)

    return pref_transcripts_dict


def process_gene(eachline_split):
    """

    :param eachline_split:
        ['NFIB~GLI1', 'Exon_boundary-Exon_Body', 'Promoter_Swap', '-|End_E8|NFIB|NM_005596', '1',
        '+|Body_E2|GLI1|NM_001160045', 'In_Untranslated_Region', '100', '100', 'Fusion-Candidate', 'NO', '--', 'chr9',
        '14120439', 'chr12', '57858612', '-', 'NOT_EX_DB']
    :return:
        ('NFIB', 'GLI1')
    """
    # Short circuit evaluation if we have a proper delimiter in this field
    if gene_delimiter in eachline_split[0]:
        return eachline_split[0].split(gene_delimiter)[0], eachline_split[0].split(gene_delimiter)[1]
    else:
        raise RuntimeError("Delimiter {} not found in {}.".format(gene_delimiter, eachline_split[0]))


# noinspection DuplicatedCode
def select_preferred_transcript(fusion_lines, preferred_transcripts):
    """
    ******* Preferred transcript logic ************
    Logic is to see if genes have preferred transcripts in the transcript file
    If preferred transcript is listed in transcript file, get lines from fusion report that are only having preferred
    transcript and pass it to filtered report

    If preferred transcript is not listed in the transcript file, pass the fusion line to filtered report
    """

    fusion_lines_split = fusion_lines.split("\n")
    line_count = 0
    lines_req = ""
    preferred_dict = collections.OrderedDict()
    not_preferred_dict = collections.OrderedDict()
    for eachLine in fusion_lines_split:
        line_count += 1
        if line_count < 3:
            lines_req = lines_req + eachLine + "\n"
            continue
        each_line_split = eachLine.split("\t")
        if len(each_line_split) < 3:
            continue
        # Example line:
        # KIAA1549~BRAF    Exon-Exon_boundary    In-Frame    -|End_E15|KIAA1549|NM_001164665    1    -
        # |Start_E9|BRAF|NM_004333    2    271    523    Fusion-Candidate    -    -    -    chr7
        # 138552721    chr7    140487384    1934663

        gene1, gene2 = process_gene(each_line_split)

        # 0 FGFR1~FGFR1
        # 1 Exon_boundary-Exon_Body
        # 2 Exon_to_Intron_or_Intergenic_Fusion
        # 3 -|End_E3|FGFR1|NM_001174066
        # 4 2
        # 5 NA
        # 6 NA
        # 7 100
        # 8 100
        # 9 Same_Gene
        # 10 NO
        # 11 -
        # 12 -
        # 13 chr11
        # 14 2660642
        # 15 chr8
        # 16 38285881\
        # 17 -       \
        # 18 EXPERIENCE_DB

        # eg., chr11:2660642-chr8:38285881
        bps = each_line_split[13] + ":" + each_line_split[14] + "-" + each_line_split[15] + ":" + each_line_split[16]

        # Non canonical fusion with no annotation of transcript
        # Example: QKI-RAF1    Intron-Exon_boundary    Promoter_Swap    NA    NA
        # -|Start_E7|RAF1|NM_002880    1    619    1401    -    -    -    -
        # chr6    163836270    chr3    12645788    151190482
        # The annotation says NA

        if len(each_line_split[3]) < 3 or len(each_line_split[5]) < 3:
            if gene1 + "-" + gene2 in not_preferred_dict:
                not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                    not_preferred_dict[gene1 + "-" + gene2] + ";" + eachLine + "\n"
            else:
                not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"
            continue

        # Get transcripts from the line for gene1 and gene2
        tr_gene1 = each_line_split[3].split("|")[3]
        tr_gene2 = each_line_split[5].split("|")[3]

        # Maintain dictionary for events that have preferred transcript and events that do not. Key is Gene
        if gene1 in preferred_transcripts or gene2 in preferred_transcripts:

            # One of the genes have preferred transcripts
            if gene1 in preferred_transcripts and gene2 not in preferred_transcripts:
                pref_transcript_gene1 = preferred_transcripts[gene1]
                if tr_gene1 == pref_transcript_gene1:
                    if gene1 + "-" + gene2 + "-" + bps in preferred_dict:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"
                else:
                    if gene1 + "-" + gene2 in not_preferred_dict:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"

            # One of the genes has preferred transcripts
            if gene2 in preferred_transcripts and gene1 not in preferred_transcripts:
                pref_transcript_gene2 = preferred_transcripts[gene2]
                if tr_gene2 == pref_transcript_gene2:
                    if gene1 + "-" + gene2 + "-" + bps in preferred_dict:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"
                else:
                    if gene1 + "-" + gene2 in not_preferred_dict:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"

                        # Both genes have preferred transcripts
            if gene1 in preferred_transcripts and gene2 in preferred_transcripts:
                pref_transcript_gene1 = preferred_transcripts[gene1]
                pref_transcript_gene2 = preferred_transcripts[gene2]
                if tr_gene1 == pref_transcript_gene1 and tr_gene2 == pref_transcript_gene2:
                    if gene1 + "-" + gene2 + "-" + bps in preferred_dict:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"
                else:
                    if gene1 + "-" + gene2 + "-" + bps in not_preferred_dict:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                            not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
                    else:
                        not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"

        # If neither gene has preferred transcripts
        if gene1 not in preferred_transcripts and gene2 not in preferred_transcripts:
            if gene1 + "-" + gene2 + "-" + bps in not_preferred_dict:
                not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = \
                    not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] + ";" + eachLine + "\n"
            else:
                not_preferred_dict[gene1 + "-" + gene2 + "-" + bps] = eachLine + "\n"
            continue

    # All preferred transcript fusion lines need to go to filtered report
    for eachFusion in preferred_dict:
        if ";" in preferred_dict[eachFusion]:
            fusions_split = preferred_dict[eachFusion].split(";")
            for each_hit in fusions_split:
                # Remove column 18
                # each_hit = each_hit.replace("\tEXPERIENCE_DB", "").replace("\tNOT_EX_DB", "")
                if each_hit not in lines_req:
                    lines_req = lines_req + each_hit
        else:
            lines_req = lines_req + preferred_dict[eachFusion]

    # Fusion lines in not_preferred_dict that are NOT present in preferred_dict need to go to filtered report if
    # satisfying certain criteria
    for eachFusion in not_preferred_dict:
        if eachFusion not in preferred_dict:
            # Check if transcripts are not NA, dont print not preferred transcripts, if NA let it pass through
            if not_preferred_dict[eachFusion].split("\t")[3] != "NA" \
                    and not_preferred_dict[eachFusion].split("\t")[5] != "NA":
                genes = eachFusion.split("-")[0] + "-" + eachFusion.split("-")[1]
                found_flag = 0
                for eachPrFusion in preferred_dict:
                    if genes in eachPrFusion:
                        found_flag = 1
                        break
                if found_flag == 1:
                    continue

            if ";" in not_preferred_dict[eachFusion]:
                fusions_split = not_preferred_dict[eachFusion].split(";")
                for each_hit in fusions_split:
                    lines_req = lines_req + each_hit  # .replace("\tEXPERIENCE_DB", "").replace("\tNOT_EX_DB", "")
            else:
                lines_req = lines_req + \
                           not_preferred_dict[eachFusion]  # .replace("\tEXPERIENCE_DB", "").replace("\tNOT_EX_DB", "")

    return lines_req


def process_final_reports(input_file, preferred_transcripts, output_file, allowed_tr_vars):
    # iterate through each sample directory in input directory and look for
    # FinalReport.tsv and create Filtered report based off that
    try:
        with open(input_file, "r") as FinalReportFile:
            lines_req = reduce_next_exon_splicing(FinalReportFile, allowed_tr_vars)
            lines_req = select_preferred_transcript(lines_req, preferred_transcripts)
        with open(output_file, "w") as NewFile:
            NewFile.write(lines_req)
    except IOError as ioerr:
        logger.error(ioerr.strerror)
        exit(1)


if __name__ == '__main__':
    usage = "python ReportFilter.py -i <report_file> -p <preferred_file> -o <output_file>"
    parser = argparse.ArgumentParser(description='GSP Fusion Pipeline')
    parser.add_argument("-i", "--input", dest="ifile",
                        required=True, help="The path to the input \"Final_Report\"")
    parser.add_argument("-o", "--output", dest="ofile",
                        required=True,
                        help="the output filtered file")
    parser.add_argument("-p", "--prefTranscripts", dest="pref",
                        required=True, help="File containing preferred transcripts")
    parser.add_argument("-t", "--transcriptvariants", dest="trvars",
                        required=True, help="File containing transcript variants allowed with breakpoints")
    inpArgs = parser.parse_args()
    main(inpArgs)
