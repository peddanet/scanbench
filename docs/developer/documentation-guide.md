# Documentation guide

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

## Structure

~~~text
README.md               project entry on GitHub; links the documentation home
docs/README.md          documentation home: lead document of all areas
docs/glossary.md        every technical term, with a link for further reading
docs/user/README.md     user guide: one page with clickable table of contents
docs/user/img/          screenshots of the user guide
docs/developer/         developer documentation, lead document README.md
docs/concept/           design documents and revisions, lead document README.md
~~~

## Rules

1. **Lead documents.** Whenever an area has more than one document, its
   `README.md` is the lead document and links every page of the area with a
   one-line description. `docs/README.md` links all lead documents. A new page
   is added to its lead document in the same commit. The user documentation
   is deliberately one page (`docs/user/README.md`) with a numbered,
   clickable table of contents; the developer documentation is split into
   one page per functional unit.
2. **Back links.** Every page starts with a line
   `Back to: [lead document](README.md) · [Documentation home](../README.md)`.
3. **Planned pages** are listed in the lead document without a link, with the
   milestone that brings them; no empty placeholder files.
4. **Language** of all documentation is English; user-visible program text is
   English and translated by Qt translation files.
5. **Glossary.** Every technical term used in a document is explained in
   `docs/glossary.md` (or, for design terms, in the concept glossary) with a
   link for further reading.
6. **Commands** are complete, copy-paste-ready code blocks fenced with `~~~`.
   Each command states its privilege level (normal user, `sudo` from the user
   context, root shell) and why.
7. **Diagrams** are written in Mermaid inside the Markdown; GitHub renders
   them. Diagrams for PDF documents are rendered to PNG from sources kept next
   to the document (`docs/concept/diagrams`).
8. **Sources.** Statements about external software, standards or services
   link their source.
9. **No private data** in documentation; examples use placeholder addresses
   such as `192.168.0.10`.
10. **Same pull request.** A change that users or developers notice updates
    the documentation in the pull request that makes the change.

## PDF documents

Concept and handover documents are kept as Markdown and built to PDF with
pandoc and XeLaTeX; the Markdown is the source, the PDF is committed next to
it. Rebuild from the directory of the document (normal user):

~~~bash
cd docs/concept
pandoc scanbench-concept.md -o scanbench-concept.pdf --pdf-engine=xelatex
~~~
