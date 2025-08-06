#!/usr/bin/env python3
import os
import sqlite3
import argparse
import subprocess
import logging
from pathlib import Path
import json
import hashlib

CUR_DIR = Path(os.path.dirname(__file__))
VAPI = os.environ.get("VAPI_HOSTNAME")

class Status:
    PENDING = "pending"
    ACCEPT  = "accepted"
    REJECT  = "rejected"
    DUPLICATED  = "duplicate_commit"
    DUPLICATED_POV = "duplicated_pov"

def run_cmd(cmd, cwd = None):
    try:
        cmd = list(map(str, cmd))
        ret = subprocess.check_output(cmd, cwd = cwd, stdin = subprocess.DEVNULL,
                                                      stderr = subprocess.DEVNULL)
        return ret.decode("utf-8", errors="ignore")
    except:
        logging.error("Fail to run: " + " ".join(cmd))
        return ""

MAX_PRIORTY = 1000000
BLOB_SEEDS = "blob_seeds"
PRIORITY = "blob_priority.json"
DUMMY_VD_UUID = "DUMMY_ID-TEMP-TEMP-TEMP-XXXXXXXXXXXX"
def get_corpus_infos(pov):
    pov = Path(str(pov))
    cur = pov.parent
    while cur is not cur.parent:
        seeds = cur / BLOB_SEEDS
        priority = cur / PRIORITY
        if seeds.exists() and priority.exists(): return (seeds, priority)
        cur = cur.parent
    return (None, None)

def get_scratch(name):
    scratch = Path(os.environ.get("AIXCC_CRS_SCRATCH_SPACE"))
    ret = scratch / name
    os.makedirs(str(ret), exist_ok=True)
    return ret

