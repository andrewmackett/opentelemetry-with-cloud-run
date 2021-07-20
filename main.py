#!/usr/bin/env python3
# Copyright 2021 The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import time
import os
import requests

from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

from grpc import ssl_channel_credentials
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

set_global_textmap(CloudTraceFormatPropagator())

tracer_provider = TracerProvider()


TRACING_EXPORT = os.environ.get("TRACING_EXPORT", "console")

if TRACING_EXPORT == "google":
    cloud_trace_exporter = CloudTraceSpanExporter()
elif TRACING_EXPORT == "honeycomb":
    cloud_trace_exporter = OTLPSpanExporter(
        endpoint="api.honeycomb.io:443",
        insecure=False,
        credentials=ssl_channel_credentials(),
        headers=(
            ("x-honeycomb-team", os.environ.get("HONEYCOMB_API_KEY")),
            ("x-honeycomb-dataset", os.environ.get("HONEYCOMB_DATASET")),
        ),
    )
else:
    cloud_trace_exporter = ConsoleSpanExporter()


tracer_provider.add_span_processor(
    BatchSpanProcessor(cloud_trace_exporter)
)
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

url = os.environ.get("URL_TO_CALL", "https://icanhazip.com/")

@app.route("/")
def hello_world():
    # You can still use the OpenTelemetry API as usual to create custom spans
    # within your trace
    with tracer.start_as_current_span("do-work"):
        time.sleep(0.2)
        with tracer.start_as_current_span("example-request"):
            requests.get(url)
            return "Hello, World!"


if __name__ == "__main__":
    app.run(port=8082)