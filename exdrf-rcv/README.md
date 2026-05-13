# exdrf-rcv

The **remote-controlled-view (RCV)** stack renders **exdrf** resources and
related data into a user interface that the front end drives over HTTP.

**exdrf-rcv** is the **shared Python runtime** for RCV *backends*. It defines
**`RcvPlan`**, discriminated **`RcvField`** types, and helpers that
**`exdrf-gen-al2rcv`**-generated route modules import next to your FastAPI app.

The browser UI that consumes those endpoints lives in **fr-one** under
**`libs/rcv`**; this package stays on the **exdrf** / API side of that boundary.

Python **3.12.2+** is required. Install next to **exdrf** in the same
environment as **exdrf-gen-al2rcv** output.

## Related packages

- **exdrf-gen-al2rcv** — emits `{resource}_rcv_paths.py` scaffolds and root
  **`api.py`** wired to your **`--get-db`** callable.
- **exdrf-gen-al2r** — sibling FastAPI router codegen; similar category layout.
