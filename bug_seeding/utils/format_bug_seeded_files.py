"""

Created on 02-August-2020
@author Jibesh Patra

Run this script after bug seeding has finished

"""
import os
import subprocess
from threading import Timer
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from pathlib import Path


def format_a_js_file(target_js_file_path: str) -> str:
    def kill_process(p):
        return p.kill()

    err_in_execution = False
    path_to_process = os.path.join(os.path.normpath(
        os.getcwd() + os.sep), 'static_analysis_js', 'utils', 'format_a_js_file.js')
    time_out_before_killing = 5000  # seconds
    try:
        p = subprocess.Popen([
            'node', path_to_process,
            '-inFile', target_js_file_path,
        ], stdout=subprocess.PIPE)
        time_out = Timer(time_out_before_killing, kill_process, [p])
        try:
            time_out.start()
            stdout, stderr = p.communicate()
            if stderr:
                err_in_execution = stderr.decode("utf-8")
        finally:
            time_out.cancel()
    except subprocess.TimeoutExpired:
        pass
    return err_in_execution


def format_files_in_dir(indir):
    js_files = list(Path(indir).rglob('*.js'))
    print(f"Will format {len(js_files)} files")
    with Pool(processes=cpu_count()) as p:
        with tqdm(total=len(js_files)) as pbar:
            pbar.set_description_str(
                desc="Formatting js files ", refresh=False)
            for i, execution_errors in tqdm(
                    enumerate(p.imap_unordered(format_a_js_file,
                                               js_files, chunksize=10))):
                # print(execution_errors)
                pbar.update()
            p.close()
            p.join()


if __name__ == '__main__':
    format_files_in_dir('benchmarks/js_benchmark_seeded_bugs')
