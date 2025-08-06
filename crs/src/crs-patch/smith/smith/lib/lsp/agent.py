from pathlib import Path
from typing import List
import subprocess

from .pylspclient.pylspclient import JsonRpcEndpoint, LspEndpoint, LspClient
from .pylspclient.pylspclient.lsp_pydantic_strcuts import * # pylint: disable=wildcard-import, unused-wildcard-import
from ...constants import LSP_TIMEOUT # pylint: disable=relative-beyond-top-level

class LspAgent():
    # TODO: Workspace-specific command line options for optimization
    def __init__(self, language_server_binary: Path, language: str):
        assert (
            subprocess.run(["which", language_server_binary], check=False).returncode == 0
        ), f"{language_server_binary} is not installed"

        self.languageId = LanguageIdentifier[language.upper()] # pylint: disable=invalid-name
        self.proc = subprocess.Popen(
            [language_server_binary],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        assert self.proc.stdin is not None and self.proc.stdout is not None
        endpoint = LspEndpoint(
            JsonRpcEndpoint(self.proc.stdin, self.proc.stdout),
            timeout=LSP_TIMEOUT
        )
        self.client = LspClient(endpoint)

        self.client.initialize(
            processId=None,
            rootPath=None,
            rootUri=None,
            initializationOptions=None,
            capabilities={},
            trace="off",
            workspaceFolders=None
        )

    def terminate(self):
        self.client.shutdown()
        self.client.exit()
        self.proc.kill()
        self.proc.terminate()

    def get_definition(self, file: Path, position: Position) -> List[Location]:
        # TODO: Do we have to increase the version number?
        self.client.didOpen(
            TextDocumentItem(
                uri=f"file://{file}",
                languageId=self.languageId,
                version=1,
                text=file.read_text()
            )
        )
        definitions = self.client.definition(
            TextDocumentIdentifier(uri=f"file://{file}"),
            position
        )

        if not isinstance(definitions, list):
            return [definitions]

        if not isinstance(definitions[0], Location):
            # Validation error
            return []

        return definitions              # type: ignore

    def get_references(
        self,
        file: Path,
        position: Position,
        include_declaration: bool = False
    ) -> List[Location]:
        self.client.didOpen(
            TextDocumentItem(
                uri=f"file://{file}",
                languageId=self.languageId,
                version=1,
                text=file.read_text()
            )
        )
        references = self.client.references(
            TextDocumentIdentifier(uri=f"file://{file}"),
            position,
            context=ReferenceContext(includeDeclaration=include_declaration)
        )

        return references
