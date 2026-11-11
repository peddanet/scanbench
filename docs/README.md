# scanbench documentation

Back to: [project README](../README.md)

This is the lead document of the whole documentation. Every area has its own
lead document that links all of its pages; every page links back to its lead
document and to this page.

| Area | Lead document | Audience |
|---|---|---|
| User documentation | [user/README.md](user/README.md) | people who install and use scanbench |
| Developer documentation | [developer/README.md](developer/README.md) | contributors and maintainers |
| Concept | [concept/README.md](concept/README.md) | anyone who wants the design rationale |
| Glossary | [glossary.md](glossary.md) | all; every technical term used in the documentation |

## Map of all documents

~~~text
docs/
  README.md                     this page
  glossary.md                   technical terms with links
  user/
    README.md                   lead: user documentation
    installation.md             system packages, install.sh, desktop entry, uninstall
    getting-started.md          first start, commands, directories
    updating.md                 new releases, live switching, update and publish
    documents.md                scanning documents, duplex, PDF sizes
    photo-album.md              scanning photo albums, frames, confirmation
    printing.md                 CUPS printers and driver options
    troubleshooting.md          scanbench doctor, scanner not found, desktop icon, printing
    img/                        screenshots
  developer/
    README.md                   lead: developer documentation
    architecture.md             layers, modules, patterns (Mermaid diagrams)
    coding-standard.md          rules and measurable limits
    quality-gates.md            tools/check.sh, the six gates, pre-push hook
    ci.md                       GitHub Actions workflow and branch protection
    release-process.md          git-flow, versions, tags, patch delivery
    documentation-guide.md      how this documentation is organised
  concept/
    README.md                   lead: concept, revisions, roadmap, decisions
    scanbench-concept.md / .pdf concept revision 1
    img/, diagrams/             rendered diagrams and their Mermaid sources
~~~

Language of all documentation: English.
