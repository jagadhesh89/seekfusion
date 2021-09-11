import os
import argparse
import math
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
    """
    class representation:
    {'Ref_Genome': '/dlmp/misc-data/pipelinedata/deployments/umifusion/2.0/snapshot_090820/genome/allchr.fa',
    'Samtools': '/biotools8/biotools/samtools/1.3.1/samtools',
    'GeneBedFile': '/dlmp/dev/runs/SARCP/SARCP_010221-mgt84-2_LIB-210103-002_IL4467-P6_JFKVW/samples/20-WFYQD-A-02-00/ordered_service/target.bed',
    'FinalBlatFilteredFile': '20-WFYQD-A-02-00_SARCP_ACTB_1.fa.filtered.blat',
    'EnsEnd': '/dlmp/misc-data/pipelinedata/deployments/umifusion/2.0/snapshot_090820/Homo_sapiens.GRCh37.75.Exon_End.15bases_up_down_exon.bed',
    'GeneExon': 'ACTB_1',
    'SampleName': '20-WFYQD-A-02-00_SARCP',
    'GeneReq': 'ACTB',
    'EnsStart': '/dlmp/misc-data/pipelinedata/deployments/umifusion/2.0/snapshot_090820/Homo_sapiens.GRCh37.75.Exon_Start.15bases_up_down_exon.bed',
    'ContigFile': '20-WFYQD-A-02-00_SARCP_ACTB_1.contigs'}
    """
    Configuration = {}

    def __init__(self, m_args):
        self.validate_arguments(m_args)

    def __str__(self):
        return str(self.Configuration)

    def validate_arguments(self, cli_args):

        if not os.access(cli_args.blat, os.R_OK):
            logger.error("Final Contigs Blat Result {} is not accessible.".format(cli_args.blat))
            exit(1)
        self.Configuration["FinalBlatFilteredFile"] = cli_args.blat

        if not os.access(cli_args.contigs, os.R_OK):
            logger.error("Contigs File {} is not accessible.".format(cli_args.contigs))
            exit(1)
        self.Configuration["ContigFile"] = cli_args.contigs

        self.Configuration["GeneReq"] = cli_args.gene_exon.split("_")[0]

        if not os.access(cli_args.ensstart, os.R_OK):
            logger.error("Ensemble Starts File {} is not accessible.".format(cli_args.ensstart))
            exit(1)

        if not os.access(cli_args.ensend, os.R_OK):
            logger.error("Ensemble Ends File {} is not accessible.".format(cli_args.ensend))
            exit(1)

        self.Configuration["EnsStart"] = cli_args.ensstart
        self.Configuration["EnsEnd"] = cli_args.ensend

        if not os.access(cli_args.genebed, os.R_OK):
            logger.error("Gene Bed File {} is not accessible.".format(cli_args.genebed))
            exit(1)

        self.Configuration["GeneBedFile"] = cli_args.genebed

        self.Configuration["SampleName"] = cli_args.sample_name
        self.Configuration["GeneExon"] = cli_args.gene_exon

        if not os.access(cli_args.samtools, os.X_OK):
            logger.error("Samtools {} is not executable.", format(cli_args.samtools))
            exit(1)
        self.Configuration["Samtools"] = cli_args.samtools

        if not os.access(cli_args.refgenome, os.R_OK):
            logger.error("Reference Genome {} is not readable.".format(cli_args.refgenome))
            exit(1)
        self.Configuration["Ref_Genome"] = cli_args.refgenome

        logger.info(self.__str__())
        return self

    @property
    def gene_exon(self):
        return self.Configuration["GeneExon"]

    @property
    def sample_name(self):
        return self.Configuration["SampleName"]

    @property
    def ens_start(self):
        return self.Configuration["EnsStart"]

    @property
    def ens_end(self):
        return self.Configuration["EnsEnd"]

    @property
    def gene_bed_file(self):
        return self.Configuration["GeneBedFile"]

    @property
    def contig_file(self):
        return self.Configuration["ContigFile"]

    @property
    def final_blat_filtered_file(self):
        return self.Configuration["FinalBlatFilteredFile"]

    @property
    def temp_path(self):
        return self.Configuration["TempPath"]

    @property
    def gene_req(self):
        return self.Configuration["GeneReq"]

    @property
    def read_length(self):
        return self.Configuration["ReadLength"]

    @property
    def samtools(self):
        return self.Configuration["Samtools"]

    @property
    def ref_genome(self):
        return self.Configuration["Ref_Genome"]


