from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag, TemplateString
from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import client
from trame.widgets import vuetify3 as v3
from trame_server import Server


@TrameApp()
class App:
    def __init__(self):
        self.server: Server = get_server()  # type: ignore
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
        builder = TrameCodeBuilder(self.state.vuetify_code)
        builder.build_trame_code()
        self.state.trame_code = builder.get_trame_code()


class TrameCodeBuilder:
    def __init__(self, vuetify_code):
        self.vuetify_code = vuetify_code
        self.trame_code = []

    def generate_attribute_list(self, attrs: dict[str, Any]):
        attribute_list = []

        for k, v in attrs.items():
            value_is_expression = False
            key = k.replace("-", "_")
            if key == "class":
                key = "classes"
            if key.startswith(":"):
                key = key[1:]
                value_is_expression = True

            value = v
            if value == "":
                value = True
            elif isinstance(value, list):
                value = f'"{" ".join(value)}"'
            else:
                value = f'"{value}"'

            if value_is_expression:
                value = f"({value},)"

            attribute_list.append(f"{key}={value}")

        return attribute_list

    def build_element(self, element: Tag, indent=0):
        if element.name:
            has_children = any(element.children)
            indentation = "    " * indent

            trame_tag = re.sub(
                r"-(\w)",
                lambda m: m.group(1).upper(),
                element.name[0].upper() + element.name[1:],
            )

            attribute_list = self.generate_attribute_list(element.attrs)
            attribute_string = ", ".join(attribute_list)

            if has_children:
                self.trame_code.append(
                    f"{indentation}with {trame_tag}({attribute_string}):"
                )
            else:
                self.trame_code.append(f"{indentation}{trame_tag}({attribute_string})")

            for child in element.children:
                if isinstance(child, Tag):
                    self.build_element(child, indent + 1)
                elif isinstance(child, TemplateString):
                    self.trame_code.append(f"{indentation}    '{child}'")
                else:
                    return
                    # print(isinstance(child, Tag))
                    # raise ValueError(f"Unknown child element type: {type(element)}")

    def build_trame_code(self):
        soup = BeautifulSoup(self.vuetify_code, "html.parser")
        for child in soup.children:
            if isinstance(child, Tag):
                self.build_element(child)
            elif isinstance(child, NavigableString):
                return
            else:
                raise ValueError(f"Unknown element type: {type(child)}")

    def get_trame_code(self):
        return "\n".join(self.trame_code)


if __name__ == "__main__":
    app = App()
    app.server.start()
