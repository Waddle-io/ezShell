"""
Prompt engineering module for ezShell — defines all LLM system prompts and user-prompt builders.

This module centralises every string that is sent to the Groq LLM so that prompt
changes can be made in one place without touching business logic.  It provides:

* **System prompts** — static constants (``SYSTEM_PROMPT``, ``ASK_SYSTEM_PROMPT``,
  ``CHAT_SYSTEM_PROMPT``) that instruct the model on its role, output format, and
  behavioural constraints for each interaction mode.
* **Prompt builders** — functions that compose the dynamic user-facing portion of
  each request by interpolating runtime data (failed command, error output, system
  environment, user question) into a structured template.

JSON schema contract
--------------------
``SYSTEM_PROMPT`` and ``ASK_SYSTEM_PROMPT`` both instruct the model to return a
JSON object with the following four keys::

    {
      "summary":        str,        # One-sentence description of the issue/answer
      "explanation":    str,        # 2–3 sentence markdown explanation
      "suggested_fix":  str | null, # Exact shell command or null
      "fix_description":str         # Short description of suggested_fix
    }

``CHAT_SYSTEM_PROMPT`` does *not* enforce a JSON schema; it allows free-form
markdown because ``ChatSession`` extracts commands from fenced code blocks rather
than parsing JSON.

---

Module d'ingénierie des prompts pour ezShell — définit tous les prompts système LLM et
les constructeurs de prompts utilisateur.

Ce module centralise toutes les chaînes envoyées au LLM Groq afin que les modifications
de prompts puissent être effectuées en un seul endroit sans toucher à la logique métier.
Il fournit :

* **Prompts système** — constantes statiques (``SYSTEM_PROMPT``, ``ASK_SYSTEM_PROMPT``,
  ``CHAT_SYSTEM_PROMPT``) qui instruisent le modèle sur son rôle, son format de sortie
  et ses contraintes comportementales pour chaque mode d'interaction.
* **Constructeurs de prompts** — fonctions qui composent la partie utilisateur dynamique
  de chaque requête en interpolant des données d'exécution dans un gabarit structuré.

Contrat de schéma JSON
----------------------
``SYSTEM_PROMPT`` et ``ASK_SYSTEM_PROMPT`` instruisent tous deux le modèle de retourner
un objet JSON avec les quatre clés suivantes::

    {
      "summary":        str,        # Description en une phrase
      "explanation":    str,        # Explication markdown en 2–3 phrases
      "suggested_fix":  str | null, # Commande shell exacte ou null
      "fix_description":str         # Courte description de suggested_fix
    }

``CHAT_SYSTEM_PROMPT`` n'impose pas de schéma JSON ; il autorise le markdown libre car
``ChatSession`` extrait les commandes des blocs de code délimités plutôt que de parser
du JSON.
"""

from __future__ import annotations

__all__ = [
    "SYSTEM_PROMPT",
    "ASK_SYSTEM_PROMPT",
    "CHAT_SYSTEM_PROMPT",
    "build_chat_system_prompt",
    "build_error_analysis_prompt",
    "build_ask_prompt",
]

# ---------------------------------------------------------------------------
# SYSTEM_PROMPT
# ---------------------------------------------------------------------------
# Used by ShellAssistant.diagnose_failure for one-shot error analysis.
# Instructs the model to act as a DevOps expert, respect the user's OS/package
# manager, focus on the root cause, and always return the four-key JSON schema
# described in the module docstring.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ezShell, an ultra-fast, expert DevOps and system administration AI assistant integrated directly into the user's terminal.
Your purpose is to diagnose command failures instantly and provide exact, actionable fixes.

GUIDELINES:
1. Be concise, direct, and technical. Skip pleasantries and filler text (e.g., do not say "Hello!", "Certainly!").
2. Context Awareness: Always respect the user's OS, package manager, and shell environment provided in the context.
   - Debian/Ubuntu: use apt
   - Fedora/RHEL/CentOS: use dnf
   - Arch Linux: use pacman
   - macOS: use brew
3. Focus on the root cause: explain why the command failed in 1-2 crisp sentences.
4. Always provide an exact, executable fix command when possible.

RESPONSE FORMAT:
You MUST format your response as a valid JSON object with the following schema:
{
  "summary": "1-sentence summary of the issue (e.g. 'Missing package libpq-dev' or 'Git branch does not exist')",
  "explanation": "Brief explanation of the root cause in markdown format (maximum 2-3 sentences)",
  "suggested_fix": "Exact shell command to fix the issue, or null if no automated fix applies",
  "fix_description": "Short explanation of what the fix command does (e.g. 'Installs the missing development headers')"
}

IMPORTANT: Output ONLY the raw JSON object. Do not wrap in backticks or markdown code blocks unless requested.
"""

# ---------------------------------------------------------------------------
# ASK_SYSTEM_PROMPT
# ---------------------------------------------------------------------------
# Used by ShellAssistant.ask for natural-language terminal queries (!ask mode).
# Shares the same four-key JSON schema as SYSTEM_PROMPT but has a softer tone
# suited to answering "how do I…" questions rather than diagnosing failures.
# ---------------------------------------------------------------------------

ASK_SYSTEM_PROMPT = """You are ezShell, a helpful and concise terminal assistant.
The user is asking a natural language question about command line tools, shell scripts, or system tasks.

