"""CLI command definitions using Click."""

from __future__ import annotations

import sys
from typing import Any

import click

from genai_cli import __version__
from genai_cli.auth import AuthError, AuthManager
from genai_cli.client import GenAIClient
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.streaming import stream_or_complete


pass_config = click.make_pass_decorator(ConfigManager, ensure=True)


@click.group(invoke_without_command=True)
@click.option("--model", "-m", default=None, help="Override model for this invocation")
@click.option("--prompt", "-p", "prompt_name", default=None, help="System prompt profile to use")
@click.option("--session-id", default=None, help="Reuse an existing session ID (e.g., from web UI)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--config", "-c", "config_path", default=None, help="Custom config file")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
@click.version_option(__version__, prog_name="genai-cli")
@click.pass_context
def main(
    ctx: click.Context,
    model: str | None,
    prompt_name: str | None,
    session_id: str | None,
    verbose: bool,
    config_path: str | None,
    json_out: bool,
) -> None:
    """Corporate AI CLI Agent — chat with AI from your terminal."""
    overrides: dict[str, Any] = {}
    if model:
        overrides["default_model"] = model
    if verbose:
        overrides["verbose"] = True

    ctx.ensure_object(dict)
    config = ConfigManager(config_path=config_path, cli_overrides=overrides)
    ctx.obj["config"] = config
    ctx.obj["display"] = Display()
    ctx.obj["verbose"] = verbose
    ctx.obj["json_out"] = json_out
    ctx.obj["session_id"] = session_id

    # Activate prompt profile if specified
    if prompt_name:
        from genai_cli.prompts.registry import PromptRegistry

        registry = PromptRegistry(config)
        agent_name = config.settings.agent_name
        body = registry.load_prompt_body(prompt_name, agent_name)
        if body is None:
            click.echo(f"Error: unknown prompt profile '{prompt_name}'", err=True)
            ctx.exit(1)
            return
        config.set_active_prompt(prompt_name, body)

    if ctx.invoked_subcommand is None:
        from genai_cli.repl import ReplSession

        repl = ReplSession(ctx.obj["config"], ctx.obj["display"], session_id=session_id)
        repl.run()


@main.command()
@click.argument("message")
@click.option("--files", "-f", multiple=True, help="Files/directories to include")
@click.option(
    "--type", "-t", "file_type", default="all",
    help="File type filter: code|docs|scripts|notebooks|all",
)
@click.option("--no-stream", is_flag=True, help="Disable streaming")
@click.option("--auto-apply", is_flag=True, help="Auto-apply file changes")
@click.option("--agent", is_flag=True, help="Enable agent mode")
@click.option("--max-rounds", default=5, help="Max agent loop iterations")
@click.option("--dry-run", is_flag=True, help="Show changes without applying")
@click.pass_context
def ask(
    ctx: click.Context,
    message: str,
    files: tuple[str, ...],
    file_type: str,
    no_stream: bool,
    auto_apply: bool,
    agent: bool,
    max_rounds: int,
    dry_run: bool,
) -> None:
    """Send a one-shot message to the AI."""
    from genai_cli.bundler import FileBundler

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]
    auth = AuthManager()

    try:
        client = GenAIClient(config, auth)
    except AuthError as e:
        display.print_error(str(e))
        sys.exit(1)

    model_name = config.settings.default_model
    model_info = config.get_model(model_name)
    if model_info:
        display.print_info(f"Model: {model_info.display_name}")

    # Bundle and upload files if provided
    import uuid

    session_id = str(uuid.uuid4())

    if files:
        bundler = FileBundler(config)
        ft = file_type if file_type != "all" else None
        bundles, _unmatched = bundler.bundle_files(list(files), file_type=ft)
        for bundle in bundles:
            display.print_bundle_summary(
                bundle.file_type, bundle.file_count, bundle.estimated_tokens
            )
        if bundles:
            try:
                client.ensure_session(session_id, model_name)
                client.upload_bundles(session_id, bundles)
                display.print_success("Files uploaded")
            except Exception as e:
                display.print_error(f"Upload failed: {e}")
                sys.exit(1)

    use_streaming = not no_stream and config.settings.streaming

    try:
        full_text, chat_msg = stream_or_complete(
            client, message, model_name, session_id, config, use_streaming
        )
    except AuthError as e:
        display.print_error(str(e))
        sys.exit(1)
    except Exception as e:
        display.print_error(f"Request failed: {e}")
        sys.exit(1)

    display.print_message(full_text, role="assistant")

    if chat_msg and chat_msg.tokens_consumed:
        display.print_info(
            f"Tokens: {chat_msg.tokens_consumed:,} | "
            f"Cost: ${chat_msg.token_cost:.4f}"
        )

    client.close()


