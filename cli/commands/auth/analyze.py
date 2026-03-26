"""Generate and validate token acquisition functions using LLM.

The LLM receives trace summaries, discovers the auth mechanism itself,
and generates ``acquire_token()`` / ``refresh_token()`` functions.
The generated script is then tested interactively: ``acquire_token()`` is
called (prompting the user for credentials), and if it fails the error is
fed back to the LLM on the same conversation for correction.  The same
validation loop runs for ``refresh_token()`` when present.

Raises ``NoAuthDetected`` if the LLM concludes there is no auth.

Also contains the ``spectral auth analyze`` Click command.
"""

from __future__ import annotations

import traceback

import click

from cli.helpers.auth.errors import AuthScriptError, AuthScriptInvalid
from cli.helpers.auth.generation import (
    extract_script,
    get_auth_instructions,
    script_has_refresh,
)
from cli.helpers.auth.runtime import call_auth_module_source
from cli.helpers.auth.usage import result_to_token_state
from cli.helpers.console import console
from cli.helpers.context import build_timeline
from cli.helpers.llm import Conversation, init_debug
from cli.helpers.prompt import render
from cli.helpers.storage import auth_script_path, load_app_bundle, resolve_app

_MAX_FIX_ATTEMPTS = 5


@click.command()
@click.argument("app_name")
@click.option(
    "--debug", is_flag=True, default=False, help="Save LLM prompts/responses to debug/"
)
def analyze(app_name: str, debug: bool) -> None:
    """Analyze auth mechanism for an app and generate an auth script."""

    resolve_app(app_name)
    console.print(f"[bold]Loading captures for app:[/bold] {app_name}")
    bundle = load_app_bundle(app_name)
    console.print(f"  Loaded {len(bundle.traces)} traces")

    init_debug(debug=debug)

    conv = Conversation(
        system=[build_timeline(bundle)],
        max_tokens=8192,
        label="generate_auth_script",
        tool_names=["decode_base64", "decode_url", "decode_jwt", "inspect_trace"],
        bundle=bundle,
    )

    # ── Step 1: initial generation ──────────────────────────────────────
    try:
        script = extract_script(conv.ask_text(get_auth_instructions()))
    except AuthScriptInvalid:
        console.print("[red]Failed to generate auth script[/red]")
        console.print("[red]Run again with --debug[/red]")
        return

    if script is None:
        console.print()
        console.print(
            "[dim]No authentication mechanism detected in traces. "
            "No script generated.[/dim]"
        )
        return

    # ── Step 2: validate acquire_token in a fix loop ────────────────────
    script = _validate_function(
        conv, script, fn="acquire_token", fn_args=(), label="acquire"
    )
    if script is None:
        return

    # Save the working script (acquire confirmed OK)
    script_path = auth_script_path(app_name)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script)

    # ── Step 3: validate refresh_token if present ───────────────────────
    if script_has_refresh(script):
        console.print("[bold]Testing refresh_token()...[/bold]")

        # We need a refresh token from the acquire result to test refresh.
        # Re-run acquire to get the result (script is already validated).
        output: list[str] = []
        try:
            acquire_result = call_auth_module_source(script, "acquire_token", output)
            token_state = result_to_token_state(acquire_result)
        except AuthScriptError:
            # acquire worked before but fails now (e.g. OTP expired) — skip refresh test
            console.print(
                "[yellow]Could not obtain a fresh token to test refresh. "
                "Skipping refresh validation.[/yellow]"
            )
            console.print(f"[green]Auth script written to {script_path}[/green]")
            return

        if token_state.refresh_token is None:
            console.print(
                "[dim]acquire_token() did not return a refresh_token. "
                "Skipping refresh validation.[/dim]"
            )
        else:
            script = _validate_function(
                conv,
                script,
                fn="refresh_token",
                fn_args=(token_state.refresh_token,),
                label="refresh",
            )
            if script is not None:
                script_path.write_text(script)
    else:
        console.print("[dim]No refresh_token() in script — skipping refresh validation.[/dim]")

    console.print(f"[green]Auth script written to {script_path}[/green]")


# ── Shared fix loop ────────────────────────────────────────────────────────


def _validate_function(
    conv: Conversation,
    script: str,
    *,
    fn: str,
    fn_args: tuple[object, ...] = (),
    label: str,
) -> str | None:
    """Run *fn* from *script*, and if it fails ask the LLM to fix it.

    Returns the (possibly corrected) script, or ``None`` if all attempts
    were exhausted.
    """

    for attempt in range(_MAX_FIX_ATTEMPTS):
        output: list[str] = []
        try:
            call_auth_module_source(script, fn, output, *fn_args)
            console.print(f"[green]{fn}() succeeded.[/green]")
            return script
        except AuthScriptError:
            error_trace = traceback.format_exc()
            console.print(f"[red]{fn}() failed (attempt {attempt + 1}/{_MAX_FIX_ATTEMPTS}):[/red]")
            console.print(error_trace)

        # Ask the LLM to fix the script on the same conversation
        prompt = render(
            "auth-fix.j2",
            traceback=error_trace,
            script_stdout="".join(output),
        )
        text = conv.ask_text(prompt)

        try:
            fixed = extract_script(text)
        except AuthScriptInvalid as e:
            console.print(f"[red]LLM produced invalid code:[/red] {e}")
            continue

        if fixed is None:
            console.print(
                f"[red]LLM returned NO_AUTH while trying to fix {fn}(). Aborting.[/red]"
            )
            return None

        script = fixed
        console.print("[green]Script updated by LLM. Retrying...[/green]")

    console.print(
        f"[red]Exhausted {_MAX_FIX_ATTEMPTS} fix attempts for {fn}(). "
        f"The LLM was unable to produce a working script.[/red]"
    )
    raise click.ClickException(
        "Run 'spectral auth analyze' again to regenerate from scratch."
    )
