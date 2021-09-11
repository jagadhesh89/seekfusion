task Aggregate_GeneMetric {
	Array[File]? GeneMetrics
	String SAMPLE_ID
    String QUEUE
    String MAIL

	command <<<
	for GeneMetric in ${sep=' ' GeneMetrics} ; do
		/bin/cat $GeneMetric >> metrics.txt
	done

	sed -i '/^$/d' metrics.txt

	>>>

	output {
        File Read_Metrics= "metrics.txt"
    }
	runtime {
        sge_queue: "${QUEUE}"
        sge_mail: "${MAIL}"
    }
}
