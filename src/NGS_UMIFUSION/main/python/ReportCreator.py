import argparse
import logging

# Set basic logging level. Change the screen-handler to WARN or ERROR to reduce verbosity
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.INFO)  # Change this to reduce screen level verbosity
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)


def main(inp_args):
    process_report(inp_args.bpfile, inp_args.template)


def process_report(bpfile, template):

    header = ""
    template_str = ""
    req_lines = ""
    line_count = 0
    
    try:
        with open(template, "r") as templateFile:
            for eachLine in templateFile:
                if line_count == 0:
                    header = eachLine
                if line_count == 1:
                    template_str = eachLine
                    break
                line_count += 1
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(ex.errno)
    
    try:
        with open(bpfile, "r") as breakpointFile:
            for eachLine in breakpointFile:
                each_line_split = eachLine.split("\t")
                fiveprime_bp_chr = each_line_split[0]
                fiveprime_bp_coord = each_line_split[1]
                threeprime_bp_chr = each_line_split[2]
                threeprime_bp_coord = each_line_split[3]
                
                req_fusion = template_str.replace("<5PBRPTCHR>", fiveprime_bp_chr)
                req_fusion = req_fusion.replace("<5PBRPTCOORD>", fiveprime_bp_coord)
                req_fusion = req_fusion.replace("<3PBRPTCHR>", threeprime_bp_chr)
                req_fusion = req_fusion.replace("<3PBRPTCOORD>", threeprime_bp_coord)
                
                req_lines = req_lines + req_fusion
        
    except IOError as ex:
        logger.exception(ex.strerror)
        exit(ex.errno)
        
    print(header+req_lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", "--BreakpointFile",
                        dest="bpfile",
                        help="the breakpoint file",
                        required=True)
    parser.add_argument("-t", "--templateFile",
                        dest="template",
                        help="template of star fusion style report",
                        required=True)
    inpArgs = parser.parse_args()
    main(inpArgs)
