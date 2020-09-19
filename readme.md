# py-prometheus-metric-report

## Desc

Python script to create pdf report of available metrics, their descriptions, apperance nad many others.
Script uses `ThreadPoolExecutor` for better performance.

## Requirements

```bash
pip install -r requirements.txt
```

Also `wkhtmltopdf` will be needed. More info [here](https://github.com/JazzCore/python-pdfkit).

## Usage

```bash
./py-prometheus-metric-report.py \
  --metrics-address http://prometheus.domain.com:9090 \
  --metrics-address https://thanos.domain.com

usage: py-prometheus-metric-report.py [-h] [--metrics-address METRICS_ADDRESS]
                                      [--label-limiter LABEL_LIMIT]

Produce Prometheus pdf report with markdown middle step

optional arguments:
  -h, --help            show this help message and exit
  --metrics-address METRICS_ADDRESS
                        Prometheus API url
  --label-limiter LABEL_LIMIT
                        Label print limit in pdf
```

## Credits

[@amadeuszkryze](https://github.com/amadeuszkryze)

[@majkel94](https://github.com/majkel94)
