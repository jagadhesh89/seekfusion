import sys
import os
import argparse
import logging
import collections

IN_GENE_ONCE_NUMBER = 9999999


# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

# Example Gene Bed File
# ALK	chr2	29415640	30144477
# TFE3	chrX	48886242	48900990
# CCNB3	chrX	50027542	50094911
# SEPT14	chr7	55863605	55929689
# AFAP1	chr4	7765491	7873805
# AGBL4	chr1	48999844	50489468


def get_gene_bed_regions(gene_bed_file):
    """
    Returns a map of a bed file, keyed on GeneID with a string chr:start-end as the content
    :param gene_bed_file:
    :return: bedmap
    """
    GeneBedRegions = collections.OrderedDict()

    gene_bed_file = open(gene_bed_file, "r")
    for eachLine in gene_bed_file:
        if eachLine.startswith("#"):
            continue
        eachLine_split = eachLine.strip().split("\t")
        if len(eachLine_split) < 4:
            logger.warning("Bed line does not meet minimum number of columns {}.".format(eachLine))
            continue
        logger.debug(eachLine_split)

        key = eachLine_split[3].split(":")[0]
        value = eachLine_split[0]+":"+eachLine_split[1]+"-"+eachLine_split[2]

        # Test that start and end are integers

        if not eachLine_split[1].isdigit():
            logger.error("{} is not a valid start position in bed file.".format(eachLine_split[1]))
            exit(1)
        elif not eachLine_split[2].isdigit():
            logger.error("{} is not a valid end position in bed file.".format(eachLine_split[2]))
        elif key in GeneBedRegions:
            logger.error("Key {} with value {} is duplicate of {}".format(
                key,
                value,
                GeneBedRegions[key]
            ))
            exit(1)

        GeneBedRegions[key] = value
        logger.info("Parsed {} as {}".format(key, GeneBedRegions[key]))

    logger.info(GeneBedRegions)
    return GeneBedRegions


def check_regions(r_chr, cur_chr, rs, cs, re, ce):
    WithinFlag = 0
    if cur_chr.strip() in r_chr.strip():
        if cs < rs <= ce <= re:
            WithinFlag = 1
        if cs >= rs and ce <= re:
            WithinFlag = 1
        if rs <= cs <= re <= ce:
            WithinFlag = 1

    if WithinFlag:
        logger.info("Check Regions Hit: {} {} {} {} {} {} {}".format(r_chr, cur_chr, rs, cs, re, ce, WithinFlag))

    return WithinFlag


