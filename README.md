# serp-event-registry

[![validate](https://github.com/rampstackco/serp-event-registry/actions/workflows/validate.yml/badge.svg)](https://github.com/rampstackco/serp-event-registry/actions/workflows/validate.yml)

A dated, sourced, confidence tagged public record of events that changed what search and AI answer surfaces return.

Rows cover AI answer surfaces including ChatGPT, Perplexity, the Gemini app, Google AI Overviews and Google AI Mode, as well as the classic Google SERP. The scope is therefore wider than the repository name suggests: SERP in the name marks the lineage of the data, not the boundary of it.

The registry exists because no vendor publishes this table. Google announces Google events, OpenAI announces OpenAI events, and volatility sensors report movement without a cause. Joining those into one timeline, with an explicit statement of how well each date is attested, is the work this repository does.

## The canon

`data/events.jsonl` is the source of truth. One JSON object per line, sorted by `event_date` ascending. Anything else that presents this data is a derivative of that file. `schema/event.schema.json` defines the row contract and `scripts/validate.py` enforces it in CI on every pull request.

## What a row means

A row asserts that a named actor did a named thing on a named date, on one or more named surfaces, and it cites where that claim comes from. The fields are documented in the schema. The ones that carry the most weight:

| Field | Meaning |
| --- | --- |
| `event_date` | The date the event is anchored to. For announced changes this is the announcement date, not the date the change finished reaching users. |
| `date_precision` | `day`, `week`, or `estimated`. Says how much to trust `event_date`. |
| `surface` | Which answer surfaces the event lands on. |
| `attribution` | How well the event and its date are attested. See below. |
| `source_urls` | Primary sources. Required for every row except `sensor_spike`. |
| `related_events` | Pointers to other rows. Used to link an observed spike to a later established cause without merging the two rows. |

## The attribution ladder

Four tiers, applied to the event and its date together:

1. `vendor_confirmed`. The vendor stated the event and the date on its own property. A Google core update with start and completion timestamps on the Search Status Dashboard sits here.
2. `vendor_announced`. The vendor announced the event, but the rollout window or the exact date is uncertain. A feature announced at a keynote and described as arriving "this week" sits here.
3. `community_inferred`. No vendor statement exists, and multiple independent observers converge on the event.
4. `hypothesis`. We suspect the event and say so.

A row never climbs the ladder because a volatility sensor agreed with it. Corroboration is recorded in `sensor_corroboration` and changes nothing about the tier.

## What this is not

It does not claim causation. It records events and observed volatility with stated confidence, and leaves the inference to whoever is doing the study.

## Citing

Cite the repository and the commit you read, because the file changes as events are added and as attribution tiers are revised:

```
serp-event-registry, rampstackco. https://github.com/rampstackco/serp-event-registry
Retrieved at commit <sha>.
```

## Proposing an event

Open a pull request that adds one line to `data/events.jsonl`, keeping the file sorted by `event_date`. Include at least one primary source URL: a vendor blog post, a status page, or an official changelog. Secondary reporting can support a row but does not carry it on its own.

Proposals without sources are closed. Proposals whose date is softer than the row claims are asked to lower `date_precision` or `attribution` rather than to drop the row.

## Running the validator

```
python -m pip install jsonschema
python scripts/validate.py
```

The validator checks the schema, `event_id` uniqueness and slug format, the date window, source presence and scheme, `related_events` resolution, and file ordering. It reports every failure it finds with the line number and the reason. It never edits the data file: an out of order file is an error to fix, not something to correct silently.

## License

MIT. See [LICENSE](LICENSE).
