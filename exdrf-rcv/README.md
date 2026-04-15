# exdrf-rcv

The RCV project aims to create a system for rendering resources
(as described in the exdrf repo) and other data into the user interface.

**exdrf-rcv** holds **shared Python runtime** for **remote-controlled-view**
(RCV) backends: types and helpers consumed by code emitted by
**`exdrf-gen-al2rcv`** (and by hand-written route modules next to that output).
**`RcvPlan`** and discriminated **`RcvField`** models live in.

The customer-facing RCV UI lives in the **`fr-one`** repo at
**`libs/rcv`**; this package is the exdrf-side counterpart for server logic
and generated stubs.

Python **3.12.2+** is required. Install next to **`exdrf`** in the same
environment as **`exdrf-gen-al2rcv`**.
