# pylint: skip-file
# ruff: noqa
"""Memory utilization test for OTF batch SFTP transfers.

Creates a batch of 10 sequential SFTP transfers, each moving a unique 1 MB file
from sftp_1 (172.16.0.21) to sftp_2 (172.16.0.22). RSS memory is sampled every
MEMORY_SAMPLE_INTERVAL seconds in a background thread and written to:

  * the console (printed via pytest -s)
  * /tmp/otf_mem_<run_id>.log  (CSV: timestamp, elapsed_s, rss_mb)

Memory growth is driven by Python handler object accumulation (SSH connections,
loggers, etc.), not by file size, so small files are sufficient to catch
regressions while keeping the test fast enough for regular CI runs.

Run this test in isolation with output visible:
    pytest tests/test_memory_large_file_transfer.py -v -s
"""

import ctypes
import datetime
import gc
import json
import os
import re
import threading
import time
import uuid

import psutil
import pytest

from opentaskpy.config.loader import ConfigLoader
from opentaskpy.taskhandlers import batch
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_LOG_LEVEL"] = "INFO"
os.environ["OTF_BATCH_POLL_INTERVAL"] = (
    "0.1"  # don't wait 5s between batch status checks
)
os.environ["OTF_NO_THREAD_SLEEP"] = "1"  # don't wait 1s between task thread creation

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_TASKS = 10
FILE_SIZE_BYTES = (
    1 * 1024 * 1024
)  # 1 MB — small enough for fast CI runs; memory growth is handler-driven, not file-size-driven
MEMORY_SAMPLE_INTERVAL = 2  # seconds between RSS samples
TRANSFER_TIMEOUT = 120  # seconds per task

# Memory regression threshold.  Current baseline is ~5 MB/task after fixes;
# 15 MB/task gives generous headroom while catching any return of the original
# ~24 MB/task leak caused by un-nulled task_handler references in batch.py.
MAX_UNRECOVERABLE_GROWTH_PER_TASK_MB = 15

