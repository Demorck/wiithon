import typer

from wiithon.cli.dol import dol_app
from wiithon.cli.iso import iso_app
from wiithon.cli.rarc import rarc_app

app = typer.Typer(help="Wii ISO patching and inspection tool.")

app.add_typer(iso_app,  name="iso")
app.add_typer(dol_app,  name="dol")

app.add_typer(rarc_app, name="rarc")

__all__ = ["app"]