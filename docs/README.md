# scanbench documentation

Back to: [project README](../README.md)

This is the lead document of the whole documentation. An area with several
pages has a lead document that links all of them; every page links back to
its lead document and to this page. The user documentation is a single guide
with a clickable table of contents.

| Area | Lead document | Audience |
|---|---|---|
| User guide | [user/README.md](user/README.md) | people who install and use scanbench |
| Developer documentation | [developer/README.md](developer/README.md) | contributors and maintainers |
| Concept | [concept/README.md](concept/README.md) | anyone who wants the design rationale |
| Glossary | [glossary.md](glossary.md) | all; every technical term used in the documentation |

## Map of all documents

~~~text
docs/
  README.md                     this page
  glossary.md                   technical terms with links
  user/
    README.md                   user guide: installation, use, printing, updating, troubleshooting
    img/                        screenshots
  developer/
    README.md                   lead: developer documentation
    architecture.md             layers, functional units, patterns (Mermaid diagrams)
    update-and-switching.md     core modules, update and publish workflows, live switching
    scanning-and-documents.md   SANE adapter, documents, PDF output
    photo-album.md              detection, frame geometry and editor, cropping
    printing.md                 CUPS adapter and print dialog
    gui.md                      workbench, tabs, task runner, threads
    coding-standard.md          rules and measurable limits
    quality-gates.md            tools/check.sh, the six gates, pre-push hook
    ci.md                       GitHub Actions workflow and branch protection
    release-process.md          git-flow, versions, tags, patch delivery
    documentation-guide.md      how this documentation is organised
  concept/
    README.md                   lead: concept, revisions, roadmap, decisions
    scanbench-concept.md / .pdf concept revision 1
    settings-and-sessions.md    detail settings, transparency, configuration layers, sessions
    image-correction.md         white balance, levels, saturation, sharpening of photos
    img/, diagrams/             rendered diagrams and their Mermaid sources
~~~

Language of all documentation: English.
