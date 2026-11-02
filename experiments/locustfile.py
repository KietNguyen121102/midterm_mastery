"""HW5/HW6-style load test against GET /files.

Uses FastHttpUser and almost no think time, same as the HW6 search test.
Each user fetches one of the uploaded files. The default file is 64 KiB:
1024 UDP chunks, long enough that the 2 s client quiet-timeout dominates
latency, short enough that a 5-to-10 minute run stays cheap.

    locust -f experiments/locustfile.py --host http://<ALB>
    FILE=f256kib.bin LOCUST_WAIT=0 locust -f experiments/locustfile.py --host http://<ALB>
"""
import os

from locust import FastHttpUser, constant, task

FILE = os.getenv("FILE", "f64kib.bin")
WAIT = float(os.getenv("LOCUST_WAIT", "0"))


class FileUser(FastHttpUser):
    wait_time = constant(WAIT)

    @task
    def get_file(self):
        with self.client.get(
            f"/files?name={FILE}",
            name=f"GET /files?name={FILE}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                return
            if response.status_code == 503:
                response.failure("503 gateway busy / queue wait")
                return
            if response.status_code == 504:
                response.failure("504 backend did not finish")
                return
            response.failure(f"status {response.status_code}")