class SubmitDB:
    def __init__(self):
        if os.environ.get("DEV", False):
            workdir = Path(os.environ.get("AIXCC_CRS_SCRATCH_SPACE", "/tmp"))
        else:
            workdir = Path(os.environ.get("JAVA_WORK", "/tmp"))
        # workdir = Path(os.environ.get("CRS_WORKDIR", "/tmp"))
        self.workdir = workdir
        self.db = sqlite3.connect(str(workdir / "submit.db"))
        self.__create()

    def __create(self):
        try:
            self.db.cursor().execute("CREATE TABLE submit(id, harness, pov, status, pov_hash)")
        except: pass

    def __add(self, data):
        query = "insert into submit(id, harness, pov, status, pov_hash) values(?, ?, ?, ?, ?)"
        self.db.cursor().execute(query, data)
        self.db.commit()

    def __update(self, id, status):
        query = "update submit set status = ? where id = ?"
        self.db.cursor().execute(query, (status, id))
        self.db.commit()

    def __load_bic_hints(self):
        hints = os.environ.get("BIC_HINTS")
        if hints == None: return None
        hints = Path(hints)
        if not hints.exists(): return None
        return hints

    def __submit_vapi(self, harness, pov):
        if VAPI == None: return DUMMY_VD_UUID
        hints = self.__load_bic_hints()
        cp = os.environ.get("TARGET_CP")
        cmd = ["python3", CUR_DIR / "vapi-client/verifier.py", "submit_vd"]
        cmd += [f"--project={cp}"]
        cmd += [f"--harness={harness}"]
        cmd += [f"--pov={pov}"]
        cmd += [f"--commit-hints-file={hints}"]
        submit_id = run_cmd(cmd).strip()
        if submit_id != "": return submit_id
        print("submit vapi error")
        return None

    def __check_vapi(self, submit_id):
        if VAPI == None: return None
        cmd = ["python3", CUR_DIR / "vapi-client/verifier.py", "check_vd"]
        cmd += ["--vd-uuid", submit_id]
        ret = run_cmd(cmd).strip()
        if ret in [Status.PENDING, Status.ACCEPT]:
            return ret
        if Status.REJECT in ret:
            if Status.DUPLICATED in ret: return Status.DUPLICATED
            return Status.REJECT
        # print("check vapi error")
        return None

    def __pass_corpus_for_patch(self, harness, pov):
        (blobs, priority) = get_corpus_infos(pov)
        if blobs == None or priority == None: return
        with open(priority) as f: priority = json.load(f)
        for name in priority:
            p = priority[name][0]
            if p == MAX_PRIORTY: p = 0
            priority[name] = p
        corpus_dir = get_scratch("corpus")
        with open(corpus_dir / f"{harness}.json", "wt") as f:
            json.dump(priority, f)
        run_cmd(["rsync", "-a", f"{blobs}/.", corpus_dir / harness])

    def __calc_pov_hash(self, harness, pov):
        pov = Path(str(pov))
        data = bytes(harness, "utf-8")
        if pov.exists():
            with open(pov, "rb") as f: data += f.read()
        return hashlib.sha1(data).hexdigest()

    def __submitted(self, pov_hash):
        res = self.db.cursor().execute("SELECT * from submit where pov_hash = ?", (pov_hash,))
        return len(list(res.fetchall())) != 0

    def submit(self, harness, pov):
        pov_hash = self.__calc_pov_hash(harness, pov)
        if self.__submitted(pov_hash):
            self.__add((DUMMY_VD_UUID, harness, pov, Status.DUPLICATED_POV, pov_hash))
            print(f"submit_id: DUPLICATED", flush=True)
            return
        # self.__pass_corpus_for_patch(harness, pov)
        submit_id = self.__submit_vapi(harness, pov)
        print(f"submit_id: {submit_id}", flush=True)
        self.__add((submit_id, harness, pov, Status.PENDING, pov_hash))

    def check(self):
        res = self.db.cursor().execute("SELECT * from submit where status = ?", (Status.PENDING,))
        accepted = []
        rejected = []
        duplicated = []
        for item in res.fetchall():
            (id, harness, pov, status, _) = item
            if id == None or id == "None": continue
            status = self.__check_vapi(id)
            if status in [None, Status.PENDING]: continue
            self.__update(id, status)
            if status == Status.ACCEPT: accepted.append((id, pov))
            if status == Status.REJECT: rejected.append((id, pov))
            if status == Status.DUPLICATED: duplicated.append((id, pov))

        for (id, pov) in accepted:
            print(f"accepted:{id}:{pov}", flush=True)
        for (id, pov) in rejected:
            print(f"rejected:{id}:{pov}", flush=True)
        for (id, pov) in duplicated:
            print(f"duplicated:{id}:{pov}", flush=True)

    def summary(self):
        res = self.db.cursor().execute("SELECT * from submit")
        with open(self.workdir / "verified_stats", "wt+") as f:
            for item in res.fetchall():
                (id, harness, pov, status, pov_hash) = item
                f.write(f"[{pov_hash}][{status}] {id}: {harness}, {pov}\n")
        if VAPI == None:
            res = self.db.cursor().execute("SELECT * from submit")
            with open(self.workdir / "verified_logs", "wt+") as f:
                for item in res.fetchall():
                    (id, harness, pov, status, pov_hash) = item
                    f.write(f"[{pov_hash}] ./run.sh run_pov {pov} {harness}\n")

    def precompile(self):
        if VAPI == None: return
        hints = self.__load_bic_hints()
        cp = os.environ.get("TARGET_CP")
        cmd = ["python3", CUR_DIR / "vapi-client/verifier.py", "precompile"]
        cmd += [f"--project={cp}"]
        if hints != None:
            cmd += [f"--commit-hints-file={hints}"]
        run_cmd(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", help="harness id")
    parser.add_argument("--pov", help="pov data blob path")
    parser.add_argument("--check", help="check the verifier result with VAPI", default=False, action="store_true")
    parser.add_argument("--precompile", help="precompile CPs", default=False, action="store_true")
    args = parser.parse_args()

    db = SubmitDB()
    if args.precompile: return db.precompile()
    if args.harness and args.pov: db.submit(args.harness, args.pov)
    if args.check: db.check()
    db.summary()

if __name__ == "__main__":
    main()