@main.group()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Manage authentication."""


@auth.command("login")
@click.pass_context
def auth_login(ctx: click.Context) -> None:
    """Login by providing your bearer token and API URL."""
    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]
    auth_mgr = AuthManager()

    token = click.prompt("Paste your Bearer token from browser DevTools", hide_input=True)
    api_url = click.prompt("Enter API base URL (e.g. https://api-genai.example.com)")

    auth_mgr.save_token(token)

    # Save API URL to user config
    from pathlib import Path

    import yaml

    user_config_path = Path.home() / ".genai-cli" / "settings.yaml"
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if user_config_path.is_file():
        with open(user_config_path) as f:
            existing = yaml.safe_load(f) or {}
    existing["api_base_url"] = api_url

    web_url = click.prompt(
        "Enter Web UI URL (e.g. https://genai.example.com)",
        default=api_url.replace("api-", "").rstrip("/"),
    )
    existing["web_ui_url"] = web_url

    with open(user_config_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)

    display.print_success("Token saved to ~/.genai-cli/.env")
    display.print_success(f"API URL saved: {api_url}")

    # Verify
    token_obj = auth_mgr.load_token()
    if token_obj and token_obj.email:
        display.print_success(f"Logged in as: {token_obj.email}")
        remaining = auth_mgr.time_remaining(token_obj)
        display.print_info(f"Token expires in: {remaining}")


@auth.command("verify")
@click.pass_context
def auth_verify(ctx: click.Context) -> None:
    """Verify the current auth token."""
    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]
    auth_mgr = AuthManager()

    token_obj = auth_mgr.load_token()
    if token_obj is None:
        display.print_error("No token found. Run 'genai auth login'.")
        sys.exit(1)

    if token_obj.email:
        display.print_success(f"Email: {token_obj.email}")
    if token_obj.expires_at:
        display.print_info(f"Expires: {token_obj.expires_at.isoformat()}")
        remaining = auth_mgr.time_remaining(token_obj)
        if auth_mgr.is_expired(token_obj):
            display.print_error("Token has EXPIRED. Run 'genai auth login'.")
            sys.exit(1)
        display.print_info(f"Time remaining: {remaining}")

    # Try to call usage endpoint
    try:
        client = GenAIClient(config, auth_mgr)
        usage = client.get_usage()
        display.print_success("API connection verified")
        display.print_usage(config.mapper.map_usage(usage))
        client.close()
    except AuthError as e:
        display.print_error(f"API verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        display.print_warning(f"Could not verify API connection: {e}")


@main.command("history")
@click.option("--limit", default=10, help="Number of sessions to show")
@click.pass_context
def history(ctx: click.Context, limit: int) -> None:
    """List recent conversations."""
    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]
    auth_mgr = AuthManager()

    try:
        client = GenAIClient(config, auth_mgr)
        sessions = client.list_history(limit=limit)
        mapper = config.mapper
        mapped = [mapper.map_history_entry(s) for s in sessions]
        display.print_history(mapped)
        client.close()
    except AuthError as e:
        display.print_error(str(e))
        sys.exit(1)
    except Exception as e:
        display.print_error(f"Failed to fetch history: {e}")
        sys.exit(1)


@main.command("usage")
@click.pass_context
def usage(ctx: click.Context) -> None:
    """Show token usage and costs."""
    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]
    auth_mgr = AuthManager()

    try:
        client = GenAIClient(config, auth_mgr)
        usage_data = client.get_usage()
        mapped_usage = config.mapper.map_usage(usage_data)
        display.print_usage(mapped_usage)
        client.close()
    except AuthError as e:
        display.print_error(str(e))
        sys.exit(1)
    except Exception as e:
        display.print_error(f"Failed to fetch usage: {e}")
        sys.exit(1)


@main.command("models")
@click.pass_context
def models(ctx: click.Context) -> None:
    """List all available models."""
    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    all_models = config.get_all_models()
    display.print_models_table(all_models)


@main.group("config")
@click.pass_context
def config_cmd(ctx: click.Context) -> None:
    """View or update configuration."""


@config_cmd.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str) -> None:
    """Get a config value."""
    config: ConfigManager = ctx.obj["config"]
    value = config.get(key)
    if value is None:
        click.echo(f"Key '{key}' not found")
    else:
        click.echo(f"{key} = {value}")


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a config value in user settings."""
    from pathlib import Path

    import yaml

    display: Display = ctx.obj["display"]
    user_config_path = Path.home() / ".genai-cli" / "settings.yaml"
    user_config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if user_config_path.is_file():
        with open(user_config_path) as f:
            existing = yaml.safe_load(f) or {}

    # Type coercion
    if value.lower() in ("true", "false"):
        existing[key] = value.lower() == "true"
    elif value.isdigit():
        existing[key] = int(value)
    else:
        try:
            existing[key] = float(value)
        except ValueError:
            existing[key] = value

    with open(user_config_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)

    display.print_success(f"Set {key} = {existing[key]}")


@main.command("files")
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--type", "-t", "file_type", default="all",
    help="File type filter: code|docs|scripts|notebooks|all",
)
@click.pass_context
def files_cmd(ctx: click.Context, paths: tuple[str, ...], file_type: str) -> None:
    """Preview files that would be bundled for upload."""
    from genai_cli.bundler import FileBundler

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    bundler = FileBundler(config)
    ft = file_type if file_type != "all" else None
    bundles, _unmatched = bundler.bundle_files(list(paths), file_type=ft)

    if not bundles:
        display.print_warning("No files found matching criteria")
        return

    for bundle in bundles:
        display.print_bundle_summary(
            bundle.file_type, bundle.file_count, bundle.estimated_tokens
        )
        display.print_file_list(bundle.file_paths)