def check_presence(m_path, m_type, m_name):
    if len(m_path) < 1:
        logger.error("Incorrect Path for " + m_name)
        exit(1)

    if "f" in m_type:
        if not os.path.isfile(m_path):
            logger.error(m_name + " does not exist in " + m_path)
            exit(1)
    else:
        if not os.path.isdir(m_path):
            logger.error(m_name + " does not exist in " + m_path)
            exit(1)

    return m_path


def check_dir(m_dir):
    if not os.path.isdir(m_dir):
        os.makedirs(m_dir)


def ensembl_line_parser(line):
    """
    This function accepts a line like "chr1	11854	11884	+	Start_E1	DDX11L1	DDX11L1-002",
    get the [1] field and adds 15, then returns the number.
    :param line:
    :return: exon start/stop position  '11869'
    """
    EnsemblLineSplit = line.split("\t")
    Start = EnsemblLineSplit[1]

    return str(int(Start) + 15)


def read_ensembl(ensembl_file_start, ensembl_file_end):
    """

    :param ensembl_file_start: "chr1	11854	11884	+	Start_E1	DDX11L1	DDX11L1-002"
                               "chr1	12598	12628	+	Start_E2	DDX11L1	DDX11L1-002"
    :param ensembl_file_end: "chr1	12212	12242	+	End_E1	DDX11L1	DDX11L1-002"
                             "chr1	12706	12736	+	End_E2	DDX11L1	DDX11L1-002"
    :return:  OrderedDict([('chr1', OrderedDict([(1, '11869-12227,12613-12721')]))])
    """
    # Load up Ensembl coordinates
    # Dict will be in structure EnsemblCoord["chr1"]["1"] = "123-134-ABC-ex-1-ENS001"
    ensembl_file_start = open(ensembl_file_start, "r")
    ensembl_file_end = open(ensembl_file_end, "r")
    EnsemblCoord = collections.OrderedDict()
    StartArray = []
    EndArray = []

    for eachLine in ensembl_file_start:
        StartArray.append(eachLine)

    for eachLine in ensembl_file_end:
        EndArray.append(eachLine)

    for i in range(0, len(StartArray)):
        StartLine = StartArray[i]
        EndLine = EndArray[i]
        Strand = StartLine.split("\t")[3]
        if Strand == "+":
            ChrStart = ensembl_line_parser(StartLine)
            ChrEnd = ensembl_line_parser(EndLine)
        else:
            ChrStart = ensembl_line_parser(EndLine)
            ChrEnd = ensembl_line_parser(StartLine)

        Chromosome = StartLine.split("\t")[0]
        ExonCoordStr = ChrStart + "-" + ChrEnd
        FirstNumber_of_ExonCoordStr = int(ExonCoordStr[0])
        if Chromosome in EnsemblCoord.keys():
            if FirstNumber_of_ExonCoordStr in EnsemblCoord[Chromosome]:
                EnsemblCoord[Chromosome][FirstNumber_of_ExonCoordStr] = \
                    EnsemblCoord[Chromosome][FirstNumber_of_ExonCoordStr] + "," + ExonCoordStr
            else:
                EnsemblCoord[Chromosome][FirstNumber_of_ExonCoordStr] = ExonCoordStr
        else:
            EnsemblCoord[Chromosome] = collections.OrderedDict()
            EnsemblCoord[Chromosome][FirstNumber_of_ExonCoordStr] = ExonCoordStr

    # #logger.info("EnsemblCoord {}".format(EnsemblCoord))
    return EnsemblCoord


