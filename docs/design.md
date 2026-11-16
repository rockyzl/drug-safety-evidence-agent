# Evidence Desk design

Designed in [Paper](https://app.paper.design/file/01M7GZ4X3RT3H1KPN7BEJK659S). The actual exported design is preserved in `paper-export.jsx`; the working website translates it into semantic HTML, CSS and JavaScript.

Direction: an evidence-reading desk. White canvas, dark ink, blue links, IBM Plex Sans for the interface and IBM Plex Serif for the main heading. A question leads into a two-column draft/source workspace. Withheld claims and tool traces are expandable. A saved example is explicitly labeled; live progress comes from server events.

The GitHub design-tool review considered:

- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), MIT, inspected at commit `902bf616a0cc590d3f89f233f0c4e00072e549f0`. Used locally as a reference for accessibility, responsive layout and focus behavior. Its generated style recommendations did not fit the research task and were not adopted wholesale. No global MCP server installed.
- [Anthropic frontend-design skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design): visual hierarchy and deliberate typography.
- [21st Magic MCP](https://github.com/21st-dev/magic-mcp): reviewed, not installed; it requires separate service configuration and was unnecessary with Paper already connected.

The shipped interface has English copy, visible keyboard focus, mobile layout, reduced-motion support, self-hosted IBM Plex fonts (OFL license alongside font files), and no decorative stock imagery. Screen widths of 1440 and 390 pixels are checked with Playwright.

## Safety-brief revision

The Paper canvas was updated to foreground three perspectives: study evidence, FDA communication and the indexed prescribing information. The source drawer also gained a label entry. A screenshot checkpoint verified the revised heading and workspace. Paper then reported its weekly MCP limit, preventing the final screenshot and JSX export; `paper-export.jsx` remains the original v1 export. The finish-work tool succeeded. Code reuses the original style values and adds source coverage and section headings; the actual website is verified in desktop and mobile browsers.
