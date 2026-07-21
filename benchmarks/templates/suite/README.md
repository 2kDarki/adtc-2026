# Your Suite Name

Brief description of what this suite evaluates.

## How to Create a New Suite

1. Copy this template directory to `suites/<your-suite-id>/v1/`
2. Edit `suite.json` with your suite metadata
3. Add evaluation items to `dataset.json`
4. Run validation: `python -m benchmarks.framework.cli validate <your-suite-id>`
5. Run coverage: `python -m benchmarks.framework.cli coverage <your-suite-id>`

## Categories

List your categories here.

## Items

Add items following the schema in `benchmarks/eval/schema.json`.

## Version History

- v1.0.0: Initial release
