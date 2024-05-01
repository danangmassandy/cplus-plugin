import traceback

from functools import partial

from qgis.core import Qgis

from ..models.base import ScenarioResult
from ..utils import FileUtils
from ..tasks import ScenarioAnalysisTask
from .request import CplusApiRequest, JOB_COMPLETED_STATUS, JOB_STOPPED_STATUS


class ScenarioAnalysisTaskApiClient(ScenarioAnalysisTask):
    def run(self):
        """Run scenario analysis using API."""
        self.request = CplusApiRequest()
        self.scenario_directory = self.get_scenario_directory()
        FileUtils.create_new_dir(self.scenario_directory)
        try:
            self.__execute_scenario_analysis()
        except Exception as ex:
            self.log_message(traceback.format_exc(), info=False)
            err = f"Problem executing scenario analysis in the server side: {ex}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.error = ex
            self.cancel_task()
            return False
        return True

    def __execute_scenario_analysis(self):
        # TODO: validate all layers exists in server
        # submit scenario detail to the API
        # TODO: build json
        scenario_detail = {}
        # scenario_uuid = self.request.submit_scenario_detail(scenario_detail)
        scenario_uuid = "c8880388-81df-438b-ab66-4e4dd5cd9f59"
        # execute scenario detail
        self.request.execute_scenario(scenario_uuid)
        # fetch status by interval
        status_pooling = self.request.fetch_scenario_status(scenario_uuid)
        status_pooling.on_response_fetched = self.__update_scenario_status
        status_response = status_pooling.results()
        # if success, fetch output list
        scenario_status = status_response.get("status", "")
        if scenario_status == JOB_COMPLETED_STATUS:
            self.__retrieve_scenario_outputs(scenario_uuid)
        elif scenario_status == JOB_STOPPED_STATUS:
            scenario_error = status_response.get("errors", "Unknown error")
            raise Exception(scenario_error)

    def __update_scenario_status(self, response):
        self.set_status_message(response.get("progress_text", ""))
        self.update_progress(response.get("progress", 0))

    def __retrieve_scenario_outputs(self, scenario_uuid):
        # TODO: retrieve scenario outputs
        # TODO: ensure the scenario and output attribute will be the same with ScenarioAnalysisTask
        self.scenario_result = ScenarioResult(
            scenario=self.scenario, scenario_directory=self.scenario_directory
        )