def process_contig_file(m_contigfile):
    """
    it concatenates sequences belongs to the same contig

    :param m_contigfile: file handler
                         ">Contig1
                            CGTCACCGGAGTCCATCACGATGCCAGTGGTACGGCCAGGACCTGACTGACTACCTCATG
                            AAGATCCTCACCGAGCGCGGCTACAGCTCCACCACCACAGGACTCCAAT
                            >Contig2
                            ATTGGAGTCCTGCTCGGTGAGGATCTTCATGAGGTAGTCAGTCAGGTCCCGGCCAGCCAG
                            GTCCAGACGCAGGATGGCATGGGGGAGGGCATACCCCTCTGGCCGTACCACTGGCATCGT
                            GATGGACTCCGGTGACG"
    :return:  OrderedDict([('Contig1', 'CGTCACCGGAGTCCATCACGATGCCAGTGGTACGGCCAGGACCTGACTGACTACCTCATGAAGATCCTCACCGAGCGCGGCTACAGCTCCACCACCACAGGACTCCAAT'),
    ('Contig2', 'ATTGGAGTCCTGCTCGGTGAGGATCTTCATGAGGTAGTCAGTCAGGTCCCGGCCAGCCAGGTCCAGACGCAGGATGGCATGGGGGAGGGCATACCCCTCTGGCCGTACCACTGGCATCGTGATGGACTCCGGTGACG')])
    """
    TmpSeq = ""
    TmpCount = 0
    ContigSeqs = collections.OrderedDict()
    ContigHeader = ""
    for eachLine in m_contigfile:
        TmpCount += 1
        if eachLine[0] in ">":
            if TmpCount != 1:
                ContigSeqs[ContigHeader] = TmpSeq
                TmpSeq = ""
            ContigHeader = eachLine.strip().replace(">", "")
        else:
            TmpSeq = TmpSeq + eachLine.strip()
    ContigSeqs[ContigHeader] = TmpSeq
    logger.info("ContigSeqs {}".format(ContigSeqs))
    return ContigSeqs


def repeat_check(m_seq):
    # This function calculates a Homopolymer weighted ratio to help in identifying stretch of nucleotide repeats
    """

    :param m_seq:  'GGCCAGGACCTGACTGACTACCTCATGAAGATCCTCACCGAGCGCGGCTACAGCTCCACCACCA'
    :return: 0
    """
    PrevNuc = ""
    TmpCount = 0
    LocalSummationReq = 0
    GlobalSummationReq = 0
    SummationCount = 0
    for eachNuc in m_seq:
        TmpCount += 1
        CurNuc = eachNuc
        if TmpCount == 1:
            LocalSummationReq += 1
            PrevNuc = CurNuc
            continue
        if CurNuc.upper() == PrevNuc.upper():
            LocalSummationReq += 1
            if TmpCount == len(m_seq):
                GlobalSummationReq = GlobalSummationReq + math.pow(LocalSummationReq, 2)
                SummationCount += 1
        else:
            if LocalSummationReq < 1:
                LocalSummationReq = 1

            GlobalSummationReq = GlobalSummationReq + math.pow(LocalSummationReq, 2)
            SummationCount += 1
            if TmpCount == len(m_seq):
                GlobalSummationReq = GlobalSummationReq + math.pow(LocalSummationReq, 2)
                SummationCount += 1
            LocalSummationReq = 1
        PrevNuc = CurNuc
    if SummationCount == 0:
        return 1
    WHR = round((float(GlobalSummationReq) / float(SummationCount)), 2)
    if WHR > 10:
        return 1
    else:
        return 0


def check_within_gene_bed(m_cur_chr, m_cur_chr_start, m_cur_chr_end, m_known_genes, m_genereq):
    """
    check if the current blat entry is inside the gene m_genereq. If so, return this gene. otherwise, return 0
    :param m_cur_chr:'chr5'
    :param m_cur_chr_start:77080659
    :param m_cur_chr_end:77080731
    :param m_known_genes: an ordered dictionary like
        OrderedDict([('ACTB', 'chr7:5566776-5570340'), ('AHRR', 'chr5:304290-438405')])
    :param m_genereq:ACTB
    :return:
    """
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


