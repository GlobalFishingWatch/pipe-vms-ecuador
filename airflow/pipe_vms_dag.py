from airflow.contrib.operators.bigquery_check_operator import BigQueryCheckOperator
from airflow.models import DAG

from airflow_ext.gfw import config as config_tools
from airflow_ext.gfw.models import DagFactory

from datetime import timedelta


PIPELINE = 'pipe_vms_ecuador'

#
# PIPE_VMS_ecuador
#
class PipelineDagFactory(DagFactory):
    """Concrete class to handle the DAG for pipe_vms_ecuador."""

    def __init__(self, pipeline=PIPELINE, **kwargs):
        """
        Constructs the DAG.

        :@param pipeline: The pipeline name. Default value the PIPELINE.
        :@type pipeline: str.
        :@param kwargs: A dict of optional parameters.
        :@param kwargs: dict.
        """
        super(PipelineDagFactory, self).__init__(pipeline=pipeline, **kwargs)

    def view_partition_count_check(self, dataset_id, table_id, date):
        """
        Checks if the BigQuery table with timestamp date has data.

        :@param dataset_id: The dataset id of the BQ table.
        :@type dataset_id: str.
        :@param table_id: The table id of the BQ table.
        :@type table_id: str.
        :@return: The BigQueryCheckOperator that checked the partition."""
        return BigQueryCheckOperator(
            task_id='table_partition_check',
            use_legacy_sql=False,
            sql='SELECT '
                    'COUNT(*) FROM `{dataset}.{table}` '
                'WHERE '
                    'timestamp > Timestamp("{date}") '
                    'AND timestamp <= TIMESTAMP_ADD(Timestamp("{date}"), INTERVAL 1 DAY)'
                .format(
                    dataset=dataset_id,
                    table=table_id,
                    date=date),
            retries=2*24*2,                        # Retries 2 days with 30 minutes.
            execution_timeout=timedelta(days=2),   # TimeOut of 2 days.
            retry_delay=timedelta(minutes=30),     # Delay in retries 30 minutes.
            max_retry_delay=timedelta(minutes=30), # Max Delay in retries 30 minutes
            on_failure_callback=config_tools.failure_callback_gfw
        )

    def build(self, dag_id):
        """
        Override of build method.

        :@param dag_id: The id of the DAG.
        :@type table: str.
        """
        config = self.config
        config['source_paths'] = ','.join(self.source_table_paths())
        config['source_dates'] = ','.join(self.source_date_range())

        with DAG(dag_id, schedule_interval=self.schedule_interval, default_args=self.default_args) as dag:

            view_partition_count_check = self.view_partition_count_check(
                '{source_dataset}'.format(**config),
                '{source_table}'.format(**config),
                '{ds}'.format(**config))

            fetch_normalized = self.build_docker_task({
                'task_id':'fetch_normalized_daily',
                'pool':'k8operators_limit',
                'docker_run':'{docker_run}'.format(**config),
                'image':'{docker_image}'.format(**config),
                'name':'fetch-normalized-daily',
                'dag':dag,
                'arguments':['fetch_normalized_vms',
                        '{source_dates}'.format(**config),
                        '{source_paths}'.format(**config),
                        '{project_id}:{pipeline_dataset}.{normalized}'.format(**config)]
            })

            dag >> view_partition_count_check >> fetch_normalized

        return dag


for mode in ['daily','monthly', 'yearly']:
    dag_id = '{}_{}'.format(PIPELINE, mode)
    globals()[dag_id] = PipelineDagFactory(schedule_interval='@{}'.format(mode)).build(dag_id)
