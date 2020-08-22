from airflow import DAG

from airflow_ext.gfw.models import DagFactory

from datetime import datetime, timedelta

ECUADOR_VMS_SCRAPPER_POOL = 'ecuador-vms-scrappers'
PIPELINE = 'pipe_vms_ecuador_api'


class PipeVMSEcuadorDagFactory(DagFactory):
    """Concrete class to handle the DAG for pipe_vms_ecuador_api."""

    def __init__(self, pipeline=PIPELINE, **kwargs):
        """
        Constructs the DAG.

        :@param pipeline: The pipeline name. Default value the PIPELINE.
        :@type pipeline: str.
        :@param kwargs: A dict of optional parameters.
        :@param kwargs: dict.
        """
        super(PipeVMSEcuadorDagFactory, self).__init__(pipeline=pipeline, **kwargs)

    def source_date(self):
        """
        Validates that the schedule interval only be in daily mode.

        :raise: A ValueError.
        """
        if self.schedule_interval != '@daily':
            raise ValueError('Unsupported schedule interval {}'.format(self.schedule_interval))

    def build(self, dag_id):
        """
        Override of build method.

        :@param dag_id: The id of the DAG.
        :@type table: str.
        """
        config = self.config

        two_days_before = datetime.now() - timedelta(days=2)
        with DAG(dag_id, schedule_interval=self.schedule_interval, default_args=self.default_args, end_date=two_days_before) as dag:

            fetch = self.build_docker_task({
                'task_id':'pipe_ecuador_fetch',
                'pool':ECUADOR_VMS_SCRAPPER_POOL,
                'docker_run':'{docker_run}'.format(**config),
                'image':'{docker_image}'.format(**config),
                'name':'pipe-ecuador-fetch',
                'dag':dag,
                'retries':5,
                'max_retry_delay': timedelta(hours=5),
                'arguments':['fetch_ecuador_vms_data',
                             '{ecuador_vms_gcs_path}'.format(**config),
                             '{ds}'.format(**config)]
            })


            dag >> fetch

        return dag

pipe_vms_ecuador_api_dag = PipeVMSEcuadorDagFactory().build(PIPELINE)
