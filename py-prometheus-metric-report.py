#!/usr/bin/env python

from collections import defaultdict
from markdown import markdown
from markdown.extensions.toc import TocExtension
from tqdm import tqdm
import argparse
import concurrent.futures
import pdfkit
import requests
import threading
import time

import urllib3
urllib3.disable_warnings()

class py_prometheus_metric_doc_preparer(object):
    def __parse_cli_args(self):
        """CLI parser"""
        parser = argparse.ArgumentParser(
            description='Produce Prometheus markdown documentation and based on that - pdf report.',
            usage='%(prog)s [options]',
            epilog="Use wisely..")
        parser.add_argument(
            '-m',
            '--metrics-address',
            action='append',
            default=[],
            dest='metrics_address',
            help='Prometheus API url')
        parser.add_argument(
            '--label-limiter',
            action='store',
            default=20,
            dest='label_limit',
            help='Label print limit in pdf')
        parser.add_argument(
            '--no-pdf',
            action='store_true',
            default=False,
            dest='no_pdf',
            help='Do not generate pdf')
        parser.add_argument(
            '--pdf-only',
            action='store_true',
            default=False,
            dest='pdf_only',
            help='Generate pdf file only')
        self.__args = parser.parse_args()

    def __init__(self):
        """Main function"""
        self.__parse_cli_args()
        self.__metrics = list()
        self.__detailed_metrics = dict()

        if not self.__args.pdf_only:
            self.__metrics = self.__make_initial_call_for_metrics()
            self.__detailed_metrics = self.__make_detailed_call_for_metrics()
            self.__generate_md_doc()
        if not self.__args.no_pdf:
            self.__generate_pdf_doc()

    def __make_initial_call_for_metrics(self) -> list:
        # For unique list set
        __metrics = set()
        for address in self.__args.metrics_address:
            r = requests.get(f"{address}/api/v1/label/__name__/values", verify=False)
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

        thread_local = threading.local()

        def download_parallel(urls, info):
            def download_data(url):
                def get_session():
                    if not hasattr(thread_local, "session"):
                        thread_local.session = requests.Session()
                    return thread_local.session

                session = get_session()
                with session.get(url, verify=False) as response:
                    return response

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                return list(tqdm(executor.map(download_data, urls), total=len(urls), desc=info, ascii=True))

        detailed_metrics = defaultdict(new_metrics_grup)
        GROUP_KEY = '__name__'
        detail_requests = list()
        metadata_requests = list()

        # array[start:stop:step]
        for metric in tqdm(self.__metrics[::], desc="List of requests", ascii=True):
            for address in self.__args.metrics_address:
                detail_requests.append(f"{address}/api/v1/query?query={metric}")
                metadata_requests.append(f"{address}/api/v1/targets/metadata?metric={metric}")

        for r in tqdm(download_parallel(detail_requests, "Detail info requests"), desc="Parsing detail info", ascii=True):
            #TODO: add exception if not jsonable
            if r.status_code == 200 and r.json()['status'] == 'success':
                for result in r.json()['data']['result']:
                    group = result['metric'].pop(GROUP_KEY)
                    for label, value in result['metric'].items():
                        detailed_metrics[group]['labels'][label].add(value)
                    detailed_metrics[group]['freshness'].add(result['value'][0] or 0)

        for m in tqdm(download_parallel(metadata_requests, "Metadata info requests"), desc="Parsing medatada info", ascii=True):
            if m.status_code == 200 and m.json()['status'] == 'success':
                for result in m.json()['data']:
                    group = str(m.url).split("=")[1]
                    detailed_metrics[group]['metric_type'].add(result['type'])
                    detailed_metrics[group]['help'].add(result['help'])
                    detailed_metrics[group]['found_in'].add(result['target']['instance'])
                    detailed_metrics[group]['jobs'].add(result['target']['job'])

        return detailed_metrics

    def __generate_md_doc(self) -> bool:
        with open("prometheus_metric_report.md","w") as f:
            id = 1
            f.write(f"# Metric report [{time.strftime('%d-%m-%Y %H:%M')}]\n\n")
            for metric, value in tqdm(self.__detailed_metrics.items(), desc="MD creation", ascii=True):
                #METRIC NAME
                f.write(f"## {id}) {str(metric)}\n\n")
                id+=1

                #HELP
                f.write(f"### Help\n\n{list(value['help'] or ['unavailable'])}\n\n")

                #METRIC TYPE
                f.write(f"### Type\n\n{list(value['metric_type'] or ['unavailable'])}\n\n")

                #APPEARS IN JOBS
                f.write(f"### Appears in jobs\n\n{list(value['jobs'] or ['unavailable'])}\n\n")

                #APPEARS ON INSTANCES
                f.write(f"### Appears on instances\n\n{list(value['found_in'] or ['unavailable'])}\n\n")

                #FRESHNES
                freshness = list([
                    str(format(time.time() - max(value['freshness'] or [0]), '.2f') + 's'),
                    str(format(time.time() - min(value['freshness'] or [0]), '.2f') + 's')
                ])
                f.write(f"### Freshness\n\n{freshness}\n\n")

                #TABLE with labels and counters
                f.write(f"### Labels\n\n")
                f.write("| Label | Size | Values |\n")
                f.write("| --- | --- | --- |\n")
                for label, v in value['labels'].items():
                    f.write(f"| {label} | {len(v)} | {list(v)[:self.__args.label_limit:]}{'<br>__MORE DATA BUT TURNCATED__'*(len(v) > self.__args.label_limit)} |\n")
                f.write(f"\n\n")

        return True

    def __generate_pdf_doc(self) -> bool:
        input_filename = 'prometheus_metric_report.md'
        output_filename = 'prometheus_metric_report.pdf'
        options = {'quiet': '', 'footer-right': '[page] of [topage]', 'zoom': 1.5}

        with open(input_filename, 'r') as f:
            html = markdown(f.read(), output_format='html5', extensions=['tables', TocExtension(baselevel=2)])

        pdfkit.from_string(html, output_filename, options=options, css="styles/monospace.css")
        return True

if __name__ == '__main__':
    py_prometheus_metric_doc_preparer()
