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
        ecuador_vms_gcs_path=config['ecuador_vms_gcs_path']
        config['ecuador_vms_gcs_path']=ecuador_vms_gcs_path[:-1] if ecuador_vms_gcs_path.endswith('/') else ecuador_vms_gcs_path

        with DAG(dag_id, schedule_interval=self.schedule_interval, default_args=self.default_args) as dag:


            filter_the_query_date = self.build_docker_task({
                'task_id':'pipe_ecuador_filter',
                'pool':'k8operators_limit',
                'docker_run':'{docker_run}'.format(**config),
                'image':'{docker_image}'.format(**config),
                'name':'pipe-ecuador-filter',
                'dag':dag,
                'retries':5,
                'max_retry_delay': timedelta(hours=5),
                'arguments':['filter_ecuador_vms_data',
                             '-d {ds}'.format(**config),
                             '-i {ecuador_vms_gcs_path}/'.format(**config),
                             '-o {ecuador_vms_gcs_path}/'.format(**config)]
            })

            load = self.build_docker_task({
                'task_id':'pipe_ecuador_load',
                'pool':'k8operators_limit',
                'docker_run':'{docker_run}'.format(**config),
                'image':'{docker_image}'.format(**config),
                'name':'pipe-ecuador-load',
                'dag':dag,
                'retries':5,
                'max_retry_delay': timedelta(hours=5),
                'arguments':['load_ecuador_vms_data',
                             '{{ macros.ds_add(ds, -2) }}',
                             '{ecuador_vms_gcs_path}'.format(**config),
                             '{project_id}:{ecuador_vms_bq_dataset_table}'.format(**config)]
            })

            if config.get('is_fetch_enabled', False):
                # The Ecuatorian API brings results from 2 days before the requested date.
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
                                 '-d {ds}'.format(**config),
                                 '-o {ecuador_vms_gcs_path}/'.format(**config),
                                 '-rtr {}'.format(config.get('ecuador_api_max_retries', 3))]
                })
                dag >> fetch >> filter_the_query_date >> load
            else:
                # You need to setup the source_gcs_path/s Airflow Variable
                for source_existence in self.source_gcs_sensors(dag, date='{ds}.json.gz'.format(**config)):
                    dag >> source_existence >> filter_the_query_date >> load


        return dag

pipe_vms_ecuador_api_dag = PipeVMSEcuadorDagFactory().build(PIPELINE)
