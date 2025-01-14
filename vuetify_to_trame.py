from __future__ import annotations

import re
from typing import Any

from black import FileMode, format_str
from bs4 import BeautifulSoup, Comment, NavigableString, Tag, TemplateString
from trame.app import get_server
from trame.decorators import TrameApp, change, trigger
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import client, code, html
from trame.widgets import vuetify3 as v3
from trame_server import Server


@TrameApp()
class App:
    def __init__(self):
        self.server: Server = get_server()  # type: ignore
        self.state = self.server.state

        self.state.trame__title = "Vuetify to Trame Converter"
        self.state.snackbar_show = False
        self.state.snackbar_text = ""
        self.state.snackbar_color = "green"
        self.state.vuetify_code = ""
        self.state.trame_code = ""
        self.state.link_editors = True
        self.state.line_limit = 80

        self.build_ui()

    def build_ui(self):
        with VAppLayout(self.server, theme="dark"):
            client.Style("html { overflow: hidden; }")
            client.Style(".v-snackbar__content { text-align: center; }")

            v3.VSnackbar(
                v_model="snackbar_show",
                text=("snackbar_text",),
                color=("snackbar_color",),
                timeout=3000,
            )

            with v3.VAppBar(elevation=0, color="blue"):
                v3.VToolbarTitle("Vuetify to Trame Converter")
                v3.VSpacer()
                v3.VTextField(
                    label="Line length limit",
                    v_model="line_limit",
                    type="number",
                    variant="underlined",
                    style="margin-right: 8px;",
                    hide_details=True,
                )

            with v3.VMain():
                with html.Div(
                    style="flex-grow: 1; display: flex; width: 100%; height: calc(100% - 64px);"
                ):
                    code.Editor(
                        v_model=("vuetify_code",),
                        language="html",
                        theme="vs-dark",
                        # https://microsoft.github.io/monaco-editor/docs.html#variables/editor.EditorOptions.html
                        options=("output_options", {}),
                    )
                    with html.Div(
                        style="display: flex; flex-direction: column; justify-content: center;"
                    ):
                        with html.Div(
                            style="display: flex; flex-direction: column; gap: 4px;"
                        ):
                            v3.VSpacer()
                            v3.VCheckboxBtn(
                                v_model=("link_editors",),
                                false_icon="mdi-link-off",
                                true_icon="mdi-link",
                                raw_attrs=[
                                    "v-tooltip=\"'Auto update Trame code when Vuetify code is changed'\"",
                                ],
                            )
                            v3.VBtn(
                                icon="mdi-content-copy",
                                variant="text",
                                size="small",
                                raw_attrs=[
                                    "v-tooltip=\"'Copy Trame code to clipboard'\"",
                                ],
                                click="window.navigator.clipboard.writeText(trame_code); trame.trigger('copied')",
                            )
                            v3.VSpacer()
                    code.Editor(
                        v_model=("trame_code",),
                        language="python",
                        theme="vs-dark",
                        # https://microsoft.github.io/monaco-editor/docs.html#variables/editor.EditorOptions.html
                        options=("output_options", {"readOnly": True}),
                    )

    @trigger("copied")
    def on_copied(self):
        self.state.snackbar_show = True
        self.state.snackbar_text = "Copied to clipboard"
        self.state.snackbar_color = "green"

    @change("vuetify_code", "link_editors")
    def convert_code(self, **_):
        if not self.state.link_editors:
            return

        if not self.state.line_limit:
            self.state.line_limit = 80

        builder = TrameCodeBuilder(
            self.state.vuetify_code,  # type: ignore
            line_limit=self.state.line_limit,
        )
        builder.build_trame_code()
        self.state.trame_code = builder.get_trame_code()


class TrameCodeBuilder:
    def __init__(self, vuetify_code: str, *, line_limit: int = 80):
        self.vuetify_code = vuetify_code.strip()
        self.line_limit = line_limit
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
            has_children = any(
                not isinstance(child, (TemplateString, NavigableString))
                for child in element.children
            )
            indentation = "    " * indent

            trame_tag = re.sub(
                r"-(\w)",
                lambda m: m.group(1).upper(),
                element.name[0].upper() + element.name[1:],
            )

            attribute_list = self.generate_attribute_list(element.attrs)
            if element.string and element.string.strip():
                attribute_list.insert(0, f'"{element.string.strip()}"')
            attribute_string = ", ".join(attribute_list)
            if len(attribute_list) > 3:
                attribute_string += ","

            if has_children:
                self.trame_code.append(
                    f"{indentation}with v3.{trame_tag}({attribute_string}):"
                )
            else:
                self.trame_code.append(
                    f"{indentation}v3.{trame_tag}({attribute_string})"
                )

            for child in element.children:
                if isinstance(child, Tag):
                    self.build_element(child, indent + 1)
                elif isinstance(child, (TemplateString, NavigableString)):
                    continue
                elif isinstance(child, Comment):
                    if len(child.strip()):
                        self.trame_code.append(f"{indentation}# {child}")
                else:
                    raise ValueError(
                        f'Unknown child element type: {type(child)} "{child}"'
                    )

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
        raw_code = "\n".join(self.trame_code)
        return format_str(raw_code, mode=FileMode(line_length=self.line_limit))


if __name__ == "__main__":
    app = App()
    app.server.start()
