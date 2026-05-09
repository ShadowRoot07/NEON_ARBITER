import textual as t
from textual.app import App, Compositor
from textual.containers import Container
from textual.reactive import var
from textual.widget import Widget

class LogWidget(Widget):
    log = var('')

    def compose(self) -> Compositor:
        yield Container(self.log)

class Header(Widget):
    def compose(self) -> Compositor:
        yield Container('NEON ARBITER', classes='header')

class App(App):
    CSS = ''
    BINDINGS = []

    def compose(self) -> Compositor:
        yield Container(
            Header(),
            LogWidget(),
            classes='container'
        )
