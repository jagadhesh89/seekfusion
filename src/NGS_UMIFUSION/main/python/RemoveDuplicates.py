class RemoveDups:
    def __init__(self):
        self.input_file_stream = None
        self.output_stream = None
        self.allowed_dups = None
        self.unique_reads = None

    def remove(self, input_file_stream, output_stream, allowed_dups):
        self.input_file_stream = input_file_stream
        self.output_stream = output_stream
        self.allowed_dups = allowed_dups
        self.unique_reads = {}
        
        for eachLine in self.input_file_stream:
            each_line_split = eachLine.strip().split()
            # Check to see if line has some contents
            if len(each_line_split) < 10:
                continue
                
            # Get length of read
            read_len = str(len(each_line_split[9]))
            
            # Pos - EP400:16845:73S31M47S
            Pos = each_line_split[2] + ":" + each_line_split[3] + ":" + each_line_split[5]
            # unique_str - EP400:16845:73S31M47S:151
            # Gene, the read mapped to, position in the gene that the read started mapping, Cigar string, Length of Read
            unique_str = Pos + "-" + read_len
            
            # Write the read sequence if it has unique_str <= allowed duplicates
            if unique_str in self.unique_reads:
                if self.unique_reads[unique_str] < self.allowed_dups:
                    self.output_stream.write(eachLine)
                    self.unique_reads[unique_str] += 1
            else:
                self.output_stream.write(eachLine)
                self.unique_reads[unique_str] = 1