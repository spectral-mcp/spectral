"""Migrate stale tool files and app.json to current schema."""

from __future__ import annotations

import json
import re

import click

from cli.formats.app_meta import AppMeta
from cli.formats.mcp_tool import ToolDefinition, collect_param_refs
from cli.helpers.storage import store_root, tools_dir


@click.command()
def migrate() -> None:
    """Migrate on-disk tools and app.json to current schema."""
    apps_root = store_root() / "apps"
    if not apps_root.is_dir():
        click.echo("No apps found.")
        return

    apps_updated = 0
    tools_migrated = 0
    tools_removed = 0

    for d in sorted(apps_root.iterdir()):
        meta_path = d / "app.json"
        if not meta_path.is_file():
            continue

        app_name = d.name
        base_urls: list[str] = []

        # --- Fix app.json ---
        raw = json.loads(meta_path.read_text())
        if "base_url" in raw and "base_urls" not in raw:
            old_url = raw.pop("base_url")
            raw["base_urls"] = [old_url] if old_url else []
            meta = AppMeta.model_validate(raw)
            meta_path.write_text(meta.model_dump_json(indent=2))
            apps_updated += 1
            base_urls = meta.base_urls
        else:
            try:
                meta = AppMeta.model_validate(raw)
                base_urls = meta.base_urls
            except Exception:
                continue

        if not base_urls:
            continue

        # --- Fix tool files ---
        td = tools_dir(app_name)
        if not td.is_dir():
            continue

        for f in sorted(td.iterdir()):
            if f.suffix != ".json" or not f.is_file():
                continue

            try:
                tool_raw = json.loads(f.read_text())
            except Exception:
                click.echo(f"Warning: removing unreadable {f.name} for '{app_name}'", err=True)
                f.unlink()
                tools_removed += 1
                continue

            changed = False
            req = tool_raw.get("request", {})

            # Convert path → url
            if "path" in req and "url" not in req:
                req["url"] = base_urls[0] + req.pop("path")
                changed = True

            # Strip unused parameters
            props = tool_raw.get("parameters", {}).get("properties", {})
            if props:
                url_params = set(re.findall(r"\{(\w+)\}", req.get("url", "")))
                body_refs = collect_param_refs(req.get("body"))
                query_refs = collect_param_refs(req.get("query", {}))
                all_refs = url_params | body_refs | query_refs

                unused = set(props.keys()) - all_refs
                if unused:
                    for p in unused:
                        del props[p]
                    required = tool_raw.get("parameters", {}).get("required", [])
                    if required:
                        tool_raw["parameters"]["required"] = [
                            r for r in required if r not in unused
                        ]
                    changed = True

            if not changed:
                # Already up to date — still validate
                try:
                    ToolDefinition.model_validate(tool_raw)
                except Exception:
                    click.echo(f"Warning: removing invalid {f.name} for '{app_name}'", err=True)
                    f.unlink()
                    tools_removed += 1
                continue

            # Validate migrated tool
            try:
                tool = ToolDefinition.model_validate(tool_raw)
                f.write_text(tool.model_dump_json(indent=2))
                tools_migrated += 1
            except Exception as exc:
                click.echo(f"Warning: removing unfixable {f.name} for '{app_name}': {exc}", err=True)
                f.unlink()
                tools_removed += 1

    click.echo(f"{tools_migrated} tools migrated, {tools_removed} tools removed, {apps_updated} apps updated")
