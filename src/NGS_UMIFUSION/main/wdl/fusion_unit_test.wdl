## Core fusion WDL pipeline, accepts set of primers, bins reads and checks for fusions in each scattered bin
## Number of bins should be limited to avoid high memory consumption

import "/dlmp/dev/scripts/sources/teamwork/yupeng/UMIFUSION/v1.01.00/src/NGS_UMIFUSION/main/wdl/fusion.wdl" as fswdl

task regr_extract_chunk_of_primers {
    String PYTHON
    String LD_LIBRARY_PATH
    String QUEUE
    String MAIL
    String GD_saved_output
    String GD_script
    String GD_chk_points
    String dollar = "$"
    File in_tag
    command <<<
    out_dir="${in_tag}"
    echo $out_dir
    export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
    rgrs_rt=$(${PYTHON} ${GD_script} -c ${GD_chk_points} -g "$out_dir" -r ${GD_saved_output} -s 0 -e 1)
    rt_code=${dollar}{rgrs_rt:0:1}
    cat << EOF > "regr.outcome"
    $rgrs_rt
    EOF
    if ["$rt_code" -eq "0"]; then
        exit 1
    fi
    >>>
    output {
         File out_tag="regr.outcome"
    }
    runtime {
              sge_queue: "${QUEUE}"
              sge_mail: "${MAIL}"
    }
}

workflow UMIFUSION {
    String QUEUE
    String MAIL
    Int? CHUNKSIZE
    Int? THIS_CHUNK
    String ref_primers
    String PYTHON
    String LD_LIBRARY_PATH   
    String GD_saved_output
    String GD_script
    String GD_chk_points
    
    call fswdl.extract_chunk_of_primers as extract_chunk_of_primers {
        input:
            number_of_chunks=CHUNKSIZE,
            my_chunk=THIS_CHUNK,
            ref_primers=ref_primers,
            QUEUE=QUEUE,
            MAIL=MAIL
    }
    
    call regr_extract_chunk_of_primers {
        input:
            PYTHON = PYTHON,
            LD_LIBRARY_PATH=LD_LIBRARY_PATH,
            GD_saved_output=GD_saved_output,
            QUEUE=QUEUE,
            MAIL=MAIL,
            GD_script=GD_script,
            GD_chk_points=GD_chk_points,
            in_tag=extract_chunk_of_primers.my_primers
    }
}
