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
from ..utils import FileUtils, CustomJsonEncoder, todict


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

        self.build_scenario_detail_json()
        self.log_message(json.dumps(self.scenario_detail))

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
        self.log_message(f"Uploading {file_path} as {component_type}")
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
        self.log_message(f"{layer_uuid} {upload_id} {items}")
        self.log_message(json.dumps(upload_params))

        if upload_id:
            result = self.request.finish_upload_layer(layer_uuid, upload_id, items)
        else:
            layer_detail = self.request.get_layer_detail(layer_uuid)
            result = {
                "name": layer_detail['filename'],
                "size": layer_detail['size'],
                "uuid": layer_detail['uuid']
            }
        return result

    def run_parallel_upload(self, upload_dict):
        file_paths = list(upload_dict.keys())
        component_types = list(upload_dict.values())

        final_result = []
        # for idx, fp in enumerate(file_paths):
        #     result = self.run_upload(fp, component_types[idx])
        #     final_result.append(result)
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            final_result.extend(list(executor.map(
                self.run_upload,
                file_paths,
                component_types
            )))
        return list(final_result)

    def get_layer_mapping(self):
        fr = open(self.file_mapping_path, 'r')
        uploaded_layer_dict = json.loads(fr.read())
        fr.close()
        return uploaded_layer_dict

    def upload_layers(self):
        files_to_upload = {}

        for activity in self.analysis_activities:
            for pathway in activity.pathways:
                if pathway:
                    if pathway.path and os.path.exists(pathway.path):
                        is_uploaded = self.__is_layer_uploaded(pathway.path)
                        self.log_message(str(is_uploaded))
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

        sieve_enabled = self.get_settings_value(
            Settings.SIEVE_ENABLED, default=False, setting_type=bool
        )
        self.log_message(str(f"sieve_enabled: {sieve_enabled}"))

        if sieve_enabled:
            sieve_mask_layer = self.get_settings_value(
                Settings.SIEVE_MASK_PATH, default=""
            )
            self.log_message(str(f"sieve_mask_layer: {sieve_mask_layer}"))

            if sieve_mask_layer:
                is_uploaded = self.__is_layer_uploaded(sieve_mask_layer)
                if not is_uploaded:
                    files_to_upload[sieve_mask_layer] = 'sieve_mask_layer'

            snapping_enabled = self.get_settings_value(
                Settings.SNAPPING_ENABLED, default=False, setting_type=bool
            )
            if snapping_enabled:
                reference_layer = self.get_settings_value(Settings.SNAP_LAYER, default="")
                self.log_message(str(f"reference_layer: {reference_layer}"))
                if reference_layer:
                    is_uploaded = self.__is_layer_uploaded(reference_layer)
                    if not is_uploaded:
                        files_to_upload[reference_layer] = 'snap_layer'

        masking_layers = self.get_masking_layers()
        for masking_layer in masking_layers:
            is_uploaded = self.__is_layer_uploaded(masking_layer)
            if not is_uploaded:
                files_to_upload[masking_layer] = 'mask_layer'

        # for filepath, component_type in files_to_upload.items():
            # run_upload(filepath, component_type)
        self.log_message(json.dumps(files_to_upload))
        final_results = self.run_parallel_upload(files_to_upload)
        self.log_message(json.dumps(final_results))

        new_uploaded_layer = {}
        for file_path in files_to_upload:
            filename_without_ext = '.'.join(os.path.basename(file_path).split('.')[0:-1])
            for res in final_results:
                if res['name'].startswith(filename_without_ext):
                    new_uploaded_layer[file_path] = res
                    break

        uploaded_layer_dict = self.get_layer_mapping()
        with open(self.file_mapping_path, 'w') as fw:
            uploaded_layer_dict.update(new_uploaded_layer)
            fw.write(json.dumps(uploaded_layer_dict, sort_keys=True, indent=4))

    def __is_layer_uploaded(self, layer_path: str):
        # TODO: Check uploaded layer value from QGIS settings
        uploaded_layer_dict = self.get_layer_mapping()
        if layer_path in uploaded_layer_dict:
            is_uploaded = 'uuid' in self.request.get_layer_detail(uploaded_layer_dict[layer_path]['uuid'])
            return is_uploaded
        return False

    def build_scenario_detail_json(self):
        # TODO: Get layer UUID from QGIS settings
        old_scenario_dict = json.loads(json.dumps(todict(self.scenario), cls=CustomJsonEncoder))
        uploaded_layer_dict = self.get_layer_mapping()
        sieve_enabled = self.get_settings_value(Settings.SIEVE_ENABLED, default=False)
        sieve_threshold =float(
            self.get_settings_value(Settings.SIEVE_THRESHOLD, default=10.0)
        )
        sieve_mask_path = self.get_settings_value(
            Settings.SIEVE_MASK_PATH, default=""
        )
        snapping_enabled = self.get_settings_value(
            Settings.SNAPPING_ENABLED, default=False, setting_type=bool
        ) if sieve_enabled else False
        snap_layer_path = self.get_settings_value(
            Settings.SNAP_LAYER, default="", setting_type=str
        ) if snapping_enabled else False

        suitability_index = float(
            self.get_settings_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
        )
        carbon_coefficient = float(
            self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
        )
        snap_rescale = self.get_settings_value(
            Settings.RESCALE_VALUES, default=False, setting_type=bool
        )
        resampling_method = self.get_settings_value(
            Settings.RESAMPLING_METHOD, default=0
        )
        masking_layers = self.get_masking_layers()
        mask_layer_uuids = [
            obj['uuid'] for fp, obj in self.get_layer_mapping().items() if fp in masking_layers
        ]

        for activity in old_scenario_dict['activities']:
            activity['layer_type'] = 0
            for pathway in activity['pathways']:
                if pathway:
                    if pathway['path'] and os.path.exists(pathway['path']):
                        if uploaded_layer_dict.get(pathway['path'], None):
                            pathway['uuid'] = uploaded_layer_dict.get(pathway['path'])['uuid']
                            pathway['layer_uuid'] = pathway['uuid']
                            pathway['layer_type'] = 0

                    carbon_uuids = []
                    for carbon_path in pathway['carbon_paths']:
                        if os.path.exists(carbon_path):
                            if uploaded_layer_dict(carbon_path, None):
                                carbon_uuids.append(uploaded_layer_dict(carbon_path))
                    pathway['carbon_uuids'] = carbon_uuids

            new_priority_layers = []
            for priority_layer in activity['priority_layers']:
                if priority_layer:
                    if priority_layer['path'] and os.path.exists(priority_layer['path']):
                        if uploaded_layer_dict.get(priority_layer['path'], None):
                            priority_layer['uuid'] = uploaded_layer_dict.get(priority_layer['path'])['uuid']
                            priority_layer['layer_uuid'] = priority_layer['uuid']
                            new_priority_layer.append(priority_layer)
            activity['priority_layers'] = new_priority_layers

        self.scenario_detail = {
            'scenario_name': old_scenario_dict['name'],
            'scenario_desc': old_scenario_dict['description'],
            'snapping_enabled': snapping_enabled if sieve_enabled else False,
            'snap_layer': snap_layer_path,
            'snap_layer_uuid': uploaded_layer_dict.get(snap_layer_path, "")['uuid'],
            'pathway_suitability_index': suitability_index,
            'carbon_coefficient': carbon_coefficient,
            'snap_rescale': snap_rescale,
            'snap_method': resampling_method,
            'sieve_enabled': sieve_enabled,
            'sieve_threshold': sieve_threshold,
            'sieve_mask_path': sieve_mask_path,
            'sieve_mask_uuid': uploaded_layer_dict.get(sieve_mask_path, "")['uuid'],
            'mask_path': ', '.join(masking_layers),
            'mask_layer_uuids': mask_layer_uuids,
            'extent': old_scenario_dict['extent']['bbox'],
            'priority_layer_groups': old_scenario_dict.get('priority_layer_groups', []),
            'priority_layers': old_scenario_dict['activities'][0]['priority_layers'],
            'activities': old_scenario_dict['activities']
        }

    def __execute_scenario_analysis(self):
        # TODO: validate all layers exists in server
        # submit scenario detail to the API
        # TODO: build json
        scenario_uuid = self.request.submit_scenario_detail(self.scenario_detail)
        # scenario_uuid = "76daec8d-44fc-44a1-a944-f09dffbb249d"

        # execute scenario detail
        self.request.execute_scenario(scenario_uuid)
        # fetch status by interval
        status_pooling = self.request.fetch_scenario_status(scenario_uuid)
        status_pooling.on_response_fetched = self.__update_scenario_status
        status_response = status_pooling.results()
        # if success, fetch output list
        scenario_status = status_response.get("status", "")
        self.new_scenario_detail = self.request.fetch_scenario_detail(scenario_uuid)

        # scenario_status = JOB_COMPLETED_STATUS
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
