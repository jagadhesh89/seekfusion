task Control_Metrics {
    String Script # control_metric.py
    String PYTHON
    String LD_LIBRARY_PATH

    String SAMPLE_ID
    String RECIPE
    String BATCH_NAME
    String RUN_NAME
    String SAMPLE_PROJECT

    File ToTSV
    File Read_Metrics

    String MAIL
    String QUEUE
	File DedupJSON
	File AllReadJSON
    String dollar="$"

    command <<<
    set -euxo pipefail

    cp ${Read_Metrics} ./metric.1
    export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
    ${PYTHON} ${Script} -i ${ToTSV} -s ${SAMPLE_ID}_${RECIPE} -b ${BATCH_NAME} -r ${RUN_NAME} \
        -p ${SAMPLE_PROJECT} \
        > metric.2 \
        2> >(tee "Control_Metrics.log" >&2)

    # Parse the metric.1 file from the read counts to get the total reads for this sample across all bins
	
    COUNT=0
    LINES=$(cat metric.1 | wc -l)
    for num in $(seq 1 $LINES); do
        line=$(head -n $num metric.1|tail -n 1)
        MYVAL=$(printf "$line" | cut -f4)
        COUNT=$(($COUNT+$MYVAL))
    done
	
	TotalReads=$(grep "total_reads" ${AllReadJSON} | head -n1 | cut -f2 -d':' | sed "s|,||g")
	DedupedReads=$(grep "total_reads" ${DedupJSON} | head -n1 | cut -f2 -d':' | sed "s|,||g")
	
	Ratio=`echo "$DedupedReads / $TotalReads" | bc -l`
	Percentage=`echo "$Ratio * 100" | bc -l`
	PercentageDedup=`echo "100 - $Percentage" | bc -l`
	
	TargetReadsRatio=`echo "$COUNT / $DedupedReads" | bc -l`
	PercentageTarget=`echo "$TargetReadsRatio * 100" | bc -l`

    echo -e "#source\tmetricName\tmetricType\tmetricVal\tentityId\tentityType\tparentId\tparentType\tparentId\tparentType" > metric.0
    echo -e "UMIFUSION\tsample.coverage.reads.target.count\tI\t$COUNT\t${SAMPLE_ID}_${RECIPE}\tsample\t${BATCH_NAME}\tBatch\t${RUN_NAME}\trun" \
        > metric.3
		
	echo -e "UMIFUSION\tsample.coverage.reads.target.percent\tD\t$PercentageTarget\t${SAMPLE_ID}_${RECIPE}\tsample\t${BATCH_NAME}\tBatch\t${RUN_NAME}\trun" \
        > metric.4
		
	
	echo -e "UMIFUSION\tsample.coverage.reads.umidup.percent\tD\t$PercentageDedup\t${SAMPLE_ID}_${RECIPE}\tsample\t${BATCH_NAME}\tBatch\t${RUN_NAME}\trun" \
        > metric.5

    cat metric.0 metric.3 metric.1 metric.2 metric.4 metric.5 > ${SAMPLE_ID}.metrictsv

    >>>

    output {
        File metrics = "${SAMPLE_ID}.metrictsv"
        File log = "Control_Metrics.log"
    }

    runtime {
                sge_queue: "${QUEUE}"
                sge_mail: "${MAIL}"
    }
}