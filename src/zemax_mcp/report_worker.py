"""Offline report process; it never loads a Zemax DLL."""
import json,subprocess,sys,ctypes,os
from pathlib import Path
from .errors import ZemaxError

class ReportProcess:
    def __init__(self,request_file,result_file):
        self.request_file=Path(request_file);self.result_file=Path(result_file);self.process=None;self.log=None
    CanCancel=True
    Progress=0
    @property
    def Status(self):return "离线报告生成中" if self.IsRunning else "报告进程已结束"
    @property
    def IsRunning(self):return self.process is not None and self.process.poll() is None
    @property
    def Succeeded(self):return self.process is not None and self.process.poll()==0
    @property
    def ErrorMessage(self):
        if self.Succeeded:return ""
        path=self.result_file.with_suffix(".log")
        return path.read_text(encoding="utf-8",errors="replace")[-6000:]if path.is_file()else "报告进程失败。"
    def Run(self):
        self.log=self.result_file.with_suffix(".log").open("w",encoding="utf-8")
        self.process=subprocess.Popen([sys.executable,"-B","-m","zemax_mcp.report_worker",str(self.request_file),str(self.result_file)],
            stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log,cwd=self.request_file.parent,
            env={**os.environ,"PYTHONUTF8":"1"},creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    def WaitForCompletion(self):self.process.wait();return True
    def Cancel(self):
        if self.IsRunning:self.process.terminate()
        return True
    def Close(self):
        if self.IsRunning:return False
        if self.log:self.log.close()
        return True

def main():
    ctypes.windll.kernel32.SetDllDirectoryW(None)
    print("report_worker: reading saved input",flush=True)
    from .reports import export_saved_report
    request=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print("report_worker: rendering",flush=True)
    result=export_saved_report(Path(request["folder"]),request["results"],request["title"],request["include_charts"],request["formats"])
    Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print("report_worker: complete",flush=True)

if __name__=="__main__":main()
