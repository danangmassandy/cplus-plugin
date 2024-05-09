import os
import time
import requests
import json

from ..utils import log


JOB_COMPLETED_STATUS = "Completed"
JOB_CANCELLED_STATUS = "Cancelled"
JOB_STOPPED_STATUS = "Stopped"


def log_response(response, request_name):
    log(f"****Response - {request_name} *****")
    if isinstance(response, dict):
        log(json.dumps(response))
    else:
        log(response)


class CplusApiRequestError(Exception):
    """Error class for Cplus API Request."""

    def __init__(self, message):
        """init."""
        if isinstance(message, dict):
            message = json.dumps(message)
        log(message, info=False)
        self.message = message
        super().__init__(self.message)


class CplusApiPooling:
    """Fetch/Post url with pooling."""

    DEFAULT_LIMIT = 3600  # Check result maximum 3600 times
    DEFAULT_INTERVAL = 1  # Interval of check results
    FINAL_STATUS_LIST = [JOB_COMPLETED_STATUS, JOB_CANCELLED_STATUS, JOB_STOPPED_STATUS]

    def __init__(
        self,
        url,
        headers={},
        method="GET",
        data=None,
        max_limit=None,
        interval=None,
        on_response_fetched=None,
    ):
        """init."""
        self.url = url
        self.headers = headers
        self.current_repeat = 0
        self.method = method
        self.data = data
        self.limit = max_limit or self.DEFAULT_LIMIT
        self.interval = interval or self.DEFAULT_INTERVAL
        self.on_response_fetched = on_response_fetched

    def __call_api(self):
        if self.method == "GET":
            return requests.get(self.url, headers=self.headers)
        return requests.post(self.url, self.data, headers=self.headers)

    def results(self):
        """Return results of data."""
        self.current_repeat += 1
        if self.limit != -1 and self.current_repeat >= self.limit:
            raise requests.exceptions.Timeout()
        try:
            response = self.__call_api()
            if response.status_code != 200:
                raise CplusApiRequestError(f"{response.status_code} - {response.text}")
            result = response.json()
            log_response(result, "CplusApiRequest - status")
            if self.on_response_fetched:
                self.on_response_fetched(result)
            if result["status"] in self.FINAL_STATUS_LIST:
                return result
            else:
                time.sleep(self.interval)
                return self.results()
        except requests.exceptions.Timeout:
            time.sleep(self.interval)
            return self.results()


class TrendsApiUrl:
    """Trends API Urls."""

    def __init__(self) -> None:
        self.base_url = "https://api2.trends.earth"

    @property
    def auth(self):
        return f"{self.base_url}/auth"


class CplusApiUrl:
    """Cplus API Urls."""

    def __init__(self):
        self._api_token = None
        # TODO: retrieve base_url from QgisSettings
        self.base_url = "http://0.0.0.0:9999/api/v1"
        self.trends_urls = TrendsApiUrl()

    @property
    def api_token(self):
        if self._api_token:
            # TODO: validate its validity
            return self._api_token
        # fetch token from Trends Earth API
        # TODO: retrieve username+pw from secured QgisSettings
        username = os.getenv("CPLUS_USERNAME", "")
        pw = os.getenv("CPLUS_PASSWORD", "")

        username = "zakki@kartoza.com"
        pw = "94WF2R"

        response = requests.post(
            self.trends_urls.auth, json={"email": username, "password": pw}
        )
        if response.status_code != 200:
            raise CplusApiRequestError(
                "Error authenticating to Trends Earth API: "
                f"{response.status_code} - {response.text}"
            )
        result = response.json()
        access_token = result.get("access_token", None)
        if access_token is None:
            raise CplusApiRequestError(
                "Error authenticating to Trends Earth API: missing access_token!"
            )
        self._api_token = access_token
        return access_token

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_token}",
        }

    def layer_detail(self, scenario_uuid):
        return f"{self.base_url}/layer/{scenario_uuid}/"

    def scenario_submit(self, plugin_version=None):
        url = f"{self.base_url}/scenario/submit/"
        if plugin_version:
            url += f"?plugin_version={plugin_version}"
        return url

    def scenario_execute(self, scenario_uuid):
        return f"{self.base_url}/scenario/{scenario_uuid}/execute/"

    def scenario_status(self, scenario_uuid):
        return f"{self.base_url}/scenario/{scenario_uuid}/status/"

    def scenario_cancel(self, scenario_uuid):
        return f"{self.base_url}/scenario/{scenario_uuid}/cancel/"

    def scenario_detail(self, scenario_uuid):
        return f"{self.base_url}/scenario/{scenario_uuid}/detail/"

    def scenario_output_list(self, scenario_uuid):
        return f"{self.base_url}/scenario_output/{scenario_uuid}/list/?download_all=true&page=1&page_size=100"


class CplusApiRequest:
    """Request to Cplus API."""

    page_size = 50

    def __init__(self) -> None:
        self.urls = CplusApiUrl()

    def get(self, url):
        """GET requests."""
        log_response(self.urls.headers, "headers")
        return requests.get(url, headers=self.urls.headers)

    def post(self, url, data: json):
        """GET requests."""
        return requests.post(url, json=data, headers=self.urls.headers)


    def check_layer(self, layer_uuid):
        response = self.get(self.urls.layer_detail(layer_uuid))
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return response

    def submit_scenario_detail(self, scenario_detail):
        response = self.post(self.urls.scenario_submit(), scenario_detail)
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return response["uuid"]

    def execute_scenario(self, scenario_uuid):
        response = self.get(self.urls.scenario_execute(scenario_uuid))
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return True

    def fetch_scenario_status(self, scenario_uuid):
        url = self.urls.scenario_status(scenario_uuid)
        return CplusApiPooling(url, self.urls.headers)

    def cancel_scenario(self, scenario_uuid):
        response = self.get(self.urls.scenario_cancel(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return True

    def fetch_scenario_output_list(self, scenario_uuid):
        response = self.get(self.urls.scenario_output_list(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return result

    def fetch_scenario_detail(self, scenario_uuid):
        response = self.get(self.urls.scenario_detail(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return result
