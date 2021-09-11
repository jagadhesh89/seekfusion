export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_TRIM_THRESHOLD_=131072
export MALLOC_TOP_PAD_=131072
export MALLOC_MMAP_MAX_=65536
/biotools/biotools/java/jdk1.8.0_111/bin/java -Dbackend.providers.SGE.config.root=/dlmp/dev/temp/cromwell -Dworkflow-options.workflow-log-dir=/dlmp/dev/logs/umifusion -Dconfig.file=/dlmp/dev/scripts/sources/teamwork/yupeng/UMIFUSION/v1.01.00/configs/sge.conf -Xmx32G -Xms32G -Xss10M -jar /dlmp/misc-data/reference/tools/cromwell/0.31/cromwell-31.jar run /dlmp/dev/scripts/sources/teamwork/yupeng/UMIFUSION/v1.01.00/src/LNGS_UMIFUSION/main/wdl/fusion_im.wdl -i /dlmp/dev/runs/NGS71_golden/test2/umifusion/configs/inputs.json -o /dlmp/dev/runs/NGS71_golden/test2/umifusion/configs/configs.json -m /dlmp/dev/runs/NGS71_golden/test2/umifusion/configs/outputs.json | tee -a /dlmp/dev/runs/NGS71_golden/test2/umifusion/logs/main.log
