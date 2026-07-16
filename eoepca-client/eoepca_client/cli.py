"""EOEPCA CLI."""

from __future__ import annotations

import functools
import json
import sys
import time
from collections.abc import Callable
from enum import StrEnum
from importlib.metadata import version
from typing import Annotated, Any, NoReturn, ParamSpec, TypeVar

import typer
from rich.console import Console
from rich.table import Table

from eoepca_client import auth
from eoepca_client.client import Client
from eoepca_client.models import StacItemRef
from eoepca_client.stac_tx import EoepcaError

app = typer.Typer(name="eoepca", no_args_is_help=True)
stac_cli = typer.Typer(help="STAC commands.", no_args_is_help=True)
item_cli = typer.Typer(help="STAC item transactions.")
stac_cli.add_typer(item_cli, name="item")
app.add_typer(stac_cli, name="stac")

console = Console()
err_console = Console(stderr=True)

P = ParamSpec("P")
R = TypeVar("R")


class OutputFormat(StrEnum):
    table = "table"
    json = "json"


def _exit_error(exc: Exception) -> NoReturn:
    code = exc.exit_code if isinstance(exc, EoepcaError) else 1
    err_console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=code) from exc


def _handle_errors(fn: Callable[P, R]) -> Callable[P, R]:  # noqa: UP047
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except Exception as exc:
            _exit_error(exc)

    return wrapper


def _print_json(data: Any) -> None:
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    console.print(json.dumps(data, indent=2, default=str))


def _print_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> None:
    table = Table(show_header=True, header_style="bold")
    for _, title in columns:
        table.add_column(title)
    for row in rows:
        table.add_row(*(row.get(key, "") for key, _ in columns))
    console.print(table)


def _bbox(value: str) -> list[float]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise typer.BadParameter("bbox must be W,S,E,N")
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        raise typer.BadParameter("bbox values must be numbers") from exc


def _expires_in(exp: int) -> str:
    delta = exp - int(time.time())
    if delta <= 0:
        return "expired"
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("eoepca-client"))
        raise typer.Exit()


@app.callback()
def main(
    version_flag: Annotated[
        bool | None,
        typer.Option("--version", "-V", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """EOEPCA client — login and STAC operations against eoapi."""


@app.command()
@_handle_errors
def login(
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
    username: Annotated[str | None, typer.Option("-u", "--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    client_id: Annotated[
        str | None,
        typer.Option(help="Override Keycloak client ID."),
    ] = None,
    client_secret: Annotated[
        str | None,
        typer.Option(
            help="Keycloak client secret (enables device flow).",
        ),
    ] = None,
) -> None:
    def _prompt() -> tuple[str, str]:
        return typer.prompt("Username"), typer.prompt("Password", hide_input=True)

    result = auth.login(
        Client(platform).profile,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        prompt=_prompt if sys.stdin.isatty() else None,
    )
    if result is None:
        typer.echo("Already logged in.")
    else:
        typer.echo("Login successful.")


@app.command()
def logout(
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
) -> None:
    auth.logout(platform)
    typer.echo("Logged out.")


@app.command()
@_handle_errors
def whoami(
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
    output: Annotated[
        OutputFormat, typer.Option("-o", "--output")
    ] = OutputFormat.table,
) -> None:
    bearer = auth.get_bearer(Client(platform).profile)
    if bearer is None:
        typer.echo("Not logged in. Run: eoepca login", err=True)
        raise typer.Exit(code=2)
    identity = auth.decode_whoami(bearer)
    if output == OutputFormat.json:
        _print_json(identity)
    else:
        _print_table(
            [
                {
                    "username": identity["preferred_username"],
                    "issuer": identity["iss"],
                    "expires_in": _expires_in(identity["exp"]),
                }
            ],
            [
                ("username", "Username"),
                ("issuer", "Issuer"),
                ("expires_in", "Expires in"),
            ],
        )


@stac_cli.command("collections")
@_handle_errors
def stac_collections(
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
    output: Annotated[
        OutputFormat, typer.Option("-o", "--output")
    ] = OutputFormat.table,
) -> None:
    cols = Client(platform).eoapi.list_collections()
    if output == OutputFormat.json:
        _print_json(cols)
    else:
        _print_table(
            [{"id": c.get("id", ""), "title": c.get("title") or ""} for c in cols],
            [("id", "ID"), ("title", "Title")],
        )


@stac_cli.command("search")
@_handle_errors
def stac_search(
    collection: Annotated[list[str], typer.Option("-c", "--collection")],
    bbox: Annotated[str | None, typer.Option("--bbox")] = None,
    datetime: Annotated[str | None, typer.Option("--datetime")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 10,
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
    output: Annotated[
        OutputFormat, typer.Option("-o", "--output")
    ] = OutputFormat.table,
) -> None:
    kwargs: dict[str, Any] = {
        "collections": collection,
        "limit": limit,
        "max_items": limit,
    }
    if bbox:
        kwargs["bbox"] = _bbox(bbox)
    if datetime:
        kwargs["datetime"] = datetime
    items = list(Client(platform).eoapi.stac().search(**kwargs).items())
    if output == OutputFormat.json:
        _print_json(
            {"type": "FeatureCollection", "features": [i.to_dict() for i in items]}
        )
    else:
        _print_table(
            [
                {
                    "id": r.id,
                    "collection": r.collection or "",
                    "datetime": r.datetime or "",
                    "bbox": ",".join(map(str, r.bbox)) if r.bbox else "",
                }
                for r in (StacItemRef.from_stac_dict(i.to_dict()) for i in items)
            ],
            [
                ("id", "ID"),
                ("collection", "Collection"),
                ("datetime", "Datetime"),
                ("bbox", "BBox"),
            ],
        )


@item_cli.command("add")
@_handle_errors
def stac_item_add(
    collection: Annotated[str, typer.Argument()],
    path_or_url: Annotated[str, typer.Argument()],
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
    output: Annotated[
        OutputFormat, typer.Option("-o", "--output")
    ] = OutputFormat.table,
) -> None:
    created = Client(platform).eoapi.stac_transactions.add_item(collection, path_or_url)
    if output == OutputFormat.json:
        _print_json(created)
    else:
        typer.echo(created.id)


@item_cli.command("rm")
@_handle_errors
def stac_item_rm(
    collection: Annotated[str, typer.Argument()],
    item_id: Annotated[str, typer.Argument()],
    platform: Annotated[str, typer.Option("-p", "--platform")] = "develop",
) -> None:
    Client(platform).eoapi.stac_transactions.delete_item(collection, item_id)


if __name__ == "__main__":
    app()
