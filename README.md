# hevy-mcp-eval

> **Status:** in development. Findings + methodology will land here after the first full eval run.

An eval suite for [Hevy](https://www.hevyapp.com/) MCP servers. Two questions:

1. **Does adding a Hevy MCP to Claude actually help a lifter, vs. simpler baselines?** (the more interesting question)
2. **Which Hevy MCP implementation adds the most value?** (the leaderboard)

Built on [Inspect AI](https://inspect.aisi.org.uk/), evaluates the three most-starred Hevy MCP servers plus a thin-wrapper control against CSV-in-prompt and no-data baselines.

See [`DESIGN.md`](./DESIGN.md) for the methodology.

## License

MIT