def find_closest_boundary(m_ensembl_coord, contig_chr, first_number_of_coordinate,
                          m_breakpoint):
    ExonCoordinatesFromEnsembl = m_ensembl_coord[contig_chr][int(first_number_of_coordinate)].split(",")
    
    for eachCoordinateFullSet in ExonCoordinatesFromEnsembl:
        eachCoordinateSet_split = eachCoordinateFullSet.split("-")
        refCoordinateStart = int(eachCoordinateSet_split[0])
        refCoordinateEnd = int(eachCoordinateSet_split[1])

        # Blat gives mapping of contig to a region in genome and gives genome start and stop for mapping
        # if Breakpoints from Blat exactly matches a start AND a stop no correction
        # is required, return the coordinates
        if m_breakpoint == refCoordinateEnd or m_breakpoint == refCoordinateStart:
            return str(m_breakpoint)

        # Get Distance of Breakpoint from Ensembl Exon boundary, if it is within 30 base pairs
        # from boundary, the distance is stored
        else:
            if abs(m_breakpoint - refCoordinateStart) <= 20 or abs(m_breakpoint - refCoordinateEnd) <= 20:
                if abs(m_breakpoint - refCoordinateStart) < abs(m_breakpoint - refCoordinateEnd):
                    return str(refCoordinateStart)
                else:
                    return str(refCoordinateEnd)
                # Whichever Distance was closest to ensembl exon boundary return it
    return str(m_breakpoint)


def get_known_genes(gene_bedfile):
    """ Just reads a bed file with gene annotations
    :param gene_bedfile: "chr7	5566776	5570340	ACTB:NM_001101	GENE	-	TRANSLATING
                         chr5	304290	438405	AHRR:NM_020731	GENE	+	TRANSLATING"
    :return:     OrderedDict([('ACTB', 'chr7:5566776-5570340'), ('AHRR', 'chr5:304290-438405')])

    """
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

    logger.info("KG:{}".format(KnownGenes))
    return KnownGenes


def get_breakpoint(m_partner, m_ensembl_coord):
    MapStart = m_partner.split(":")[1]
    Chr = m_partner.split(":")[0]
    FirstNumberofCoordinate = MapStart[0]
    BreakPoint = find_closest_boundary(m_ensembl_coord, Chr, FirstNumberofCoordinate, int(MapStart))
    return Chr, BreakPoint


def get_partners(known_gene_contig_map, unknown_gene_contig_map):
    FusionsRequired = collections.OrderedDict()
    
    # One gene to other gene
    for eachUnKnownContigMap in unknown_gene_contig_map:

        for eachKnownContigMap in known_gene_contig_map:
            KnownChr = eachKnownContigMap.split(":")[0]
            KnownStart = eachKnownContigMap.split(":")[1].split("-")[0]
            KnownStop = eachKnownContigMap.split(":")[1].split("-")[1]
            UnKnownChr = eachUnKnownContigMap.split(":")[0]
            UnKnownStart = eachUnKnownContigMap.split(":")[1].split("-")[0]
            UnKnownStop = eachUnKnownContigMap.split(":")[1].split("-")[1]

            # All Combinations of start stop from blat - no restriction required due to bwa-mem enabled filtering

            FusionsRequired[KnownChr + ":" + KnownStart + "-" + UnKnownChr + ":" + UnKnownStop] = 1
            FusionsRequired[KnownChr + ":" + KnownStart + "-" + UnKnownChr + ":" + UnKnownStart] = 1
            FusionsRequired[KnownChr + ":" + KnownStop + "-" + UnKnownChr + ":" + UnKnownStart] = 1
            FusionsRequired[KnownChr + ":" + KnownStop + "-" + UnKnownChr + ":" + UnKnownStop] = 1

    # If there is an intra gene re arrangement this captures it
    if len(known_gene_contig_map) > 1:
        for eachKnownContigMap in known_gene_contig_map:
            for eachContigMap in known_gene_contig_map:
                if eachKnownContigMap != eachContigMap:
                        KnownChr = eachKnownContigMap.split(":")[0]
                        KnownStart = eachKnownContigMap.split(":")[1].split("-")[0]
                        KnownStop = eachKnownContigMap.split(":")[1].split("-")[1]
                        UnKnownChr = eachContigMap.split(":")[0]
                        UnKnownStart = eachContigMap.split(":")[1].split("-")[0]
                        UnKnownStop = eachContigMap.split(":")[1].split("-")[1]
                        
                        FusionsRequired[KnownChr + ":" + KnownStart + "-" + UnKnownChr + ":" + UnKnownStop] = 1
                        FusionsRequired[KnownChr + ":" + KnownStart + "-" + UnKnownChr + ":" + UnKnownStart] = 1
                        FusionsRequired[KnownChr + ":" + KnownStop + "-" + UnKnownChr + ":" + UnKnownStart] = 1
                        FusionsRequired[KnownChr + ":" + KnownStart + "-" + UnKnownChr + ":" + UnKnownStop] = 1

    # for eachUnKnownContigMap
    return FusionsRequired


