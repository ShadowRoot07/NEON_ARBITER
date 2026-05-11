from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Static
from textual.containers import Container, Vertical

class NeonHeader(Static):
    """Encabezado Cyberpunk."""
    def on_mount(self) -> None:
        self.update(" [bold #00ff00]⚡ NEON ARBITER v1.0[/bold #00ff00] | [cyan]Shadow_Grimorio Edition[/cyan] ")

class NeonApp(App):
    """Interfaz TUI mejorada."""
    CSS = """
    Screen {
        background: #050505;
    }
    .header {
        color: #00ff00;
        background: #111;
        height: 3;
        content-align: center middle;
        border-bottom: double #00ff00;
        margin-bottom: 1;
    }
    RichLog {
        border: solid #333;
        background: #000;
        color: #eee;
        padding: 1;
    }
    """

    BINDINGS = [("q", "quit", "Salir"), ("c", "clear", "Limpiar Logs")]

    def compose(self) -> ComposeResult:
        yield NeonHeader(classes="header")
        yield Vertical(
            RichLog(highlight=True, markup=True, id="main_log"),
            classes="container"
        )
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write("[bold green]SISTEMA INICIADO...[/bold green]")
        log.write("[blue]Conectando con Oráculo Spica...[/blue]")

    def action_clear(self) -> None:
        self.query_one(RichLog).clear()

if __name__ == '__main__':
    app = NeonApp()
    app.run()

