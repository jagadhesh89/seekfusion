import os
import argparse
import logging
import collections


# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)


class ConfigClass:
    BlatResultFile = None
    Output = None
    Logfile = None

    @staticmethod
    def validate(m_args):

        logger.info(m_args)
        retclass = ConfigClass()
        retclass.BlatResultFile = m_args.input
        retclass.Output = m_args.output
        retclass.genebed = m_args.genebed
        retclass.gene = m_args.gene
        retclass.unique_bases_threshold = m_args.unique_bases_threshold
        return retclass


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


def get_known_genes(gene_bedfile):
    """ Just reads a bed file with gene annotations """
    KnownGenes = collections.OrderedDict()
    try:
        with open(gene_bedfile, "r") as gene_bedfile:
            logger.info("Reading gene bedfile {}".format(gene_bedfile))
            for eachLine in gene_bedfile:
                if len(eachLine) <= 2:
                    continue
                eachLine_split = eachLine.strip().split("\t")
                Chromosome = eachLine_split[0]
                ChrStart = eachLine_split[1]
                ChrEnd = eachLine_split[2]
                Gene = eachLine_split[3].split(":")[0]
                KnownGenes[Gene] = Chromosome + ":" + ChrStart + "-" + ChrEnd
    except IOError as ioexception:
        logger.exception(ioexception.strerror)
        exit(1)

    #logger.info("KG:{}".format(KnownGenes))
    return KnownGenes


def main(input_arguments):
    """
    At this point, we've gotten back results from the blat jobs on all the assembled cap3 contigs
    We read the Ensembl and Refseq references

    Creates two separate exon coordinate hashes,


    :param input_arguments:
    :return:
    """
    # Handle contig blatting
    KnownGenes = get_known_genes(input_arguments.genebed)
    
    FilterBlatResults(input_arguments.BlatResultFile,input_arguments.Output,KnownGenes,input_arguments.gene, input_arguments.unique_bases_threshold)
    #blat_handler(input_arguments.BlatResultFile, input_arguments.Output, ExonCoord, EnsemblCoord)


def check_within_gene_bed(m_cur_chr, m_cur_chr_start, m_cur_chr_end, m_known_genes, m_genereq):
    WithinFlag = 0
    ReqGene = ""
    for eachGene in m_known_genes:
        ChrCoordinates_Split = m_known_genes[eachGene].split(":")
        if eachGene.strip().upper() != m_genereq.strip().upper():
            continue
        Chromosome = ChrCoordinates_Split[0]
        Coordinates_Split = ChrCoordinates_Split[1].split("-")
        ChrStart = int(Coordinates_Split[0])
        ChrEnd = int(Coordinates_Split[1])
        if m_cur_chr in Chromosome:
            if m_cur_chr_start >= ChrStart and m_cur_chr_end <= ChrEnd:
                WithinFlag = 1
                ReqGene = eachGene.strip()
                break
    if WithinFlag == 0:
        return 0
    else:
        return ReqGene


def RemoveSubsetHitswithinContigs(ContigDicts, outFile, known_genes, gene_req, unique_bases_threshold):
    ContigHitsReq = {}
    AllowedChr=["chrX","chrY"]
    for i in range(1,23):
        ChrString = "chr" + str(i)
        AllowedChr.append(ChrString)
        
    #
    outFile = open(outFile,"w")
    for eachContig in ContigDicts:
        TopHit = ContigDicts[eachContig][0]
        TopHit_Start = int(TopHit.split("\t")[6])
        TopHit_Stop = int(TopHit.split("\t")[7])
        TopHit_Chr = TopHit.split("\t")[1]
        if TopHit_Chr not in AllowedChr:
                continue
        TopHitCoords = list(range(TopHit_Start,TopHit_Stop))
        if len(ContigDicts[eachContig]) < 2:
            continue
        ContigHitsReq[eachContig] = []
        ContigHitsReq[eachContig].append(TopHit)
        for i in range(1, len(ContigDicts[eachContig])):
            NewHit = ContigDicts[eachContig][i]
            NewHit_Start = int(NewHit.split("\t")[6])
            NewHit_Stop = int(NewHit.split("\t")[7])
            NewHit_Chr = NewHit.split("\t")[1]
            NewHit_GStart = int(NewHit.split("\t")[8])
            NewHit_GStop = int(NewHit.split("\t")[9])
            if NewHit_Chr not in AllowedChr:
                continue
            NewHitCoords = list(range(NewHit_Start, NewHit_Stop))
            UniqueBases = 0
            for eachBase in NewHitCoords:
                if eachBase not in TopHitCoords:
                    UniqueBases += 1
            CheckifWithinKnownGenes = check_within_gene_bed(NewHit_Chr, int(NewHit_GStart), int(NewHit_GStop), known_genes, gene_req)

            if UniqueBases > unique_bases_threshold:  # was 10
                ContigHitsReq[eachContig].append(ContigDicts[eachContig][i])
            else:
                if CheckifWithinKnownGenes != 0:
                    ContigHitsReq[eachContig].append(ContigDicts[eachContig][i])
                        
    for eachContig in ContigHitsReq:
        if len(ContigHitsReq[eachContig]) > 1:
            for eachHit in ContigHitsReq[eachContig]:
                outFile.write(eachHit)
    outFile.close()


def FilterBlatResults(m_blat_file,outFile,known_genes,gene_req, unique_bases_threshold):
    with open(m_blat_file, "r") as m_blat_file:
        PassedHits = collections.OrderedDict()
        ReqHits = collections.OrderedDict()

        ContigDicts = {}
        for eachLine in m_blat_file:
            # Example blat line : Contig1350    chr13    96.88    32    1    0    183    214    95351676    95351707    1.6e-09    61.0
            eachLine_split = eachLine.split("\t")
            ContigID=eachLine_split[0]
            if ContigID in ContigDicts:
                ContigDicts[ContigID].append(eachLine)
            else:
                ContigDicts[ContigID] = []
                ContigDicts[ContigID].append(eachLine)

    RemoveSubsetHitswithinContigs(ContigDicts,outFile,known_genes,gene_req, unique_bases_threshold)
        
    return PassedHits


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Alignment wrapper')
    parser.add_argument("-i", "--input_File", dest="input", required=True, help="The path to BLAT_Files_For_Filter")
    parser.add_argument("-g", "--genebedFile", dest="genebed", required=True, help="Path to gene bed file")
    parser.add_argument("-o", "--outputFile", dest="output", required=True, help="Output filtered, annotated blat file")
    parser.add_argument("-G", "--GENEreq", dest="gene", required=True, help="Gene-Exon")
    parser.add_argument("-b", "--uniqueBasesThreshold", dest="unique_bases_threshold", required=True, type=int, help="Unique bases threshold to append contigs")

    inpArgs = parser.parse_args()

    config = ConfigClass.validate(inpArgs)
    main(config)