def contig_map_processor(m_contig_chr, gmap_start, gmap_end, contig_pos_start, contig_pos_end, gene_contig_map):
    """

    :param m_contig_chr:  'chr5'
    :param gmap_start: '77080659'
    :param gmap_end: '77080731'
    :param contig_pos_start: '62'
    :param contig_pos_end: '140'
    :param gene_contig_map: ordered dictionary that is modified by the function and returned
    :return: OrderedDict([('chr5:77080659-77080731', '62-140')])
    """
    if len(gene_contig_map) < 1:
        gene_contig_map[m_contig_chr + ":" + gmap_start + "-" + gmap_end] = contig_pos_start + "-" + contig_pos_end
    else:
        SeenCoordinates = 0
        for eachMapping in gene_contig_map:
            eachMapStart = eachMapping.split(":")[1].split("-")[0]
            eachMapEnd = eachMapping.split("-")[1]
            eachMapChr = eachMapping.split(":")[0]
            if int(gmap_start) >= int(eachMapStart) and int(gmap_end) <= int(eachMapEnd) and m_contig_chr == eachMapChr:
                SeenCoordinates = 1
        if SeenCoordinates != 1:
            gene_contig_map[m_contig_chr + ":" + gmap_start + "-" + gmap_end] = contig_pos_start + "-" + contig_pos_end
    return gene_contig_map


