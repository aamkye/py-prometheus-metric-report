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

![Runtime](/examples/runtime.png)

```bash
./py-prometheus-metric-report.py \
  -m http://prometheus.domain.com:9090 \
  -m https://thanos.domain.com

usage: py-prometheus-metric-report.py [options]

Produce Prometheus markdown documentation and based on that - pdf report.

optional arguments:
  -h, --help            show this help message and exit
  -m METRICS_ADDRESS, --metrics-address METRICS_ADDRESS
                        Prometheus API url
  --label-limiter LABEL_LIMIT
                        Label print limit in pdf
  --no-pdf              Do not generate pdf
  --pdf-only            Generate pdf file only

Use wisely..
```

## Example
![Sample page](/examples/example.png)

## Credits

[@amadeuszkryze](https://github.com/amadeuszkryze)

[@majkel94](https://github.com/majkel94)
