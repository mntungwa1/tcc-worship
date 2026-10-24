# Release verification — TCC Worship v0.1.0

Verified 24 October 2026.

- Eight automated Python and Streamlit AppTest checks passed: workspace backup round-trip; independent service copies; invalid/unsafe backup rejection; lyric search and slide parsing; script-safe export; full Bible/reference validation; all seven app workspaces render; song creation and queuing; and Bible reference selection/queuing (some checks share a test).
- Offline Chromium tests passed with networking disabled: service preview isolation, projector popup, go-live, arrow-key slide movement, blackout/restore, stage display with next content, scripture output, full offline Bible book/chapter/verse navigation, multi-verse reference selection, next live verse, and phrase search. No JavaScript errors in the final browser checks.
- Visually inspected offline controller and projector renders.
- Bible bundle: 66 books; upstream empty text entries are documented in THIRD_PARTY_NOTICES.md.
- Python compile check and JavaScript syntax checks completed.

Not verified: a live Streamlit server preview (automatic approval review blocked startup's external IP lookup); a deployed Community Cloud instance; actual projector/audio equipment; video playback across all codecs; FreeShow API against a running installation; PDF and PowerPoint fidelity across arbitrary user files; concurrent team use.

The source package is a first working release and needs a rehearsal with church equipment before a live service.
