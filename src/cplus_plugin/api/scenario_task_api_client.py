import concurrent.futures
import json
import os
import traceback
from urllib.parse import urlparse, parse_qs

import requests
from qgis.core import Qgis

from .multipart_upload import upload_part
from .request import CplusApiRequest, JOB_COMPLETED_STATUS, JOB_STOPPED_STATUS, CHUNK_SIZE
from ..conf import Settings
from ..models.base import Activity, NcsPathway
from ..models.base import ScenarioResult
from ..tasks import ScenarioAnalysisTask
from ..utils import FileUtils, CustomJsonEncoder

SCENARIO_DETAIL = {
    "scenario_name": "Scenario with Activity 1",
    "scenario_desc": "Test",
    "extent": [
        878529.3786140494,
        911063.0818645271,
        7216308.751738624,
        7279753.465204147
    ],
    "snapping_enabled": False,
    "reference_layer": "a45473bb-c56e-43bc-bbc5-2c7a34ebe89a",
    "sieve_enabled": False,
    "sieve_threshold": 10,
    "mask_layer": "",
    "suitability_index": 0,
    "carbon_coefficient": 0,
    "rescale_values": False,
    "resampling_method": "0",
    "priority_layers": [
        {
            "uuid": "3e0c7dff-51f2-48c5-a316-15d9ca2407cb",
            "name": "Ecological Infrastructure inverse",
            "description": "Placeholder text for ecological infrastructure inverse",
            "path": "ei_all_gknp_clip_norm.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "88c1c7dd-c5d1-420c-a71c-a5c595c1c5be",
            "name": "Ecological Infrastructure",
            "description": "Placeholder text for ecological infrastructure",
            "path": "ei_all_gknp_clip_norm.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "9ab8c67a-5642-4a09-a777-bd94acfae9d1",
            "name": "Biodiversity norm",
            "description": "Placeholder text for biodiversity norm",
            "path": "biocombine_clip_norm.tif",
            "selected": False,
            "user_defined": False,
            "groups": [
                {
                    "uuid": "21a30a80-eb49-4c5e-aff6-558123688e09",
                    "name": "Climate Resilience",
                    "value": "5"
                }
            ]
        },
        {
            "uuid": "c2dddd0f-a430-444a-811c-72b987b5e8ce",
            "name": "Biodiversity norm inverse",
            "description": "Placeholder text for biodiversity norm inverse",
            "path": "biocombine_clip_norm_inverse.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "c931282f-db2d-4644-9786-6720b3ab206a",
            "name": "Social norm",
            "description": "Placeholder text for social norm ",
            "path": "social_int_clip_norm.tif",
            "selected": True,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "f5687ced-af18-4cfc-9bc3-8006e40420b6",
            "name": "Social norm inverse",
            "description": "Placeholder text for social norm inverse",
            "path": "social_int_clip_norm_inverse.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "fce41934-5196-45d5-80bd-96423ff0e74e",
            "name": "Climate Resilience norm",
            "description": "Placeholder text for climate resilience norm",
            "path": "cccombo_clip_norm.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        },
        {
            "uuid": "fef3c7e4-0cdf-477f-823b-a99da42f931e",
            "name": "Climate Resilience norm inverse",
            "description": "Placeholder text for climate resilience",
            "path": "cccombo_clip_norm_inverse.tif",
            "selected": False,
            "user_defined": False,
            "groups": []
        }
    ],
    "priority_layer_groups": [
        {
            "name": "Climate Resilience",
            "value": "0",
            "layers": [
                "Biodiversity norm"
            ]
        },
        {
            "name": "Finance - Net Present value",
            "value": "0",
            "layers": []
        },
        {
            "name": "Finance - Years Experience",
            "value": "0",
            "layers": []
        },
        {
            "name": "Finance - Carbon",
            "value": "0",
            "layers": []
        },
        {
            "name": "Livelihood",
            "value": "0",
            "layers": []
        },
        {
            "name": "Policy",
            "value": "0",
            "layers": []
        },
        {
            "name": "Ecological infrastructure",
            "value": "0",
            "layers": []
        },
        {
            "name": "Finance - Market Trends",
            "value": "0",
            "layers": []
        },
        {
            "name": "Biodiversity",
            "value": "0",
            "layers": []
        }
    ],
    "activities": [
        {
            "uuid": "d0fa1fa6-7c27-49af-83fa-6b153d1eda0c",
            "name": "Alien Plant Removal",
            "description": "Description",
            "path": "",
            "layer_type": -1,
            "user_defined": False,
            "pathways": [
                {
                    "uuid": "d0fa1fa6-7c27-49af-83fa-6b153d1eda0c",
                    "name": "Alien Plant Removal",
                    "description": "Alien Plant Class.",
                    "path": "",
                    "layer_type": 0,
                    "layer_uuid": "d0fa1fa6-7c27-49af-83fa-6b153d1eda0c",
                    "carbon_paths": [],
                    "carbon_uuids": []
                }
            ],
            "priority_layers": [
                {
                    "uuid": "c931282f-db2d-4644-9786-6720b3ab206a",
                    "name": "Social norm",
                    "description": "Placeholder text for social norm ",
                    "path": "",
                    "selected": True,
                    "user_defined": False,
                    "groups": []
                },
                {
                    "uuid": "88c1c7dd-c5d1-420c-a71c-a5c595c1c5be",
                    "name": "Ecological Infrastructure",
                    "description": "Placeholder text for ecological infrastructure",
                    "path": "",
                    "selected": False,
                    "user_defined": False,
                    "groups": []
                },
                {
                    "uuid": "9ab8c67a-5642-4a09-a777-bd94acfae9d1",
                    "name": "Biodiversity norm",
                    "description": "Placeholder text for biodiversity norm",
                    "path": "",
                    "selected": False,
                    "user_defined": False,
                    "groups": [
                        {
                            "uuid": "21a30a80-eb49-4c5e-aff6-558123688e09",
                            "name": "Climate Resilience",
                            "value": "5"
                        }
                    ]
                }
            ],
            "layer_styles": {
                "scenario_layer": {
                    "color": "#6f6f6f",
                    "style": "solid",
                    "outline_width": "0",
                    "outline_color": "35,35,35,0"
                },
                "activity_layer": {
                    "color_ramp": {
                        "colors": "8",
                        "inverted": "0",
                        "rampType": "colorbrewer",
                        "schemeName": "Greys"
                    },
                    "ramp_type": "colorbrewer"
                }
            }
        }
    ]
}

def separate_url_and_params(url):
    parsed_url = urlparse(url)
    url_without_params = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    params = parse_qs(parsed_url.query)
    return url_without_params, params

def download_file(url, local_filename):
    parent_dir = os.path.dirname(local_filename)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def clean_filename(filename):
    """Creates a safe filename by removing operating system
    invalid filename characters.

    :param filename: File name
    :type filename: str

    :returns A clean file name
    :rtype str
    """
    characters = " %:/,\[]<>*?"

    for character in characters:
        if character in filename:
            filename = filename.replace(character, "_")

    return filename

class ScenarioAnalysisTaskApiClient(ScenarioAnalysisTask):
    def run(self):
        """Run scenario analysis using API."""
        self.request = CplusApiRequest()
        self.scenario_directory = self.get_scenario_directory()
        self.log_message(os.path.dirname(os.path.abspath(__file__)))
        self.file_mapping_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'uploaded_layer.json'
        )
        self.file_mapping_path = '/home/zamuzakki/PycharmProjects/Kartoza/CI-CPLUS/cplus-plugin/src/cplus_plugin/api/uploaded_layer.json'
        FileUtils.create_new_dir(self.scenario_directory)

        try:
            self.upload_layers()
        except Exception as e:
            self.log_message(str(e))

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

    def run_upload(self, file_path, component_type):
        # start upload
        upload_params = self.request.start_upload_layer(file_path, component_type)
        upload_id = upload_params['multipart_upload_id']
        layer_uuid = upload_params['uuid']
        upload_urls = upload_params['upload_urls']
        # do upload by chunks
        items = []
        idx = 0
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                url_item = upload_urls[idx]
                self.log_message(f"starting upload part {url_item['part_number']}")
                part_item = upload_part(
                    url_item['url'], chunk, url_item['part_number'])
                items.append(part_item)
                self.log_message(f"finished upload part {url_item['part_number']}")
                idx += 1
        self.log_message(f'***Total upload_urls: {len(upload_urls)}')
        self.log_message(f'***Total chunks: {idx}')
        # finish upload
        result = self.request.finish_upload_layer(layer_uuid, upload_id, items)
        return result

    def run_parallel_upload(self, upload_dict):
        file_paths = list(upload_dict.keys())
        component_types = list(upload_dict.values())

        final_result = []
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            final_result.extend(list(executor.map(
                self.run_upload,
                file_paths,
                component_types
            )))
        return list(final_result)

    def upload_layers(self):
        files_to_upload = {}

        for activity in self.analysis_activities:
            for pathway in activity.pathways:
                if pathway:
                    if pathway.path and os.path.exists(pathway.path):
                        is_uploaded = self.__is_layer_uploaded(pathway.path)
                        if not is_uploaded:
                            files_to_upload[pathway.path] = 'ncs_pathway'

                    for carbon_path in pathway.carbon_paths:
                        if os.path.exists(carbon_path):
                            is_uploaded = self.__is_layer_uploaded(carbon_path)
                            if not is_uploaded:
                                files_to_upload[carbon_path] = 'ncs_carbon'

            for priority_layer in activity.priority_layers:
                if priority_layer:
                    if priority_layer['path'] and os.path.exists(priority_layer['path']):
                        is_uploaded = self.__is_layer_uploaded(priority_layer['path'])
                        if not is_uploaded:
                            files_to_upload[priority_layer['path']] = 'priority_layer'

        reference_layer = self.get_settings_value(Settings.SNAP_LAYER, default="")

        if reference_layer:
            is_uploaded = self.__is_layer_uploaded(reference_layer)
            if not is_uploaded:
                files_to_upload[reference_layer] = 'reference_layer'

        mask_layer = self.get_settings_value(
            Settings.SIEVE_MASK_PATH, default=""
        )

        if mask_layer:
            is_uploaded = self.__is_layer_uploaded(mask_layer)
            if not is_uploaded:
                files_to_upload[mask_layer] = 'mask_layer'

        # for filepath, component_type in files_to_upload.items():
            # run_upload(filepath, component_type)
        final_results = self.run_parallel_upload(files_to_upload)
        self.log_message(json.dumps(final_results))

        new_uploaded_layer = {}
        for file_path in files_to_upload:
            filename_without_ext = '.'.join(os.path.basename(file_path).split('.')[0:-1])
            for res in final_results:
                if res['name'].startswith(filename_without_ext):
                    new_uploaded_layer[file_path] = res
                    break
        fr = open(self.file_mapping_path, 'r')
        uploaded_layer_dict = json.loads(fr.read())
        fr.close()
        with open(self.file_mapping_path, 'w') as fw:
            uploaded_layer_dict.update(new_uploaded_layer)
            fw.write(json.dumps(uploaded_layer_dict, sort_keys=True, indent=4))

    def __is_layer_uploaded(self, layer_path: str):
        # TODO: Check uploaded layer value from QGIS settings
        with open(self.file_mapping_path, 'r') as f:
            uploaded_layer_dict = json.loads(f.read())
            if layer_path in uploaded_layer_dict:
                is_uploaded = self.request.check_layer(uploaded_layer_dict[layer_path]['uuid'])
                return is_uploaded
            return False

    def __execute_scenario_analysis(self):
        # TODO: validate all layers exists in server
        # submit scenario detail to the API
        # TODO: build json
        self.scenario_detail = SCENARIO_DETAIL
        # scenario_uuid = self.request.submit_scenario_detail(scenario_detail)
        scenario_uuid = "76daec8d-44fc-44a1-a944-f09dffbb249d"

        # # execute scenario detail
        # self.request.execute_scenario(scenario_uuid)
        # # fetch status by interval
        # status_pooling = self.request.fetch_scenario_status(scenario_uuid)
        # status_pooling.on_response_fetched = self.__update_scenario_status
        # status_response = status_pooling.results()
        # # if success, fetch output list
        # scenario_status = status_response.get("status", "")
        self.new_scenario_detail = self.request.fetch_scenario_detail(scenario_uuid)

        scenario_status = JOB_COMPLETED_STATUS
        if scenario_status == JOB_COMPLETED_STATUS:
            self.__retrieve_scenario_outputs(scenario_uuid)
        elif scenario_status == JOB_STOPPED_STATUS:
            scenario_error = status_response.get("errors", "Unknown error")
            raise Exception(scenario_error)

    def __update_scenario_status(self, response):
        self.set_status_message(response.get("progress_text", ""))
        self.update_progress(response.get("progress", 0))

    def create_activity(self, activity: dict, download_dict: list):
        ncs_pathways = []
        for pathway in activity['pathways']:
            if 'layer_uuid' in pathway:
                del pathway['layer_uuid']
            if 'carbon_uuids' in pathway:
                del pathway['carbon_uuids']
            pathway['path'] = download_dict[os.path.basename(pathway['path'])]
            ncs_pathways.append(NcsPathway(**pathway))
        activity['pathways'] = ncs_pathways
        activity['path'] = download_dict[os.path.basename(activity['path'])]
        activity_obj = Activity(**activity)
        return activity_obj

    def set_scenario(self, output_list, download_paths):
        output_fnames = []
        for output in output_list['results']:
            if '_cleaned' in output['filename']:
                output_fnames.append(output['filename'])

        from ..utils import log
        log('WEIGHTING')
        weighted_activities = []
        activities = []

        download_dict = {
            os.path.basename(d): d for d in download_paths
        }

        log(json.dumps(self.new_scenario_detail, cls=CustomJsonEncoder))
        for activity in self.new_scenario_detail['updated_detail']['activities']:
            activities.append(self.create_activity(activity, download_dict))
        for activity in self.new_scenario_detail['updated_detail']['weighted_activities']:
            weighted_activities.append(self.create_activity(activity, download_dict))

        self.analysis_weighted_activities = weighted_activities
        self.analysis_activities = activities
        self.scenario.activities = activities
        self.scenario.weighted_activities = weighted_activities
        self.scenario.priority_layer_groups = self.new_scenario_detail['updated_detail']['priority_layer_groups']

    def __retrieve_scenario_outputs(self, scenario_uuid):
        output_list = self.request.fetch_scenario_output_list(scenario_uuid)
        urls_to_download = []
        download_paths = []
        for output in output_list['results']:
            urls_to_download.append(
                output['url'].replace('https://0.0.0.0:8888', 'http://0.0.0.0:9010')
            )
            if output['is_final_output']:
                download_path = os.path.join(
                    self.scenario_directory,
                    output['filename']
                )
                final_output_path = download_path
                self.output = output['output_meta']
                self.output['OUTPUT'] = final_output_path
            else:
                download_path = os.path.join(
                    self.scenario_directory,
                    output['group'],
                    output['filename']
                )
            download_paths.append(download_path)

        with concurrent.futures.ThreadPoolExecutor(
                max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            executor.map(
                download_file,
                urls_to_download,
                download_paths
            )
        # for idx, download_path in enumerate(download_paths):
        #     download_file(urls_to_download[idx], download_path)

        self.set_scenario(output_list, download_paths)

        self.scenario_result = ScenarioResult(
            scenario=self.scenario,
            scenario_directory=self.scenario_directory,
            analysis_output=self.output,
        )

        self.analysis_priority_layers_groups
