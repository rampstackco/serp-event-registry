# Methodology

How rows get into `data/events.jsonl`, how their confidence tier is chosen, and what this registry cannot see.

## Scope

An event belongs here if it plausibly changed what a search or AI answer surface returns to a general audience, and if it can be pinned to a date.

Surfaces in scope: the classic Google SERP, Google AI Overviews, Google AI Mode, Google Discover, ChatGPT, Perplexity, the Gemini app, Bing, and Claude. Events in scope: model releases, search feature changes, confirmed core updates, confirmed spam updates, other ranking system changes, policy changes affecting what a surface will answer, and observed volatility spikes.

Google Discover is in scope because Google confirms Discover updates on the same status dashboard it uses for Search updates, at the same evidentiary standard. Discover rows carry `surface` of `google_discover` and must not be pooled with web Search rows, which is stated on the row rather than left to the reader.

## Inclusion criteria

A row is admitted when all of the following hold:

1. It has a date, or a date range narrow enough to record with `date_precision` of `week`.
2. It has at least one primary source, unless it is a `sensor_spike`. A primary source is a vendor blog post, a vendor status page, or an official changelog. Trade press is corroboration, not a source of record.
3. It affects a general audience rather than a closed test group. A staged rollout to a subscriber tier qualifies. A private partner preview does not, unless the preview itself is the event being recorded and the description says so.
4. It is distinguishable from an existing row. If a change is an increment of an event already recorded, extend the existing description instead of adding a row.

## Exclusion criteria

Model releases confined to an API with no consumer surface behind them are excluded, because the registry tracks what an answer surface returns rather than what a vendor shipped. Developer tooling, pricing changes, and enterprise packaging changes are excluded for the same reason. Point releases that do not change the default model behind a consumer surface are excluded and are noted in the pull request that considered them.

## The attribution ladder

The tier describes the event and its date together. A well known event with a poorly attested date does not get the top tier.

**`vendor_confirmed`.** The vendor stated the event and the date on its own property, and the date can be read off that property today.

> Example: the March 2026 core update. The Google Search Status Dashboard carries a start of 27 March 2026 at 02:00 US/Pacific and a completion of 8 April 2026 at 06:00 US/Pacific. Both timestamps are vendor published.

**`vendor_announced`.** The vendor announced the event, but the rollout window is uncertain, or the date recorded here was taken from contemporaneous reporting rather than from a dateline on the vendor page.

> Example: AI Mode reaching all United States Search users. Google announced it at I/O on 20 May 2025 and said the tab would appear during that week. The announcement date is firm. The date any given user saw the tab is not.

> Example: the GPT-5 release. The vendor post confirms the release, but carries no dateline this registry can read, so the 7 August 2025 date rests on contemporaneous reporting and the row is capped at this tier.

For OpenAI events, the dated ChatGPT release notes at help.openai.com (article 6825453) are the dated official post that the `vendor_confirmed` tier requires, and the earlier practice of capping an OpenAI row at `vendor_announced` because openai.com refuses automated fetches is retired for any event those notes carry (recorded 1 October 2026).

**`community_inferred`.** No vendor statement exists and multiple independent observers converge on the event and its approximate date.

**`hypothesis`.** We suspect the event happened and we say so in the description. A hypothesis row is a claim about our own uncertainty, and it stays at this tier until a vendor statement or independent convergence moves it.

Where a community date and a vendor date disagree, the vendor date is used, the tier is set to `vendor_announced`, and the discrepancy is stated in the description.

Rows move down the ladder as readily as up. If a source is retracted or a vendor page loses the dateline that justified a tier, the row is demoted and `last_updated` is bumped.

## Date precision

`day` means the event is pinned to a calendar day. Use it for announcements and for dashboard published rollout starts.

`week` means the event is known to fall in the week beginning at `event_date`. Use it when a vendor says a change shipped "last week" or when reporting places an event within a week but no further.

`estimated` means the date is inferred and could be wrong by more than a week. Use it for silent changes noticed after the fact.

