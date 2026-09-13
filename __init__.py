"""API publique du paquet Didacode."""

from .didacode import (
    CodeHighlighter,
    Config,
    DocumentGenerator,
    ErreurGeneration,
    MarkdownConverter,
    PDFGenerator,
    RegistreAncres,
    RessourceRefusee,
    __version__,
    generer_pdf,
    main,
)

__all__ = [
    "CodeHighlighter",
    "Config",
    "DocumentGenerator",
    "ErreurGeneration",
    "MarkdownConverter",
    "PDFGenerator",
    "RegistreAncres",
    "RessourceRefusee",
    "__version__",
    "generer_pdf",
    "main",
]