def main(config):
    """
    This code checks if the blat reads are within any known gene. We then check if the coordinates of the new hit are
    novel, if they are novel we increment the count stored for that read.

    Finally, we check to see if the number of unique blat hits on a read are >=2 and those reads are returned
    in the final filtered file.

    :param config: readblat configuration object
    :return:
    """
    NonFusionReads = collections.OrderedDict()
    GeneBedRegions = get_gene_bed_regions(config.bedfile)

    # Get the hits from blat that are there only within regions,
    # also get hits from blat that occur to two regions and not just one region.
    # This will yield only potential fusion reads

    ReadCounts = collections.OrderedDict()
    ReadRegion = collections.OrderedDict()
    TmpReads = collections.OrderedDict()
    TotalFusionReads = 0
    TotalNonFusionReads = 0

    # BLAT results in BLAST8 format (really Blast option 6)
    # 0 Query_id
    # 1 Subject_id
    # 2 %_identity
    # 3 alignment_length
    # 4 mismatches
    # 5 gap_openings
    # 6 query_start
    # 7 query_end
    # 8 subject_start
    # 9 subject_end
    # 10 e-value
    # bit_score
    #
    # eg.,
    # R0260303:423:000000000-B4PYT:1:1101:15256:14331:N:0:AGGCAGAGTAAGGA	chr7	\
    # 100.00	68	0	0	84	151	55219055	55218988	1.5e-31	134.0
    # R0260303:423:000000000-B4PYT:1:1101:15256:14332:N:0:AGGCAGAGTAAGGA	chr7	\
    # 100.00	70	0	0	29	98	55219056	55218987	8.8e-33	138.0

    try:
        with open(os.path.abspath(config.input), "r") as blat_result_file:
            for eachLine in blat_result_file:
                eachLine_split = eachLine.split("\t")
                ReadName = eachLine_split[0]

                subject_chromosome = eachLine_split[1]
                subject_start_position = eachLine_split[8]
                subject_end_position = eachLine_split[9]

                TmpReads[ReadName] = 1
                within_genes = 0
                for eachRegion in GeneBedRegions.keys():
                    Coordinates = GeneBedRegions[eachRegion]  # get chr:start-end on each geneid
                    Chromosome_Coordinate_Split = Coordinates.split(":")
                    Coordinates_split = Chromosome_Coordinate_Split[1].split("-")
                    # RChromosome = Chromosome_Coordinate_Split[0]
                    RChrStart = Coordinates_split[0]
                    RChrEnd = Coordinates_split[1]
                    if subject_start_position >= RChrStart and subject_end_position <= RChrEnd:
                        within_genes = 1
                        break

                if within_genes == 1:
                    if ReadName in ReadCounts.keys():
                        if ReadCounts[ReadName] == 1 or ReadCounts[ReadName] == IN_GENE_ONCE_NUMBER:
                            if ReadCounts[ReadName] != 1:
                                ReadCounts[ReadName] = 1
                            ReadCounts[ReadName] += 1
                    else:  # ReadName not seen in ReadCounts Keys
                        ReadCounts[ReadName] = IN_GENE_ONCE_NUMBER
                else:
                    if ReadName in ReadRegion.keys():
                        ExistingCoordinates = ReadRegion[ReadName]
                        ExistingCoordinates_split = ExistingCoordinates.split(":")
                        EChr = ExistingCoordinates_split[0]
                        Start_Stop_Split = ExistingCoordinates_split[1].split("-")
                        EChrStart = Start_Stop_Split[0]
                        EChrEnd = Start_Stop_Split[1]
                        CheckFlag_1 = check_regions(EChr, subject_chromosome, int(EChrStart),
                                                    int(subject_start_position), int(EChrEnd),
                                                    int(subject_end_position))
                        CheckFlag_2 = check_regions(subject_chromosome, EChr, int(subject_start_position),
                                                    int(EChrStart), int(subject_end_position), int(EChrEnd))

                        if CheckFlag_1 == 1 or CheckFlag_2 == 1:
                            continue
                        else:
                            ReadCounts[ReadName] += 1
                    else:
                        ReadRegion[ReadName] = subject_chromosome + ":" + subject_start_position + \
                                               "-" + subject_end_position
                        if ReadName not in ReadCounts.keys():
                            ReadCounts[ReadName] = 1
                        else:
                            if ReadCounts[ReadName] == IN_GENE_ONCE_NUMBER:
                                ReadCounts[ReadName] = 2
                            else:
                                ReadCounts[ReadName] += 1

                    for eachRead in ReadCounts:
                        Count = ReadCounts[eachRead]
                        if 1 < Count < IN_GENE_ONCE_NUMBER:
                            TotalFusionReads += 1
                        else:
                            NonFusionReads[eachRead] = 1
                            TotalNonFusionReads += 1

                # WithinGenes != 1

    except IOError as ex:
        logger.exception(ex.strerror)
        sys.exit(1)

    HeaderInNonFusionFlag = 0
    Header = ""

    try:
        with open(config.fasta, "r") as OriginalFastaFile, \
                open(config.outfile, "w") as FilteredFileToWrite:
            for eachFastaSeqLine in OriginalFastaFile:
                if '>' in eachFastaSeqLine[0]:
                    Header = eachFastaSeqLine.replace(">", "")
                    Header = Header.strip()
                    if Header in NonFusionReads.keys():
                        HeaderInNonFusionFlag = 1
                else:
                    if HeaderInNonFusionFlag == 1:
                        HeaderInNonFusionFlag = 0
                        Header = ""
                    else:
                        FilteredFileToWrite.write(">" + Header + "\n" + eachFastaSeqLine.strip() + "\n")
    except IOError as ex:
        logger.exception(ex.strerror)
        sys.exit(1)


def set_file_logging(l_file, dbg):
    """
    Set up file based logging handler
    :param l_file: file to direct logging output to
    :param dbg: boolean whether to log at debug level
    :return: None
    """

    if l_file:
        formatter = logging.Formatter('%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s')
        my_handler = logging.FileHandler(l_file, mode="w")

        if dbg:
            my_handler.setLevel(logging.DEBUG)
        else:
            my_handler.setLevel(logging.INFO)

        my_handler.setFormatter(formatter)
        logger.addHandler(my_handler)

    return


class Configuration:
    input = None
    bedfile = None
    outfile = None
    fasta = None
    logfile = None
    debug = False

    @staticmethod
    def validate_arguments(args):

        config = Configuration()

        config.input = args.input
        config.bedfile = args.bed
        config.outfile = args.outfile
        config.fasta = args.fasta

        if args.debug:
            config.debug = True

        if args.logfile:
            config.logfile = args.logfile
            set_file_logging(config.logfile, config.debug)

        return config


if __name__ == '__main__':

    usage = "python ReadBlat.py -i <Read_Blat_Result> -b <BEDFile> -f <query_fasta> -o <filtered fasta output>"
    parser = argparse.ArgumentParser(description='GSP Fusion Pipeline')
    parser.add_argument("-i", "--input", dest="input", required=True, help="The path to the Blat result file")
    parser.add_argument("-f", "--fasta", dest="fasta", required=True, help="fasta read file")
    parser.add_argument("-b", "--bed", dest="bed", required=True, help="Gene Bed File for the test")
    parser.add_argument("-o", "--outfile", dest="outfile", required=True, help="Filtered blat output file")
    parser.add_argument("-l", "--logfile", dest="logfile", help="File for logging output")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", help="extended logging")

    configuration = Configuration.validate_arguments(parser.parse_args())

    main(configuration)