`event_date` anchors to the start of an event, not its completion. For a core update this is the announced rollout start. For an announced feature this is the announcement date, even when the feature reached users later. Completion dates, where a vendor publishes them, go in the description rather than in a second field, so that a study joining on `event_date` gets one row per event and decides its own window.

## Sensor spikes

A `sensor_spike` row records observed volatility and nothing else. It never names a cause, and it never carries a `source_urls` claim it cannot support, which is why it is the only event type permitted to omit sources.

Spike rows are proposed by an automated capture process that runs outside this repository and opens a pull request. They are never committed automatically. A human reviews each proposal and either admits it, merges it into an existing row, or rejects it.

When a cause is later established for a spike, the spike row gains a `related_events` pointer to the causal row. The two rows are never merged. Keeping them separate preserves the distinction between what was measured and what is believed to explain it, which is the distinction the registry exists to hold.

Published `sensor_corroboration` entries name their panel with an opaque label such as `panel_a`. The mapping from label to the underlying keyword set, market, and collection method is internal and is not published here. Labels are stable across rows, so a reader can tell that two rows cite the same panel without learning what that panel is. A reading is worth no more than the label's track record, and the label carries no claim about panel size or representativeness.

**Confirmed events are not a uniform calibration class** (recorded 1 October 2026, from a readout dated 28 August 2026). The capture process that proposes spike rows was read across the window of the August 2026 spam update, which the Search Status Dashboard dates from 18 August at 09:27 to 21 August at 01:49 US/Pacific. Across twenty panel days its mean reading sat a tenth of a standard deviation below the series mean and no panel exceeded a z score of 0.95, although the same instrument has resolved movement above z of 4 on other days, so the null is not obviously a sensitivity failure. The most likely reading is that the panels sample consumer informational queries, and a spam update concentrates its displacement where spam competes, which those panels do not overlap. The consequence for this registry is that "confirmed Google events" is a mixture the sensor sees non uniformly: core updates and spam updates are both vendor confirmed, but they land on different parts of the results. Confirmed rows therefore cannot be pooled as one ground truth class for setting or testing a spike threshold, and any calibration against them has to be stratified by `event_type` and stated per type.

## Related events

`related_events` records that two rows should be read together. It carries no direction and no causal claim. Typical uses are linking a spike to a candidate cause, linking an announcement to a later general availability row, and linking two rollouts that overlap in time and therefore confound each other.

Overlapping events are recorded as separate rows even when they are impossible to separate in the data. The December 2025 Google core update and the GPT-5.2 release share a start date. Both rows exist, both point at each other, and neither claims the volatility in that window.

## Ordering and identity

`event_id` is a slug of the form `YYYY-MM-DD-short-name` whose date portion equals `event_date`. Identifiers are stable once merged. If a date is later corrected, the row keeps its original identifier and the mismatch is resolved by issuing a new row and pointing the old one at it, because downstream joins hold the old identifier.

The file is sorted by `event_date` ascending, with `event_id` breaking ties. The validator fails on disorder rather than sorting the file, so that an unexpected reordering shows up as a failed check rather than as a silent diff.

## Known limitations

**Silent model swaps are unobservable.** Vendors change the model behind a consumer surface without announcing it, and routing layers can shift traffic between model variants continuously. Nothing in this registry detects that. A gap in the timeline is not evidence that a surface was stable.

**Absence of a row is not absence of an event.** The registry records what was announced or observed. It is a lower bound on how often these surfaces changed.

**Announcement dates are not exposure dates.** Most rows anchor to an announcement. The date a population actually saw a change is later by an interval that vendors rarely publish.

**Geographic and language coverage is uneven.** Vendor announcements about multi country rollouts usually do not enumerate countries. Rows record what the vendor said, so a market cannot be assumed to be covered on the announcement date.

**Sources rot.** Vendor pages are edited, moved, and removed. A row is only as good as its sources on the day they were checked, and the check date is the row's `last_updated`.

**The registry is a record, not an explanation.** Every causal reading of this data is the reader's own.