@main.command("bundle")
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output", "-o", default="bundle.txt",
    help="Output file path (default: bundle.txt)",
)
@click.option(
    "--type", "-t", "file_type", default="all",
    help="File type filter: code|docs|scripts|notebooks|all",
)
@click.pass_context
def bundle_cmd(
    ctx: click.Context, paths: tuple[str, ...], output: str, file_type: str
) -> None:
    """Bundle files into a single .txt file for upload."""
    from pathlib import Path

    from genai_cli.bundler import FileBundler

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    bundler = FileBundler(config)
    ft = file_type if file_type != "all" else None
    output_path = Path(output)

    file_count, total_bytes, unmatched = bundler.write_bundle(
        list(paths), output_path, file_type=ft
    )

    if unmatched:
        display.print_warning(f"No files found for: {', '.join(unmatched)}")

    if file_count == 0:
        display.print_warning("No files found matching criteria")
        return

    display.print_success(
        f"Bundled {file_count} file(s) ({total_bytes:,} bytes) → {output_path}"
    )


@main.command("resume")
@click.argument("session_id")
@click.pass_context
def resume_cmd(ctx: click.Context, session_id: str) -> None:
    """Resume a saved conversation."""
    from genai_cli.repl import ReplSession

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    repl = ReplSession(config, display, session_id=session_id)
    repl.run()


@main.group("skill")
@click.pass_context
def skill_cmd(ctx: click.Context) -> None:
    """Manage and invoke skills."""


@skill_cmd.command("list")
@click.pass_context
def skill_list(ctx: click.Context) -> None:
    """List all available skills."""
    from genai_cli.skills.registry import SkillRegistry

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    registry = SkillRegistry(config)
    skills = registry.list_skills()
    if not skills:
        display.print_warning("No skills found")
        return

    from rich.table import Table

    table = Table(title="Available Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Description")

    for s in skills:
        desc = s.description[:60] + "..." if len(s.description) > 60 else s.description
        table.add_row(s.name, s.category, desc.strip())

    display._console.print(table)


@skill_cmd.command("invoke")
@click.argument("name")
@click.option("--files", "-f", multiple=True, help="Files/directories to include")
@click.option("--auto-apply", is_flag=True, help="Auto-apply changes")
@click.option("--dry-run", is_flag=True, help="Preview without applying")
@click.option("--max-rounds", default=5, help="Max agent rounds")
@click.option("--message", "-m", default="", help="Additional message")
@click.pass_context
def skill_invoke(
    ctx: click.Context,
    name: str,
    files: tuple[str, ...],
    auto_apply: bool,
    dry_run: bool,
    max_rounds: int,
    message: str,
) -> None:
    """Invoke a skill by name."""
    from genai_cli.skills.executor import SkillExecutor
    from genai_cli.skills.registry import SkillRegistry

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    registry = SkillRegistry(config)
    executor = SkillExecutor(config, display, registry)

    result = executor.execute(
        name,
        message=message,
        files=list(files) if files else None,
        auto_apply=auto_apply,
        dry_run=dry_run,
        max_rounds=max_rounds,
    )

    if result:
        display.print_info(
            f"\nSkill completed: {len(result.rounds)} rounds, "
            f"{len(result.total_files_applied)} files modified"
        )


@main.group("prompt")
@click.pass_context
def prompt_cmd(ctx: click.Context) -> None:
    """Manage system prompt profiles."""


@prompt_cmd.command("list")
@click.pass_context
def prompt_list(ctx: click.Context) -> None:
    """List all available prompt profiles."""
    from genai_cli.prompts.registry import PromptRegistry

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    registry = PromptRegistry(config)
    prompts = registry.list_prompts()
    if not prompts:
        display.print_warning("No prompts found")
        return

    from rich.table import Table

    table = Table(title="Available Prompt Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Description")

    active = config.active_prompt_name
    for p in prompts:
        name = f"* {p.name}" if p.name == active else p.name
        desc = p.description[:60] + "..." if len(p.description) > 60 else p.description
        table.add_row(name, p.category, desc.strip())

    display._console.print(table)


@prompt_cmd.command("show")
@click.argument("name")
@click.pass_context
def prompt_show(ctx: click.Context, name: str) -> None:
    """Display the full body of a prompt profile."""
    from genai_cli.prompts.registry import PromptRegistry

    config: ConfigManager = ctx.obj["config"]
    display: Display = ctx.obj["display"]

    registry = PromptRegistry(config)
    agent_name = config.settings.agent_name
    body = registry.load_prompt_body(name, agent_name)
    if body is None:
        display.print_error(f"Prompt not found: {name}")
        return

    from rich.markdown import Markdown

    display._console.print(Markdown(body))


if __name__ == "__main__":
    main()
