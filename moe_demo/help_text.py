"""User-facing help text and tooltips (kept out of the UI code for readability and testing)."""
from __future__ import annotations

TOOLTIPS: dict[str, str] = {
    "temperature": "Randomness of sampling. Low (0-0.3) = focused and repeatable; high (0.8-1.2) = "
                   "more varied. NVIDIA recommends 1.0 for this model. Applied on the next message.",
    "top_p": "Nucleus sampling: only the smallest set of tokens whose probabilities add up to top_p "
             "is considered. NVIDIA recommends 0.95.",
    "num_ctx": "Context window in tokens (prompt + answer). Larger values use more memory; changing "
               "it makes Ollama reload the model, so the next request is slower once.",
    "num_predict": "Maximum number of tokens to generate (reasoning tokens count too). -1 = unlimited.",
    "think": "Nemotron can first write a reasoning trace and then the answer. Auto uses the category's "
             "recommended mode; Off is fastest.",
    "history": "Send earlier turns of this conversation to the model so it can refer back to them.",
    "category": "Which task type the explanation panel assumes. Auto guesses it from your prompt with "
                "a keyword heuristic.",
    "tps": "Decode speed: generated tokens divided by Ollama's measured generation time.",
    "ttft": "Time to first token, measured by this app (includes model loading if it was cold).",
    "load": "Time Ollama spent loading the model into memory for this request (0 if already loaded).",
    "wall": "Client-side end-to-end time for the whole answer.",
    "prompt_tokens": "Tokens in your prompt (including system prompt and history), counted by Ollama.",
    "gen_tokens": "Tokens generated, including reasoning tokens.",
}

MOE_GUIDE = """
### What is a Mixture of Experts (MoE)?
A normal ("dense") transformer pushes **every token through every weight**. An MoE model replaces
the big feed-forward block with **many smaller expert networks** and a small **router**:

1. The router scores every expert for the current token.
2. Only the **top-k** experts run (for this model: **6 of 128**).
3. Their outputs are combined using the router's weights.

So the model holds a lot of knowledge (**~30B parameters**) but each token only costs about
**3B parameters** of compute — hence the name *30B-A3B* ("A" = active).

### Nemotron 3.5 Lightning in particular
* **Hybrid architecture**: interleaved **Mamba-2** (state-space) layers, **MoE** layers and a few
  **attention** layers. Mamba-2 keeps memory and time per token almost constant on long inputs.
* **Multi-Token Prediction (MTP)** heads support speculative decoding for faster generation.
* **Optional reasoning**: the model can write a reasoning trace before the final answer.
* Published recommended sampling: **temperature 1.0, top-p 0.95**.

### Do experts "specialise"?
Partly. Studies of MoE models show experts develop *soft* preferences (code symbols, particular
languages, punctuation, certain topics), mostly at token level rather than "one expert per subject".
Different task types therefore tend to activate **different combinations** of experts, while
a shared set of experts handles generic language.

### What this app can and cannot show
| Shown | Source |
|---|---|
| Model loaded?, memory, context length | **Measured** (Ollama `/api/ps`) |
| Tokens/s, time to first token, load time, token counts, reasoning share | **Measured** (Ollama stats + app timer) |
| Which experts fire | **Illustrative**: Ollama does not expose router decisions. The expert panel is a deterministic simulation guided by the task category. |

### Why MoE helps task-specific performance
* **Capacity without cost**: more total knowledge at the compute price of a small model.
* **Specialisation**: different token types can use different weights without interfering.
* **Trade-off**: all 30B parameters must still sit in memory, even though few are active.
"""

PARAM_GUIDE = """
**Temperature / top-p** shape the *sampling*; they do not change the router, but they change
which tokens get generated and therefore which experts are consulted next.
**Context window** is the memory budget for prompt + answer. **Reasoning mode** trades speed
for more careful step-by-step answers.
"""
