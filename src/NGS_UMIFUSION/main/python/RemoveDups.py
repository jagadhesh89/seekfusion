import argparse
import logging
from RemoveDuplicates import RemoveDups

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

"""
Input file is a sam file of binned reads to a gene. Output file should not contain equal to or more than Allowed copies 
of a sequence that share the following information
Maps to same gene
Mapping starts at same position in gene
Mapping Length is same
Cigar string is same
If these are same for say 5 reads, only 5 reads are maintained and the 6th occurence is tossed out. 
"""


def dup_removal(in_file, out_file, allowed_dups):
    with open(in_file, "r") as InputFileStream, open(out_file, "w") as OutputStream:
        try:
            logger.info("Reading non sequence deduped file {}".format(in_file))
            allowed_dups = int(allowed_dups)
            remove_obj = RemoveDups()
            remove_obj.remove(InputFileStream, OutputStream, int(allowed_dups))
        except Exception as exc:
            logger.exception(exc)
            exit(1)


def main(in_file, out_file, allowed_duplicates):
    dup_removal(in_file, out_file, allowed_duplicates)


if __name__ == '__main__':
    # parse input
    parser = argparse.ArgumentParser(description="Get dup removed fastas")
    parser.add_argument('-i', '--inFile', dest="input",
                        help="Binned sam file")
    parser.add_argument('-o', '--outFile', dest="output",
                        help="Output file of dup removed sam")
    parser.add_argument('-n', '--numofDups', dest="dupnum",
                        help="Max number of duplicates allowed")
    args = parser.parse_args()

    # pass to main
    main(args.input, args.output, args.dupnum)
