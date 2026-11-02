# File-transfer service — 4–5 minute talk

Open `slides.html` in a browser. Arrow keys or space move between slides.
These notes time to about 4:30. Numbers are from the AWS run in us-west-2
on 2026-11-01, plus a local dry-run that isolated the 2 s timeout.

---

## Slide 1 — Setup (25 s)

Two-tier service. HTTP clients hit an ALB in front of gateway tasks. Each
gateway runs at most four FTP_6650 transfers. Those go over UDP through an
internal NLB to backend tasks that read S3. Chunks are 64 bytes; the client
gives up after five OPEN attempts and five RETY rounds, and it decides a
round is over when the server has been quiet for two seconds.

We did not sweep everything. Three knobs, one at a time.

## Slide 2 — Experiment 1: file size (70 s)

**Question.** Does a bigger file just take longer?

**Method.** HW4-style sweep, `SEND_LOSS=0`. 4 KiB, 64 KiB, 256 KiB, 1 MiB
(five reps) and 4 MiB (two). Time `GET /files`.

**Local.** Every size succeeded in 2.00–2.29 s. The quiet timeout is the
floor.

**AWS.** 4 KiB and 64 KiB: 4/5. 256 KiB: 1/5. 1 MiB and 4 MiB: none.
Gateway logs show long consecutive missing-chunk ranges — classic UDP
tail-drop from blasting thousands of datagrams. Then the client fires one
RETY per hole and the backend prints `Overloaded: dropped incoming
datagram` because the job queue is only `workers*4 = 32` deep.

**Reveal.** On a real NLB, size is a loss-exposure knob. The 4 MiB cap is
not reachable with the default retry budget.

## Slide 3 — Experiment 2: send loss (70 s)

**Question.** What does extra `SEND_LOSS` add on top of the NLB?

**Method.** Same 64 KiB file. Redeploy with `--var backend_send_loss=10`.
Eight reps. Also eight 4 KiB reps as a control.

**Result.** 64 KiB went from 80% / 8.9 s to 75% / 11.2 s. 4 KiB at 10%
was 8/8, 4.3–6.4 s. Locally, 10% still finished every 64 KiB file and 20%
collapsed to 1/8 in exactly 12 s (OPEN plus five rounds).

**Reveal.** AWS already sits near the retry ceiling for 1024-chunk files.
Ten more points of send loss buy extra quiet-timeouts, not a new failure
mode. The small file still has slack.

## Slide 4 — Experiment 3: two scalers (70 s)

**Question.** Under load, do both tiers scale? They watch different things.

**Method.** HW6 Locust FastHttpUser, 25 users, 8 minutes, 64 KiB. HW6-style
watch of desired/running/healthy for *both* services. Gateway target:
40 ALB requests/min/task. Backend target: 40% CPU.

**Result.** 1764 requests, 51% failed: 789 × 503 “gateway busy”, 105 × 504.
Gateway desired 4 at 18:54, four healthy tasks a minute later. Backend
stayed at 2 the whole run. Backend CPU averaged 22–39%; one task spiked
to 76% but target tracking uses the average, so it never crossed 40.

**Reveal.** The ALB can see request pile-up. The NLB cannot, so a backend
that is already 504ing files does not look “busy” to its scaler.

## Slide 5 — Takeaways (25 s)

1. The 2 s quiet timeout is the latency floor; AWS burst loss is the
   reliability cliff, and it starts around a few thousand chunks.
2. Five RETY rounds plus a 32-deep queue cannot repair a large hole list.
3. Gateway and backend scalers can disagree. Request-count vs CPU is not
   a cosmetic difference — it is why one tier grew and the other did not.

Stack: `http://file-transfer-gateway-34279764.us-west-2.elb.amazonaws.com`
until `scripts/destroy.sh --yes`.
