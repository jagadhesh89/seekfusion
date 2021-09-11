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


def generate_metric(filepath, sample_identifier, batch_name, run_name, sample_project):

    control_metrics = {}
    source = "BWAMEM"

    try:
        with open(filepath) as fusion_report_file:
            linecount = 0
            for eachLine in fusion_report_file:
                linecount += 1
                if linecount < 3:       # exclude two header lines
                    continue
                eachLine_split = eachLine.split("\t")
                if len(eachLine_split) < 3:
                    continue

                coordinates = eachLine_split[13] + "_" + eachLine_split[14] + "_" \
                    + eachLine_split[15] + "_" + eachLine_split[16]

                control_name = eachLine_split[0]
                if "chr1_1_chr2_1" in coordinates:
                    control_metrics[control_name] = eachLine_split[7] + "," + eachLine_split[8]
    except IOError as ex:
        logger.exception(ex.strerror)
        raise

    NegativeReads = 0
    NegativeTags = 0
    PositiveReads = 0
    PositiveTags = 0

    for each_control in control_metrics:
        metric_type = "I"
        reads_aligned = control_metrics[each_control].split(",")[1]
        molecular_tags = control_metrics[each_control].split(",")[0]
        
        if "GDC" in each_control.upper():
            NegativeReads += int(reads_aligned)
            NegativeTags += int(molecular_tags)
        else:
            PositiveReads += int(reads_aligned)
            PositiveTags += int(molecular_tags)
        total_string = "\t".join(
            [
                source,
                "sample.bwamem." + each_control + ".readsaligned.total",
                metric_type,
                reads_aligned,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
        )

        print(total_string)

        tags_string = "\t".join(
            [
                source,
                "sample.bwamem." + each_control + ".tagsaligned.total",
                metric_type,
                molecular_tags,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
        )

        print(tags_string)
    
    PositiveReads = str(PositiveReads)
    NegativeReads = str(NegativeReads)
    PositiveTags = str(PositiveTags)
    NegativeTags = str(NegativeTags)
    total_string = "\t".join(
            [
                source,
                "sample.bwamem.positiveControl.readsaligned.total",
                metric_type,
                PositiveReads,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
    )
    print(total_string)
    tags_string = "\t".join(
            [
                source,
                "sample.bwamem.positiveControl.tagsaligned.total",
                metric_type,
                PositiveTags,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
    )
    print(tags_string)
    
    total_string = "\t".join(
            [
                source,
                "sample.bwamem.negativeControl.readsaligned.total",
                metric_type,
                NegativeReads,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
    )
    print(total_string)
    tags_string = "\t".join(
            [
                source,
                "sample.bwamem.negativeControl.tagsaligned.total",
                metric_type,
                NegativeTags,
                sample_identifier,
                "sample",
                batch_name,
                "Batch",
                run_name,
                "run"
            ]
    )
    print(tags_string)

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UMIFUSION ROQCM Control Metric Collector')
    parser.add_argument("-i", "--input_tsv",
                        dest="tsv",
                        required=True,
                        help="a formatted _to_vcf.tsv")
    parser.add_argument("-s", "--sampleID",
                        dest="sampleID",
                        required=True,
                        help="the sample ID (N001-200ng)")
    parser.add_argument("-b", "--batchName",
                        dest="batchName",
                        required=True,
                        help="The Batch ID (051117)")
    parser.add_argument("-r", "--runName",
                        dest="runName",
                        required=True,
                        help="The run name / Run Dir Base (NGS71_51117_LIB022_IL018A_B4PYT)")
    parser.add_argument("-p", "--sampleproject",
                        dest="sampleProject",
                        required=True,
                        help="The sample project")
    args = parser.parse_args()
    generate_metric(args.tsv, args.sampleID, args.batchName, args.runName, args.sampleProject)