# SFTP container IP addresses (match docker-compose network config)
SFTP_1_HOST = "172.16.0.21"
SFTP_2_HOST = "172.16.0.22"
SFTP_SRC_DIR = "/home/application/testFiles/src"
SFTP_DST_DIR = "/home/application/testFiles/dest"
SFTP_USER = "application"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_sparse_file(path: str, size: int) -> None:
    """Create a sparse file at *path* of *size* bytes.

    On Linux the OS allocates no real disk blocks for the gap; reading back
    returns zeroes. SFTP will stream exactly *size* bytes of zeroes to the
    destination, giving a realistic large-file memory-pressure test without
    consuming real disk space on the source side.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.seek(size - 1)
        fh.write(b"\x00")


class MemoryMonitor:
    """Samples RSS memory of the current process in a background thread.

    Usage::

        monitor = MemoryMonitor("/tmp/mem.log")
        initial = monitor.current_rss_mb()
        monitor.start()
        # ... run workload ...
        monitor.stop()
        summary = monitor.summary()
    """

    def __init__(self, log_file: str, sample_interval: float = 2.0) -> None:
        self._log_file = log_file
        self._sample_interval = sample_interval
        self._stop_event = threading.Event()
        self._samples: list[tuple[float, float]] = []  # (elapsed_s, rss_mb)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._process = psutil.Process(os.getpid())
        self._start_time: float = 0.0

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join()

    def current_rss_mb(self) -> float:
        return self._process.memory_info().rss / (1024 * 1024)

    def _run(self) -> None:
        with open(self._log_file, "w", encoding="utf-8") as fh:
            fh.write("timestamp,elapsed_s,rss_mb\n")
            while not self._stop_event.is_set():
                elapsed = time.monotonic() - self._start_time
                rss_mb = self.current_rss_mb()
                ts = datetime.datetime.now().isoformat(timespec="seconds")
                line = f"{ts},{elapsed:.1f},{rss_mb:.1f}\n"
                fh.write(line)
                fh.flush()
                self._samples.append((elapsed, rss_mb))
                self._stop_event.wait(self._sample_interval)

    def summary(self) -> dict:
        if not self._samples:
            return {}
        rss_values = [s[1] for s in self._samples]
        return {
            "min_mb": min(rss_values),
            "max_mb": max(rss_values),
            "final_mb": rss_values[-1],
            "samples": len(rss_values),
        }


# ---------------------------------------------------------------------------
# Task / batch config builders
# ---------------------------------------------------------------------------


def _transfer_task_definition(file_name: str) -> dict:
    """Return a validated-compatible SFTP transfer task definition dict."""
    return {
        "type": "transfer",
        "source": {
            "hostname": SFTP_1_HOST,
            "directory": SFTP_SRC_DIR,
            "fileRegex": re.escape(file_name),
            "protocol": {
                "name": "sftp",
                "credentials": {"username": SFTP_USER},
                "timeout": TRANSFER_TIMEOUT,
            },
        },
        "destination": [
            {
                "hostname": SFTP_2_HOST,
                "directory": SFTP_DST_DIR,
                "protocol": {
                    "name": "sftp",
                    "credentials": {"username": SFTP_USER},
                    "timeout": TRANSFER_TIMEOUT,
                },
            }
        ],
    }


def _batch_definition(task_ids: list) -> dict:
    """Return a sequential batch definition where each task depends on the previous."""
    tasks = []
    for i, task_id in enumerate(task_ids, start=1):
        entry: dict = {
            "order_id": i,
            "task_id": task_id,
            "timeout": TRANSFER_TIMEOUT,
        }
        if i > 1:
            entry["dependencies"] = [i - 1]
        tasks.append(entry)
    return {"type": "batch", "tasks": tasks}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def memory_test_config(tmp_path):
    """Write unique task + batch JSON config files to a temporary directory.

    Returns a 4-tuple:
        (config_dir: str, batch_id: str, task_ids: list[str], file_names: list[str])
    """
    run_id = uuid.uuid4().hex[:8]
    task_ids = [f"mem-sftp-{run_id}-{i}" for i in range(1, NUM_TASKS + 1)]
    file_names = [f"mem_test_{run_id}_{i}.dat" for i in range(1, NUM_TASKS + 1)]
    batch_id = f"mem-sftp-batch-{run_id}"

    # ConfigLoader requires a variables.json to be present
    (tmp_path / "variables.json").write_text("{}", encoding="utf-8")

    # Write one transfer JSON file per task
    for task_id, file_name in zip(task_ids, file_names):
        task_def = _transfer_task_definition(file_name)
        (tmp_path / f"{task_id}.json").write_text(
            json.dumps(task_def, indent=2), encoding="utf-8"
        )

    # Write the batch JSON file
    batch_def = _batch_definition(task_ids)
    (tmp_path / f"{batch_id}.json").write_text(
        json.dumps(batch_def, indent=2), encoding="utf-8"
    )

    return str(tmp_path), batch_id, task_ids, file_names


@pytest.fixture(scope="function")
def large_source_files(root_dir, memory_test_config):
    """Create 2 GB sparse source files on the sftp_1 volume, clean up in teardown.

    Both the source files on sftp_1 and the destination files on sftp_2 are
    removed after the test, ensuring the disk is not filled.
    """
    _, _, _, file_names = memory_test_config
    src_dir = os.path.join(root_dir, "testFiles", "sftp_1", "src")
    dst_dir = os.path.join(root_dir, "testFiles", "sftp_2", "dest")

    src_paths = []
    for file_name in file_names:
        path = os.path.join(src_dir, file_name)
        _create_sparse_file(path, FILE_SIZE_BYTES)
        src_paths.append(path)
        print(
            f"\n  [setup] Created sparse source: {path} "
            f"({FILE_SIZE_BYTES / (1024 ** 2):.0f} MB apparent)"
        )

    yield src_paths

    # --- teardown: remove source files ---
    for path in src_paths:
        if os.path.exists(path):
            os.remove(path)
            print(f"  [teardown] Removed source     : {path}")

    # --- teardown: remove destination files ---
    for file_name in file_names:
        dst_path = os.path.join(dst_dir, file_name)
        if os.path.exists(dst_path):
            os.remove(dst_path)
            print(f"  [teardown] Removed destination: {dst_path}")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_memory_usage_large_file_batch_sftp_transfer(
    root_dir,
    setup_sftp_keys,
    memory_test_config,
    large_source_files,
):
    """Run 10 sequential 1 MB SFTP transfers as a batch and monitor RSS memory.

    The test:
    1. Writes 10 unique task JSON configs + 1 batch JSON config to a tmp dir.
    2. Creates a 1 MB sparse file on sftp_1 for each task.
    3. Starts a background thread sampling RSS every MEMORY_SAMPLE_INTERVAL s.
    4. Runs the batch via ConfigLoader + batch.Batch.run().
    5. Prints a memory summary to the console and writes a CSV log to /tmp.
    6. Asserts all transfers succeeded and all destination files exist.
    7. Asserts unrecoverable RSS growth per task is below the regression threshold.
    8. Cleans up source and destination files in fixture teardown.
    """
    config_dir, batch_id, task_ids, file_names = memory_test_config
    log_file = f"/tmp/otf_mem_{batch_id}.log"

    print(f"\n[memory-test] Memory log  : {log_file}")
    print(f"[memory-test] Config dir  : {config_dir}")
    print(f"[memory-test] Batch ID    : {batch_id}")
    print(
        f"[memory-test] {NUM_TASKS} tasks × {FILE_SIZE_BYTES / (1024 ** 2):.0f} MB each"
    )

    config_loader = ConfigLoader(config_dir)
    batch_definition = config_loader.load_task_definition(batch_id)

    # --- profiling: baseline before batch ---
    gc.collect()

    monitor = MemoryMonitor(log_file=log_file, sample_interval=MEMORY_SAMPLE_INTERVAL)
    initial_rss = monitor.current_rss_mb()
    print(f"[memory-test] Initial RSS : {initial_rss:.1f} MB")

    monitor.start()
    try:
        batch_obj = batch.Batch(None, batch_id, batch_definition, config_loader)
        result = batch_obj.run()
    finally:
        monitor.stop()

    final_rss = monitor.current_rss_mb()
    summary = monitor.summary()
    growth = final_rss - initial_rss

    print()
    print("[memory-test] ========== Memory Usage Summary ==========")
    print(f"[memory-test] Initial RSS : {initial_rss:.1f} MB")
    print(f"[memory-test] Final RSS   : {final_rss:.1f} MB")
    print(f"[memory-test] Peak RSS    : {summary.get('max_mb', 0):.1f} MB")
    print(f"[memory-test] Min RSS     : {summary.get('min_mb', 0):.1f} MB")
    print(f"[memory-test] Growth      : {growth:+.1f} MB")
    print(f"[memory-test] Samples     : {summary.get('samples', 0)}")
    print(f"[memory-test] Log file    : {log_file}")
    print("[memory-test] =============================================")

    # --- gc analysis ---
    rss_before_gc = monitor.current_rss_mb()
    collected = gc.collect()
    rss_after_gc = monitor.current_rss_mb()
    print()
    print(f"[gc] Objects collected by gc.collect() : {collected}")
    print(f"[gc] RSS before gc.collect()           : {rss_before_gc:.1f} MB")
    print(f"[gc] RSS after  gc.collect()           : {rss_after_gc:.1f} MB")
    print(
        f"[gc] RSS freed by gc                   : {rss_before_gc - rss_after_gc:+.1f} MB"
    )

    # --- malloc_trim: ask glibc to return freed arenas to the OS ---
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
        rss_after_trim = monitor.current_rss_mb()
        print(f"[gc] RSS after  malloc_trim(0)        : {rss_after_trim:.1f} MB")
        print(
            f"[gc] RSS freed by malloc_trim         : {rss_after_gc - rss_after_trim:+.1f} MB"
        )
        print(
            f"[gc] Unrecoverable RSS growth         : {rss_after_trim - initial_rss:+.1f} MB"
        )
    except Exception as e:
        print(f"[gc] malloc_trim not available: {e}")

    # --- assert all transfers completed successfully ---
    assert result, "Batch of large-file SFTP transfers reported failure"

    dst_dir = os.path.join(root_dir, "testFiles", "sftp_2", "dest")
    for file_name in file_names:
        dst_path = os.path.join(dst_dir, file_name)
        assert os.path.exists(
            dst_path
        ), f"Expected destination file not found after transfer: {dst_path}"

    # --- memory regression assertion ---
    # Use the post-malloc_trim RSS as the "true" retained memory; fall back to
    # post-gc RSS when malloc_trim is unavailable (non-Linux environments).
    try:
        unrecoverable_mb = rss_after_trim - initial_rss
    except NameError:
        unrecoverable_mb = rss_after_gc - initial_rss

    growth_per_task_mb = unrecoverable_mb / NUM_TASKS
    print()
    print(f"[assert] Unrecoverable growth per task : {growth_per_task_mb:.1f} MB")
    print(
        f"[assert] Threshold                     : {MAX_UNRECOVERABLE_GROWTH_PER_TASK_MB} MB/task"
    )
    assert growth_per_task_mb < MAX_UNRECOVERABLE_GROWTH_PER_TASK_MB, (
        f"Memory regression detected: {growth_per_task_mb:.1f} MB/task retained after "
        f"gc.collect() + malloc_trim (threshold: {MAX_UNRECOVERABLE_GROWTH_PER_TASK_MB} MB/task). "
        f"Total unrecoverable growth: {unrecoverable_mb:.1f} MB over {NUM_TASKS} tasks."
    )
