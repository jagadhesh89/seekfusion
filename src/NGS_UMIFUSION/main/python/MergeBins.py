import argparse
import logging
import os
import sys


"""
Accepts a list of R1 and R2 files, or a single R1 and R2 file.
Reverse complements the R1(s) and append the R2s if they exist to either a _SNG.fa or _CMB.fa
    in the output path. 

INPUT:  
1) list of file paths in text format 
2) path where merged files should reside

USAGE:  python3 MergeBins.py -i binfile.txt -o outputPath
    or
        python3 MergeBins.py -r1 sample_R1.fa -r2 sample_R2.fa -o outputPath
        
"""


# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)


def set_file_logging(my_conf):
    """
    Adds logging to file if specified in configuration object
    :param my_conf:
    :return:
    """
    if my_conf.LogFile:
        formatter = logging.Formatter('%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s')
        my_handler = logging.FileHandler(my_conf.LogFile, mode="w")

        if my_conf.Debug:
            my_handler.setLevel(logging.DEBUG)
        else:
            my_handler.setLevel(logging.INFO)

        my_handler.setFormatter(formatter)
        logger.addHandler(my_handler)

    return


def get_bin_ext(my_file):
    filename = my_file.split(os.sep)[-1]
    basename = filename.split(".")[-2]
    m_bin = str.join("_", basename.split("_")[0:-1])
    my_ext = basename.split("_")[-1]
    return m_bin, my_ext


def rev_comp(seq):
    return seq.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1]


def combine_r1r2(my_r1, my_r2, m_bin, m_args):

    extension = ""

    # if my_r1 and my_r2:  # both files available produce combined fasta
    #     extension = "_CMB"
    # else:
    #     extension = "_SNG"

    logger.info("{} {} {},{}".format(m_bin, extension, my_r1, my_r2))

    out_file = m_args.outpath + os.sep + m_bin + extension + ".fa"
    try:
        with open(out_file, "w") as out:
            # Write the reverse complement of the R1 file if it exists to outfile
            if my_r1:
                with open(my_r1, "r") as infile:
                    for line in infile:
                        line = line.strip()
                        if line.startswith('>'):
                            out.write(line+"\n")
                        elif line:
                            out.write(rev_comp(line.strip())+"\n")
            # and then stream the R2 file verbatim
            if my_r2:
                with open(my_r2, "r") as infile:
                    for line in infile:
                        out.write(line)
    except IOError as exc:
        logger.exception(exc.strerror)
        sys.exit(1)
    # close outfile
    return out_file


def process_serial_merge(m_args):
    """
    If provided a file of "sampleName\tbinName\tR1.fa\tR2.fa" process all rows serially and produce
    merged output
    :param m_args:
    :return: list of files created
    """

    file_array = []
    outlist = []

    try:
        with open(m_args.input, "r") as input_file:
            for my_line in input_file:
                file_array.append(my_line.strip().split('\t'))
    except IOError as exc:
        logger.exception(exc.strerror)
    # For each bin, we determine whether any reads have been put in R1 or R2 sub-bins
    # and then determine what the extension of the merged file should be.

    for row in file_array:
        m_bin = row[0]+"_"+row[1]
        if row[2] == "null" or row[2].strip() == "":
            logger.warning("Column 3 in file list is empty for {},{}".format(row[0], row[1]))
            R1 = None
        else:
            R1 = row[2]

        if row[3] == "null" or row[3].strip() == "":
            R2 = None
            logger.warning("Column 4 in file list is empty for {},{}".format(row[0], row[1]))
        else:
            R2 = row[3]

        if not R1 and not R2:  # neither file available, skip -- how did this happen
            logger.warning("No files found for {}".format(m_bin))
            continue
        else:
            outlist.append(combine_r1r2(R1, R2, m_bin, m_args))

    return outlist


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='GSP Fusion Pipeline')
    parser.add_argument("-i", "--input", dest="input",
                        help="serially process a tab-delimited file containing a list of bin" +
                             "_names, R1 and R2 file paths (optional)")
    parser.add_argument("-o", "--output", dest="outpath",
                        help="The path to store output files in")
    parser.add_argument("-r1", dest="R1", help="The R1 fasta file or None")
    parser.add_argument("-r2", dest="R2", help="The R2 fasta file or None")
    parser.add_argument("-t", "--textfile", dest="TextFile",
                        help="if specified, directs paths of files created to this file")
    parser.add_argument("-l", "--logfile", dest="LogFile", help="File to direct logging to.")
    parser.add_argument("-d", "--debug", dest="Debug", action="store_true", help="Enable debug level logging.")

    args = parser.parse_args()

    # Todo: validate_args(args)

    set_file_logging(args)

    if not args.outpath:
        args.outpath = os.getcwd()

    if args.R1:
        if args.R1.strip() == "null":
            args.R1 = None

    if args.R2:
        if args.R2.strip() == "null":
            args.R2 = None

    # If we are processing a list of files given in a tab delimited file
    if args.input:
        file_list = process_serial_merge(args)
        if args.TextFile:  # we have specified a file to direct the files created to
            try:
                with open(args.TextFile, "w") as text_out:
                    for outfile in file_list:
                        text_out.write(outfile+"\n")
            except IOError as ex:
                logger.exception(ex.strerror)

        for outfile in file_list:
            logger.info("Output to {}".format(outfile))
            print(outfile)

    elif args.R1 or args.R2:
            if args.R1:
                my_bin, ext = get_bin_ext(args.R1)
            elif args.R2:
                my_bin, ext = get_bin_ext(args.R2)
            else:
                logger.error("")

            outfile = combine_r1r2(args.R1, args.R2, my_bin, args)
            logger.info("Output to {}".format(outfile))
            if args.TextFile:  # we have specified a file to direct the files created to
                try:
                    with open(args.TextFile, "w") as text_out:
                        text_out.write(outfile+"\n")
                except IOError as ex:
                    logger.exception(ex.strerror)
            print(outfile)
    else:
        logger.warning("Nothing to do.")
