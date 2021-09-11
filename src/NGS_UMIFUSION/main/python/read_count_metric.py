import argparse
import logging

"""
This program returns a formatted ROQCM metric row containing read count metrics for a given merged fasta file.

INPUT:  
1) Fastq file(s)

USAGE: python read_count_metric.py -i merged_R1R2.fa 
"""

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)


def generate_metric(filepath, sample_identifier, primer_bin, batch_name, run_name, source):

    try:
        with open(filepath, "r") as FastaFile:
            linecount = sum(1 for line in FastaFile)
        total_reads = int(float(linecount)/float(2))

    except IOError as exc:
        logger.exception(exc.strerror)
        raise

    metric_string = "\t".join([
        source,
        "sample.primer_"+primer_bin+"_reads.count",
        "I",
        str(total_reads),
        sample_identifier,
        "sample",
        batch_name,
        "Batch",
        run_name,
        "run"
    ])
    return metric_string

# Source+"\t"+
# "sample.primer_"+
# eachPrimer+"_reads.count\t"+
# Metrictype+"\t"+
# Reads+"\t"+
# SampleID+
# "\tsample\t"+
# BatchName+
# "\tBatch\t"+
# RunName+
# "\trun\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ROQCM ReadCount Collector')
    parser.add_argument("-i", "--inputFasta",
                        dest="fasta",
                        required=True,
                        help="A merged R1/R2 fasta file")
    parser.add_argument("-s", "--sampleID",
                        dest="sampleID",
                        required=True,
                        help="the sample ID (N001-200ng)")
    parser.add_argument("-b", "--batchName",
                        dest="batchName",
                        required=True,
                        help="The Batch ID (051117)")

    parser.add_argument("-p", "--primerName",
                        dest="primerName",
                        required=True,
                        help="The primer ID (EGFR_34)")
    parser.add_argument("-r", "--runName",
                        dest="runName",
                        required=True,
                        help="The run name (NGS71_51117_LIB022_IL018A_B4PYT)")
    parser.add_argument("-S", "--SOURCE",
                        dest="source",
                        required=True,
                        help="The ROQCM Source Identifier (ie., UMIFUSION)")

    args = parser.parse_args()

    print(
        generate_metric(
            args.fasta, args.sampleID, args.primerName, args.batchName, args.runName, args.source
        )
    )
