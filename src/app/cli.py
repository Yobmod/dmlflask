import os
import click
from flask import Flask
from app import models


def register(app: Flask) -> None:
    @app.cli.group()  # adds function as base command ('translate')
    def translate() -> None:
        """Translation and localization commands."""
        pass

    @translate.command()  # add functions as to translate
    @click.argument('lang')  # add argument to translate
    def init(lang: str) -> None:
        """Initialize a new language. e.g. flask translate init <language-code>"""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):   # if function is True, it didn't return 0,
            raise RuntimeError('extract command failed')                        # so it failed -> then stop it
        if os.system(
                'pybabel init -i messages.pot -d app/translations -l ' + lang):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')

    @translate.command()
    def update() -> None:
        """Update all languages."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile() -> None:
        """Compile all languages."""
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')

    @app.cli.group()  # adds function as base command ('translate')
    def search() -> None:
        """Search indexing commands."""
        pass

    @search.command()
    def reindex() -> None:
        """Re-index database for search."""
        models.Post.reindex()
        print("search index updated")