Provide a concise answer with the exact command to execute.

RESPONSE FORMAT:
Output a valid JSON object:
{
  "summary": "Short title or summary",
  "explanation": "Brief technical explanation (maximum 2-3 sentences)",
  "suggested_fix": "Exact shell command to execute, or null",
  "fix_description": "Short explanation of the command"
}

Output ONLY the JSON object.
"""

# ---------------------------------------------------------------------------
# CHAT_SYSTEM_PROMPT
# ---------------------------------------------------------------------------
# Used by ChatSession as the base system prompt for interactive multi-turn chat.
# Does NOT enforce a JSON schema — the model is free to respond in markdown.
# build_chat_system_prompt() appends live system-environment context before use.
# Key constraints: no emojis, commands must be in bash fenced blocks, concise.
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """You are ezShell, an expert DevOps, terminal, and systems engineering AI assistant running in an interactive terminal popup window.
The user is conversing with you directly from their command line.

GUIDELINES:
1. Be direct, clear, and technically precise.
2. NEVER use emojis anywhere in your output. Use standard text characters or symbols like '›', '•', '→', '[!]' if needed.
3. When recommending terminal commands to run, always format each command in its own markdown bash code block:
```bash
<exact command>
```
4. Context Awareness: Always tailor commands to the user's operating system, shell, package manager, and active working directory provided below.
5. Provide a short, informative explanation of what the command does or any important options/flags.
6. Keep responses focused and readable inside a terminal window. Avoid unnecessary filler or overly long responses.
"""


def build_chat_system_prompt(system_context: str) -> str:
    """Build the system prompt for the interactive chat session with environment context.

    Appends a ``### SYSTEM ENVIRONMENT CONTEXT:`` section containing the
    serialised ``SystemContext`` to ``CHAT_SYSTEM_PROMPT`` so that the model
    can tailor its responses (package manager, shell, working directory, etc.)
    to the user's live environment.

    Args:
        system_context: A pre-formatted string representation of the user's
            system environment, typically produced by
            ``SystemContext.to_prompt_context()``.

    Returns:
        The complete system prompt string ready to be sent as the first
        ``{"role": "system", ...}`` message in a chat-completion request.
    """
    return f"{CHAT_SYSTEM_PROMPT}\n### SYSTEM ENVIRONMENT CONTEXT:\n{system_context}"


def build_error_analysis_prompt(
    command: str,
    exit_code: int,
    error_output: str,
    system_context: str,
) -> str:
    """Build the user-turn prompt for analysing a failed shell command.

    Combines the system-environment context, the failed command with its exit
    code, and the command's output into a single structured prompt string.
    Overly long ``error_output`` values are truncated to keep the request
    within LLM token limits: the first 1 000 characters and last 2 000
    characters are preserved, with a ``[truncated]`` marker in between.

    Args:
        command: The exact shell command string that was executed and failed.
        exit_code: The non-zero integer exit code returned by the command.
        error_output: The stderr (and optionally stdout) text produced by the
            command.  May be an empty string.
        system_context: A pre-formatted string representation of the user's
            system environment, typically produced by
            ``SystemContext.to_prompt_context()``.

    Returns:
        A formatted multi-section prompt string ready to be passed as the
        ``prompt`` argument to ``GroqClient.complete`` alongside
        ``SYSTEM_PROMPT``.
    """
    # Truncate error output if excessively long to stay well within token limits
    max_error_chars = 3000
    cleaned_error = error_output.strip()
    if len(cleaned_error) > max_error_chars:
        cleaned_error = (
            cleaned_error[:1000]
            + "\n... [truncated] ...\n"
            + cleaned_error[-2000:]
        )

    return f"""### SYSTEM CONTEXT:
{system_context}

### FAILED COMMAND:
`{command}` (Exit Code: {exit_code})

### COMMAND OUTPUT / STDERR:
```
{cleaned_error if cleaned_error else "(No stderr output, command exited with non-zero code)"}
```

Diagnose this error and provide the fix in the required JSON format."""


def build_ask_prompt(question: str, system_context: str) -> str:
    """Build the user-turn prompt for a natural-language ``!ask`` query.

    Embeds the user's question and the live system-environment context into a
    concise prompt that instructs the model to answer in the four-key JSON
    schema defined by ``ASK_SYSTEM_PROMPT``.

    Args:
        question: The free-form natural-language question entered by the user
            (e.g. ``"how do I list open ports on Linux?"``).
        system_context: A pre-formatted string representation of the user's
            system environment, typically produced by
            ``SystemContext.to_prompt_context()``.

    Returns:
        A formatted prompt string ready to be passed as the ``prompt`` argument
        to ``GroqClient.complete`` alongside ``ASK_SYSTEM_PROMPT``.
    """
    return f"""### SYSTEM CONTEXT:
{system_context}

### QUESTION:
{question}

Provide the answer and command in the required JSON format."""
