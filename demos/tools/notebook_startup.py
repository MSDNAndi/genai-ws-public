"""IPython startup file for the demo notebooks (the codespace installs it into
~/.ipython/profile_default/startup/, see .devcontainer/on-create.sh).

The notebooks are generated from the samples/*.py scripts, and four script-isms
break inside a Jupyter kernel. This makes them work unchanged:

  * __file__      -> a path inside the matching samples/... folder, so Path(__file__)
                     finds the sample's data, build/ and out/ folders
  * sys.path      -> that folder too, so `import kestrel_search` / `import comfy` work
  * asyncio.run() -> the kernel already runs an event loop; the coroutine runs on a
                     worker thread with its own loop instead (same as a script run)
  * sys.argv      -> just the program name: the kernel's own "-f <connection file>"
                     would otherwise reach the samples' argparse/--profile handling

Does nothing unless the kernel starts inside demos/notebooks/.
"""

import asyncio
import concurrent.futures
import sys
from pathlib import Path


def _genai_notebook_setup() -> None:
    parts = Path.cwd().resolve().parts
    if "notebooks" not in parts:
        return
    i = len(parts) - 1 - parts[::-1].index("notebooks")
    root = Path(*parts[:i])
    if not (root / "providers.json").is_file():
        return
    samples = root / "samples" / Path(*parts[i + 1:]) if len(parts) > i + 1 else root / "samples"

    # IPython restores sys.argv and __file__ after running a startup file, so set both
    # right before each cell instead
    ip = get_ipython()  # noqa: F821
    fake_file = str(samples / "_notebook.py")

    def before_cell(*_):
        sys.argv[:] = sys.argv[:1]
        ip.user_ns.setdefault("__file__", fake_file)

    ip.events.register("pre_run_cell", before_cell)
    if samples.is_dir() and str(samples) not in sys.path:
        sys.path.insert(0, str(samples))

    original_run = asyncio.run

    def run(main, **kwargs):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return original_run(main, **kwargs)
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(original_run, main, **kwargs).result()

    asyncio.run = run


_genai_notebook_setup()
del _genai_notebook_setup
