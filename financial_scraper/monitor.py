import time
import subprocess
import logging
import sqlite3
import os
import sys

# 配置监控日志，同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [MONITOR] - %(message)s',
    handlers=[
        logging.FileHandler("monitor.log"),
        logging.StreamHandler()
    ]
)

DB_PATH = "financial_data_v2.db"
# Use the python executable from the virtual environment
PYTHON_CMD = "venv/bin/python"

def get_db_counts():
    """获取当前数据库中的人员记录数"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*) FROM amac_practitioners")
        amac_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM sac_practitioners")
        sac_count = cursor.fetchone()[0]
        
        conn.close()
        return amac_count, sac_count
    except Exception as e:
        logging.error(f"Database read error: {e}")
        return -1, -1

def get_progress_status(task_name: str) -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM progress_tracking WHERE task_name = ?", (task_name,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return ""
        return str(row[0] or "")
    except Exception as e:
        logging.error(f"Progress read error ({task_name}): {e}")
        return ""

def is_pipeline_completed(pipeline_task: str) -> bool:
    return get_progress_status(pipeline_task) == "completed"

def start_process(cmd, log_path: str):
    log_handle = open(log_path, "a")
    process = subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        close_fds=True
    )
    return process, log_handle

def stop_process(process, log_handle):
    try:
        if process is not None:
            process.terminate()
            time.sleep(2)
            process.kill()
            process.wait()
    except Exception:
        pass
    try:
        if log_handle is not None and not log_handle.closed:
            log_handle.close()
    except Exception:
        pass

def main():
    logging.info("Starting Scraper Monitor Daemon (20-minute intervals)...")
    
    amac_cmd = [PYTHON_CMD, "amac_scraper.py"]
    sac_cmd = [PYTHON_CMD, "sac_scraper.py"]
    
    amac_done = is_pipeline_completed("amac_pipeline")
    sac_done = is_pipeline_completed("sac_pipeline")
    
    amac_process = None
    amac_log = None
    sac_process = None
    sac_log = None
    
    if not amac_done:
        amac_process, amac_log = start_process(amac_cmd, "amac_scraper.log")
    else:
        logging.info("AMAC pipeline completed. Monitoring only.")
        
    if not sac_done:
        sac_process, sac_log = start_process(sac_cmd, "sac_scraper.log")
    else:
        logging.info("SAC pipeline completed. Monitoring only.")
    
    # 检查间隔：20分钟 (20 * 60 = 1200 秒)
    # 为了方便您初步观察，如果需要测试可以先改成短时间，当前严格按要求设置为 1200
    check_interval = 1200 
    
    last_amac_count, last_sac_count = get_db_counts()
    logging.info(f"Initial Database records -> AMAC: {last_amac_count}, SAC: {last_sac_count}")
    
    while True:
        # 休眠 20 分钟
        time.sleep(check_interval)
        
        logging.info("--- Performing 20 Minute Health Check ---")
        
        # 检查进程是否意外退出
        amac_ret = amac_process.poll() if amac_process is not None else None
        sac_ret = sac_process.poll() if sac_process is not None else None
        
        curr_amac_count, curr_sac_count = get_db_counts()
        logging.info(f"Current Database records -> AMAC: {curr_amac_count}, SAC: {curr_sac_count}")

        amac_done = is_pipeline_completed("amac_pipeline")
        sac_done = is_pipeline_completed("sac_pipeline")
        
        # --- AMAC (中基协) 健康检查 ---
        if amac_ret is not None:
            if amac_done:
                logging.info(f"AMAC pipeline completed (exit {amac_ret}). Monitoring only.")
                stop_process(amac_process, amac_log)
                amac_process = None
                amac_log = None
            else:
                logging.warning(f"AMAC scraper exited unexpectedly with code {amac_ret}. Restarting...")
                stop_process(amac_process, amac_log)
                amac_process, amac_log = start_process(amac_cmd, "amac_scraper.log")
        elif curr_amac_count == last_amac_count and curr_amac_count != -1:
            if amac_done:
                logging.info("AMAC pipeline completed. Monitoring only.")
                stop_process(amac_process, amac_log)
                amac_process = None
                amac_log = None
            else:
                logging.warning("AMAC scraper seems stuck (no new data in 20 mins). Terminating and restarting...")
                stop_process(amac_process, amac_log)
                amac_process, amac_log = start_process(amac_cmd, "amac_scraper.log")
        else:
            logging.info("AMAC scraper is running healthily.")
            
        # --- SAC (中证协) 健康检查 ---
        if sac_ret is not None:
            if sac_done:
                logging.info(f"SAC pipeline completed (exit {sac_ret}). Monitoring only.")
                stop_process(sac_process, sac_log)
                sac_process = None
                sac_log = None
            else:
                logging.warning(f"SAC scraper exited unexpectedly with code {sac_ret}. Restarting...")
                stop_process(sac_process, sac_log)
                sac_process, sac_log = start_process(sac_cmd, "sac_scraper.log")
        elif curr_sac_count == last_sac_count and curr_sac_count != -1:
            if sac_done:
                logging.info("SAC pipeline completed. Monitoring only.")
                stop_process(sac_process, sac_log)
                sac_process = None
                sac_log = None
            else:
                logging.warning("SAC scraper seems stuck (no new data in 20 mins). Terminating and restarting...")
                stop_process(sac_process, sac_log)
                sac_process, sac_log = start_process(sac_cmd, "sac_scraper.log")
        else:
            logging.info("SAC scraper is running healthily.")

        if amac_process is None and not amac_done:
            amac_process, amac_log = start_process(amac_cmd, "amac_scraper.log")
        if sac_process is None and not sac_done:
            sac_process, sac_log = start_process(sac_cmd, "sac_scraper.log")
            
        # 更新记录
        last_amac_count = curr_amac_count
        last_sac_count = curr_sac_count

if __name__ == "__main__":
    main()