def write_fp_reduction(contig_dict, config, known_genes, gene_exon, ensembl_coord, filename):
    Gene = gene_exon.split("ex")[0]
    FoundFusions = collections.OrderedDict()
    logger.info("FP Reduce on Gene {}, contigs: {}".format(Gene, contig_dict))
    UniqueReads = 5
    try:
        with open(filename + ".final_inframe", "w") as final_inframe:
            for eachContig in contig_dict:
                ContigLinesSplit = contig_dict[eachContig].split(";")
                if len(ContigLinesSplit) < 2:
                    continue
                
                logger.info("Processing Contig: {} ".format(eachContig))
                KnownGeneContigMap = collections.OrderedDict()
                UnKnownGeneContigMap = collections.OrderedDict()
                # Iterate through each mapping of a contig
                # Contig1350    chr13    96.88    32    1    0    183    214    95351676    95351707    1.6e-09    61.0
                # If column number starts from 0, 6th and 7th column specify which part of contig mapped
                # to the chr13 loc, 8 and 9 are genomic locations to which it mapped

                for eachCLine in ContigLinesSplit:
                    CLine_Split = eachCLine.split("\t")
                    GMapStart = CLine_Split[8]
                    GMapEnd = CLine_Split[9]
                    ContigPosStart = CLine_Split[6]
                    ContigPosEnd = CLine_Split[7]
                    if int(GMapEnd) < int(GMapStart):
                        GMapStart = CLine_Split[9]
                        GMapEnd = CLine_Split[8]
                    ContigChr = CLine_Split[1]
                    # FirstNumberofCoordinate = CLine_Split[8][0]
                    # ContigStartStop = GMapStart + "-" + GMapEnd
                    # Check if it is within a Gene Bed region
                    CheckifWithinKnownGenes = \
                        check_within_gene_bed(ContigChr, int(GMapStart), int(GMapEnd), known_genes, config.gene_req)

                    # StoreMapping Info of Known Gene and Unknown partner
                    if CheckifWithinKnownGenes == Gene:
                        KnownGeneContigMap = contig_map_processor(ContigChr, GMapStart, GMapEnd,
                                                                  ContigPosStart, ContigPosEnd,
                                                                  KnownGeneContigMap)
                    else:
                        UnKnownGeneContigMap = contig_map_processor(ContigChr, GMapStart, GMapEnd,
                                                                    ContigPosStart, ContigPosEnd,
                                                                    UnKnownGeneContigMap)
                
                # get all combinations of blat mapping as potential candidates
                RequiredFusions = get_partners(KnownGeneContigMap, UnKnownGeneContigMap)
                
                logger.info("Required Fusions: {}".format(RequiredFusions))
                for eachFusion in RequiredFusions:
                    logger.info("Output for {}".format(eachFusion))
                    UnKnownPartner = eachFusion.split("-")[1]
                    KnownPartner = eachFusion.split("-")[0]
                    # Get Corrected breakpoint to Exon boundary, check if mapping is within
                    # 30bp of a exon boundary, if yes correct it to boundary
                    # There are 4 possibilities
                    KnownChr, KnownBreakpoint = get_breakpoint(KnownPartner, ensembl_coord)
                    UnKnownChr, UnKnownBreakpoint = get_breakpoint(UnKnownPartner, ensembl_coord)
                    CumulativeReads = 5
                    if len(str(KnownBreakpoint)) < 1 or len(str(UnKnownBreakpoint)) < 1:
                        continue
                    logger.info("KnownBP {}, UnknownBP {}".format(KnownBreakpoint, UnKnownBreakpoint))

                    # If known gene blat result exactly matched with the exon boundary coordinate

                    FoundFusions[str(KnownBreakpoint) + "-" + str(UnKnownBreakpoint)] = 1
                    logger.info("Writing result for {} {}".format(str(KnownBreakpoint), str(UnKnownBreakpoint)))
                    KnownBreakpoint_split = KnownBreakpoint.split("-")
                    UnKnownBreakpoint_split = UnKnownBreakpoint.split("-")
                    for eachKnownBP in KnownBreakpoint_split:
                        for eachUnKnownBP in UnKnownBreakpoint_split:
                            StrReq = str(KnownChr) + "\t" + str(eachKnownBP) + "\t" + str(UnKnownChr) + "\t" + str(
                                eachUnKnownBP) + "\t" + str(UniqueReads) + "\t" + str(CumulativeReads) + "\n"
                            logger.info("Final Out {}".format(StrReq))
                            final_inframe.write(StrReq)
                            final_inframe.flush()

    except IOError as ex:
        logger.exception(ex.strerror)
        exit(1)


