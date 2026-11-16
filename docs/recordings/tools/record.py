#!/usr/bin/env python3
"""Record a scripted terminal session as an asciicast v2 file, with a "typing" effect.

usage:  python record.py OUT.cast "Title" CMD [CMD ...]

Run it from labs/. Each CMD is typed at a prompt and then run in bash inside a 100x30 pseudo-terminal.
  - "# text"  is typed as a comment and not run (used as an on-screen caption).
  - "cd DIR"  changes the directory for the following commands (the prompt shows it).
Idle gaps in the output (model thinking time) are capped at IDLE seconds.
Any value in $REC_SECRET is replaced with *** in the output; the run fails if it still appears.
"""
import json, os, random, select, signal, subprocess, sys, time, fcntl, termios, struct, codecs

COLS, ROWS, IDLE, TIMEOUT = 100, 30, 2.0, 300
random.seed(7)


def main():
    out, title, cmds = sys.argv[1], sys.argv[2], sys.argv[3:]
    secret = os.environ.get("REC_SECRET", "")
    base = os.getcwd()
    cwd = base
    events, t = [], 0.0

    def emit(s, dt=0.0):
        nonlocal t
        t += dt
        if secret:
            s = s.replace(secret, "***")
        events.append([round(t, 3), "o", s])

    def prompt():
        rel = os.path.relpath(cwd, os.path.dirname(base))
        return f"\x1b[1;32m{rel}\x1b[0m $ "

    failures = []
    emit("\x1b[2J\x1b[H")
    for cmd in cmds:
        emit(prompt(), 0.4)
        for ch in cmd:
            emit(ch, random.uniform(0.025, 0.06))
        emit("\r\n", 0.5)
        if cmd.startswith("#"):
            continue
        if cmd.startswith("cd "):
            cwd = os.path.normpath(os.path.join(cwd, cmd[3:].strip()))
            continue
        master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
        env = dict(os.environ, TERM="xterm-256color", COLUMNS=str(COLS), LINES=str(ROWS))
        env.pop("REC_SECRET", None)
        p = subprocess.Popen(["bash", "-c", cmd], cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                             env=env, start_new_session=True, close_fds=True)
        os.close(slave)
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        last, start, buf = time.time(), time.time(), ""
        while True:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:
                    break
                now = time.time()
                buf += dec.decode(data)
                # hold back a tail so a secret split across reads is still caught
                keep = max(len(secret) - 1, 0)
                if len(buf) > keep:
                    chunk, buf = (buf[:-keep], buf[-keep:]) if keep else (buf, "")
                    emit(chunk, min(now - last, IDLE))
                    last = now
            elif p.poll() is not None:
                break
            if time.time() - start > TIMEOUT:
                os.killpg(p.pid, signal.SIGTERM)
                failures.append(f"timeout: {cmd}")
                break
        if buf:
            emit(buf, 0.0)
        rc = p.wait()
        os.close(master)
        if rc != 0:
            failures.append(f"exit {rc}: {cmd}")
    emit(prompt(), 0.6)
    emit("", 3.0)

    text = "".join(e[2] for e in events)
    if secret and (secret in text or secret[-8:] in text):
        sys.exit(f"SECRET FOUND in {out}; not written")
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"version": 2, "width": COLS, "height": ROWS, "title": title,
                            "env": {"TERM": "xterm-256color"}}) + "\n")
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"{out}: {t:.1f}s" + ("".join(f"\n  FAIL {x}" for x in failures)))


if __name__ == "__main__":
    main()
