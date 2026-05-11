from textual.app import App, ComposeResult
from textual.widgets import Header, Static
from textual.containers import Container

class LogWidget(Static):
    """Widget para mostrar los logs del bot."""
    log_content = ""

    def on_mount(self) -> None:
        self.update(self.log_content if self.log_content else "Esperando logs...")

class NeonHeader(Static):
    """Encabezado con estilo Cyberpunk."""
    def on_mount(self) -> None:
        self.update("NEON ARBITER")

class NeonApp(App):
    """Aplicación principal de la TUI."""
    # Aquí puedes añadir tu CSS más adelante
    CSS = """
    Screen {
        background: #000000;
    }
    .header {
        color: #0f0;
        text-align: center;
        text-style: bold;
        background: #111;
        height: 3;
        content-align: center middle;
        border: double #0f0;
    }
    .container {
        padding: 1;
    }
    LogWidget {
        border: solid #00ff00;
        color: #00ff00;
        background: #050505;
        height: 1fr;
    }
    """
    
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield NeonHeader(classes="header")
        yield Container(
            LogWidget(),
            classes="container"
        )

if __name__ == '__main__':
    app = NeonApp()
    app.run()

