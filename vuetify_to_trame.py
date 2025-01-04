import re

from bs4 import BeautifulSoup
from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import client
from trame.widgets import vuetify3 as v3
from trame_server import Server


@TrameApp()
class App:
    def __init__(self):
        self.server: Server = get_server()
        self.state = self.server.state

        self.state.vuetify_code = ""
        self.state.trame_code = ""

        self.build_ui()

    def build_ui(self):
        with SinglePageLayout(self.server, theme="dark") as layout:
            client.Style(
                '.v-input--horizontal { grid-template-areas: "prepend control append append"; grid-template-rows: auto;'
            )
            client.Style(".v-field__input { height: 100% !important; }")
            with layout.content:
                with v3.VContainer(fluid=True, height="100%", style="display: flex;"):
                    with v3.VRow(style="flex-grow: 1;"):
                        with v3.VCol(cols=6):
                            v3.VTextarea(
                                label="Vuetify Code",
                                v_model="vuetify_code",
                                style="height: 100%;",
                                rows="calc(100vh / 20px)",
                                row_height=20,
                                no_resize=True,
                                hide_details=True,
                            )
                        with v3.VCol(cols=6):
                            v3.VTextarea(
                                label="Trame Code",
                                v_model="trame_code",
                                style="height: 100%",
                                rows=20,
                                row_height=20,
                                no_resize=True,
                                hide_details=True,
                                readonly=True,
                            )

    @change("vuetify_code")
    def convert_code(self, **_):
        soup = BeautifulSoup(self.state.vuetify_code, "html.parser")

        trame_code = []

        def build_element(element, indent: int = 0):
            if element.name:
                has_children = any(element.children)
                indentaton = "    " * indent

                trame_tag = re.sub(
                    r"-(\w)",
                    lambda m: m.group(1).upper(),
                    element.name[0].upper() + element.name[1:],
                )

                attribute_list = ", ".join(
                    [
                        f"{'classes' if k == 'class' else k}={True if v == '' else f'\"{' '.join(v)}\"' if isinstance(v, list) else f'\"{v}\"'}"
                        for k, v in element.attrs.items()
                    ]
                )

                if has_children:
                    trame_code.append(
                        f"{indentaton}with {trame_tag}({attribute_list}):"
                    )
                else:
                    trame_code.append(f"{indentaton}{trame_tag}({attribute_list})")

                for child in element.children:
                    if child.name:
                        build_element(child, indent + 1)

        for child in soup.children:
            build_element(child)

        self.state.trame_code = "\n".join(trame_code)


if __name__ == "__main__":
    app = App()
    app.server.start()
