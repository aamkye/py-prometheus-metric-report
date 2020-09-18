#!/usr/bin/env python

from collections import defaultdict
from markdown import markdown
import threading
import concurrent.futures
from tqdm import tqdm
import argparse
import pdfkit
import requests
import time

class py_prometheus_metric_doc_preparer(object):
    def __parse_cli_args(self):
        """CLI parser"""
        parser = argparse.ArgumentParser(
            description='Produce an Ansible Inventory file based on EC2.')
        parser.add_argument(
            '--metrics-address',
            action='append',
            default=[],
            dest='metrics_address',
            help='Dont print output to stdout')
        parser.add_argument(
            '--label-limiter',
            action='store',
            default=20,
            dest='label_limit',
            help='Dont print output to stdout')
        self.__args = parser.parse_args()

    def __init__(self):
        """Main function"""

        self.__metrics = list()
        self.__detailed_metrics = dict()
        self.__parse_cli_args()
        self.__metrics = self.__make_initial_call_for_metrics()
        self.__detailed_metrics = self.__make_detailed_call_for_metrics()
        self.__generate_md_doc()
        self.__generate_pdf_doc()

    def __make_initial_call_for_metrics(self) -> list:
        # For unique list set
        __metrics = set()
        for address in self.__args.metrics_address:
            r = requests.get(f"{address}/api/v1/label/__name__/values")
            if r.json()['status'] == 'success':
                for metric in r.json()['data']:
                    __metrics.add(metric)

        # For ASC sort purposes
        __metrics = list(__metrics)
        __metrics.sort()
        return __metrics

    def __make_detailed_call_for_metrics(self) -> dict:
        def new_metrics_grup():
            """Auxiliary function to prepare data structure for new group"""
            return {
                'labels': defaultdict(set),
                'freshness': set(),
                'metric_type': set(),
                'help': set(),
                'found_in': set(),
                'jobs': set(),
            }

        # thread_local = threading.local()

        # def get_session():
        #     if not hasattr(thread_local, "session"):
        #         thread_local.session = requests.Session()
        #     return thread_local.session

        # def download_site(url):
        #     session = get_session()
        #     with session.get(url) as response:
        #         print(f"Read {len(response.content)} from {url}")

        # def download_all_sites(sites):
        #     with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        #         executor.map(download_site, sites)

        detailed_metrics = defaultdict(new_metrics_grup)
        GROUP_KEY = '__name__'

        session = requests.session()

        # detail_requests = list()
        # metadata_requests = list()

        # array[start:stop:step]
        for metric in tqdm(self.__metrics[100:110:]):
            for address in self.__args.metrics_address:
                details = f"{address}/api/v1/query?query={metric}"
                metadata = f"{address}/api/v1/targets/metadata?metric={metric}"


                r = session.get(details)
                m = session.get(metadata)

                #TODO: add exception if not jsonable
                if r.status_code == 200 and r.json()['status'] == 'success':
                    for result in r.json()['data']['result']:
                        group = result['metric'].pop(GROUP_KEY)
                        for label, value in result['metric'].items():
                            detailed_metrics[group]['labels'][label].add(value)
                        detailed_metrics[group]['freshness'].add(result['value'][0])

                if m.status_code == 200 and m.json()['status'] == 'success':
                    for result in m.json()['data']:
                        detailed_metrics[group]['metric_type'].add(result['type'])
                        detailed_metrics[group]['help'].add(result['help'])
                        detailed_metrics[group]['found_in'].add(result['target']['instance'])
                        detailed_metrics[group]['jobs'].add(result['target']['job'])

        return detailed_metrics

    def __generate_md_doc(self) -> bool:
        with open("prometheus_metric_report.md","w") as f:
            id = 1
            f.write(f"# Metrics report [{time.strftime('%H:%M %d-%m-%Y')}]\n\n")
            for metric, value in self.__detailed_metrics.items():
                #METRIC NAME
                f.write(f"## {id}) {str(metric)}\n\n")
                id+=1

                #HELP
                f.write(f"### Help\n\n{list(value['help']) or 'unavailable'}\n\n")

                #METRIC TYPE
                f.write(f"### Type\n\n{list(value['metric_type']) or 'unavailable'}\n\n")

                #APPEARS IN JOBS
                f.write(f"### Appears in jobs\n\n{list(value['jobs']) or 'unavailable'}\n\n")

                #APPEARS ON INSTANCES
                f.write(f"### Appears on instances\n\n{list(value['found_in']) or 'unavailable'}\n\n")

                #FRESHNES
                f.write(f"### Freshness\n\n{format(time.time() - max(value['freshness']), '.2f')}s - {format(time.time() - min(value['freshness']), '.2f')}s\n\n")

                #TABLE with labels and counters
                f.write(f"### Labels\n\n")
                f.write("| Label | Size | Values |\n")
                f.write("| :--- | :--- | :--- |\n")
                for label, v in value['labels'].items():
                    f.write(f"| {label} | {len(v)} | {list(v)[:self.__args.label_limit:]}{'*'*(len(v) > self.__args.label_limit)} |\n\n\n")
                f.write(f"---\n\n")

        return True

    def __generate_pdf_doc(self) -> bool:
        input_filename = 'prometheus_metric_report.md'
        output_filename = 'prometheus_metric_report.pdf'
        options = {'quiet': ''}

        with open(input_filename, 'r') as f:
            html_text = markdown(f.read(), output_format='html5', extensions=['extra', 'tables'])

        pdfkit.from_string(html_text, output_filename, options=options, css="monospace.css")
        return True

if __name__ == '__main__':
    py_prometheus_metric_doc_preparer()