def filter_fp(m_config, known_genes, ensembl_coord):
    eachFile = m_config.sample_name + "_" + m_config.gene_exon + ".fa.filtered.blat"

    GeneExon = m_config.gene_exon
    logger.info("filter_fp: GeneExon {}".format(GeneExon))
    Gene_Exon_Split = GeneExon.split("_")
    Gene_Exon = Gene_Exon_Split[0] + "ex" + Gene_Exon_Split[1].lstrip("0")

    ContigSeqs = None
    try:
        with open(m_config.contig_file, "r") as ContigFile:
            ContigSeqs = process_contig_file(ContigFile)
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(1)

    # Iterate through each Line in Blat File
    # Contig1350    chr13    96.88    32    1    0    183    214    95351676    95351707    1.6e-09    61.0
    # If column number starts from 0, 6th and 7th column specify which part of contig mapped to the chr13 loc
    ContigDict = collections.OrderedDict()
    try:
        with open(m_config.final_blat_filtered_file, "r") as eachBlatFile:
            for eachLine in eachBlatFile:
                PassFlag = 1
                eachLine_split = eachLine.split("\t")
                MapStart = eachLine_split[6]
                MapEnd = eachLine_split[7]
                ContigName = eachLine_split[0]
                CurrentContigSeq = ContigSeqs[ContigName]
                # If contig mapped to a location that is highly repetitive its homopolymer ratio is high
                # CHeck for repeats in the region and if it is repetitive with HPR>10, do not consider this region
                RepeatFlag = repeat_check(CurrentContigSeq[int(MapStart) - 1:int(MapEnd) - 1])
                # print eachLine,RepeatFlag
                if RepeatFlag == 1:
                    PassFlag = 0
                if PassFlag == 1:
                    if ContigName not in ContigDict.keys():
                        ContigDict[ContigName] = eachLine
                    else:
                        ContigDict[ContigName] = ContigDict[ContigName] + ";" + eachLine
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(1)

    # Contig Dict Data struct: ContigDict["Contig1"] = BlatLine1; BlatLine2
    # OrderedDict([('Contig1', 'Contig1\tchr7\t96.92\t65\t2\t0\t34\t98\t5568170\t5568106\t2.1e-28\t123.0\n;
    # Contig1\tchr7\t100.00\t39\t0\t0\t1\t39\t5568242\t5568280\t1.5e-14\t77.0\n;
    # Contig1\tchrX\t96.77\t31\t1\t0\t9\t39\t46148109\t46148139\t2.2e-08\t57.0\n;
    # Contig1\tchr10\t96.77\t31\t1\t0\t9\t39\t70782973\t70782943\t6.6e-09\t59.0\n'),

    # ('Contig2', 'Contig2\tchr7\t100.00\t88\t0\t0\t12\t99\t5568128\t5568215\t8.9e-44\t174.0\n;
    # Contig2\tchr7\t100.00\t42\t0\t0\t96\t137\t5568283\t5568242\t2.5e-16\t83.0\n;
    # Contig2\tchr5\t92.86\t42\t3\t0\t96\t137\t77081141\t77081182\t2.1e-13\t74.0\n;
    # Contig2\tchr2\t95.24\t42\t2\t0\t96\t137\t132021559\t132021600\t1.0e-14\t78.0\n;
    # Contig2\tchr3\t90.48\t42\t4\t0\t96\t137\t175695971\t175695930\t4.6e-12\t69.0\n;
    # Contig2\tchrX\t97.06\t34\t1\t0\t96\t129\t46148142\t46148109\t3.5e-10\t63.0\n;
    # Contig2\tchr10\t97.06\t34\t1\t0\t96\t129\t70782940\t70782973\t1.1e-10\t65.0\n')])
    write_fp_reduction(ContigDict, m_config, known_genes, Gene_Exon, ensembl_coord, eachFile)


def main(inp_args):
    inputs = ConfigClass(inp_args)
    
    EnsemblCoord = read_ensembl(inputs.ens_start, inputs.ens_end)
    KnownGenes = get_known_genes(inputs.gene_bed_file)
    filter_fp(inputs, KnownGenes, EnsemblCoord)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='UMI Fusion Pipeline Each Fusion Product Filter (EachFP.py)')
    parser.add_argument("-i", "--input", dest="blat", required=True, help="The path to the blat results")
    parser.add_argument("-t", "--contigs", dest="contigs", required=True, help="Path to the matching contig file")
    parser.add_argument("-e1", "--ens_start", dest="ensstart", required=True, help="Ensemble starts file")
    parser.add_argument("-e2", "--ens_end", dest="ensend", required=True, help="Ensemble ends file")
    parser.add_argument("-s", "--samtools", dest="samtools", required=True, help="Path to samtools binary")
    parser.add_argument("-g", "--genebed", dest="genebed", required=True, help="Path to gene bed file")
    parser.add_argument("-r", "--refgenome", dest="refgenome", required=True, help="Path to reference genome")
    parser.add_argument("-S", "--SAMPLE", dest="sample_name", required=True, help="The SampleName")
    parser.add_argument("-G", "--GENEEXON", dest="gene_exon", required=True, help="Gene-Exon")
    
    main(parser.parse_args())
