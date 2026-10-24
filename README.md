# TCC Worship
## Tabernacle Christian Centre

A working first release of a Streamlit worship preparation desk and a portable, offline HTML presentation controller. Version 0.1.0.

### Included
- Searchable song/text library; language and favourites filters; edit lyrics by verse/chorus.
- Holyrics-inspired Bible desk: verse reading pane on the left, book/chapter/verse grids on the right, reference lookup, phrase search, passage preview, verse selection, session favourites and history.
- Full 66-book World English Bible included locally. No Bible API key or internet needed. The offline HTML presenter includes the Bible workspace too, allowing unplanned scripture lookups during a live service.
- Additional authorised Bible JSON imports and comparison by matching book/chapter/verse.
- Service ordering, independent item copies and item duplication.
- Embedded images and MP4/WebM videos. PDF pages imported as images; PowerPoint **text-only** import. Export PowerPoint to PDF first to retain appearance.
- Portable offline presentation: preview/go-live separation, projector popup, stage popup with next-slide text and clock, blackout, keyboard controls and video play/pause/restart.
- Workspace JSON backup/restore, optional shared password, experimental local FreeShow REST controls.

This is an original implementation informed by worship software workflows. It is **not a source-code merger** and does not embed or rebrand Holyrics, OpenLP, Quelea or FreeShow. These desktop applications cannot be installed inside Streamlit Community Cloud as projector engines. The FreeShow adapter is optional and requires local setup.

### Windows setup
Install Python 3.11 or 3.12, extract the folder, open a terminal in it, and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:TCC_LOCAL_MODE="1"
python -m streamlit run app.py
```

Alternatively, after installing requirements into your default Python, double-click `start_windows.bat`.

### GitHub and Streamlit Community Cloud
1. Create a repository called `tcc-worship` in your GitHub account. A private repository is preferable when you will be preparing church material.
2. Upload the **contents** of this folder, including `data/`, `presenter.html`, `requirements.txt` and `.streamlit/config.toml`. Do not upload downloaded backups, private lyrics/media or secrets.
3. In Streamlit Community Cloud choose **Create app**, select the repository and branch, and set the entry point to `app.py`.
4. Select Python 3.11 or 3.12 and add this through the app's Secrets settings:

```toml
APP_PASSWORD = "choose-a-strong-church-password"
```

5. Deploy. Leave `TCC_LOCAL_MODE` unset on the cloud deployment.

Deployment status: code is prepared; repository creation and Streamlit sign-in are required to publish. The supplied connected GitHub tools do not provide repository creation, and there is no Streamlit deployment connector in this environment.

### Typical Sunday workflow
1. Open Songs & library; add or import your own authorised lyrics and add them to the service.
2. Open Bible desk. Type `John 3:16-18`, or pick a book, chapter and verse from the grids. Select the verses and add the passage.
3. Import announcements, video, images or PDF sermon slides. Add them from the library.
4. Arrange items in Service planner. Use Settings & backups to download a backup.
5. Open Presentation desk and download `TCC_Worship_Live.html`.
6. You can also try `TCC_Worship_Demo.html` included in the project straight away. Open the downloaded presentation file locally in Chrome or Edge. Press **Open projector** and allow popups. Move the popup to the extended second display; select **Full screen** there. Open stage view if required.
7. Choose an item/slide in preview, then press **Go live**. Arrow keys advance the live service; **B** toggles blackout. For videos, press Enable sound / Play inside the projector window once, then use the controller's media buttons.
8. Keep the controller window open. Playback is manual and codec-dependent; rehearse with the actual laptop and projector.

If a browser restricts popup access when opening a local HTML file, place the file in this folder and run `python serve_presenter.py`, then open the printed localhost URL. This optional server binds only to this computer.

### Data and current boundaries
- Library and service changes live in the Streamlit session. **Download a workspace backup before closing or restarting.** Cloud storage and team synchronisation are not implemented. A reconnect/restart can lose unsaved work.
- The workspace backup contains the library, prepared service and theme. Imported Bible datasets, Bible favourites and passage history are session-only; retain Bible source files separately. Imported versions are embedded in the offline presentation export.
- Extra Bible versions use the JSON structure below. They are not automatically downloaded from Holyrics. Only include texts you have permission to use.
- Images/videos accept individual files (20 MB each) and ZIP collections (512 MB per ZIP). The combined media collection supports 768 MB; the prepared service/metadata backup retains its 45 MB limit. Maximum 80 PDF pages.
- PPTX import retains text only; PDF retains page appearance but no animation/video. MP4 playback depends on the browser and codec. Streaming services/YouTube playback are not implemented.
- Offline HTML presentation is controlled from the exported controller on the same computer. The hosted Streamlit planner cannot control a presentation that has already been exported. In the offline presenter, the Holy Bible tab can look up and add new passages immediately; these live additions are not written back to the Streamlit workspace.
- Imported comparison versions match identical references; versification mapping is not implemented.
- Shared-password access is a basic gate, not individual user accounts or role-based administration.
- FreeShow commands are experimental, restricted to localhost, and not hardware-tested. Enable FreeShow's REST API first. TCC does not automatically import services into FreeShow yet.
- Automatic lyric following, microphone recognition, livestream/OBS output, countdowns and mobile remote control are planned extensions. Image/video backgrounds are available from the media library.

### Categorised image and video libraries

Open **Media & presentations → Image library / Video library**. Upload `Images.zip`
or `Videos.zip` into the matching library and click **Add files**. The importer
recognises category folders even inside an outer `Images/` or `Videos/` directory:
Praise, Worship, Offering, Communion, Sunday School, Prayer, Scripture, Welcome,
Baptism, and Easter and Christmas. Loose files and unknown folder names use the
selected upload category. Turn off folder recognition to put an entire batch into
one selected category.

Use **Browse category** to filter the collection, search within that category,
and page through twelve previews at a time. **Move to category → Save category**
changes an existing item's category. Background selection has the same category
filter. Duplicate media is skipped; a `CREDITS.csv` supplied in the ZIP retains
creator, licence and source information. Notes and preview HTML are not imported
as media.

Media bytes are streamed to a private disk cache rather than embedded in every
library item. The collection's files are not committed to GitHub. Streamlit Cloud
can clear this cache on restart/redeployment. Keep the original ZIPs or prepare a
new collection ZIP from the library. Workspace JSON contains the collection's
metadata/categories; restore the JSON, then upload the original ZIPs to reconnect
missing cached files. Selected media in saved services and offline HTML exports
is embedded so those preparations remain portable without the full collection.
Other collection media stays in its separate ZIP. For a local installation,
`TCC_MEDIA_DIR` can point to a durable private directory.

### Bible JSON format
```json
{"name":"Authorised version","credit":"Required attribution","books":{"John":{"3":{"16":"Verse text","17":"Verse text"}}}}}
```

### Validation
```bash
python -m pip install pytest
python -m pytest -q
```
See `VALIDATION.md` for checks performed on this release. Run a full rehearsal with your church's files and equipment before using it for a service.

### References and acknowledgements
- Holyrics Bible navigation and comparison workflow: https://holyrics.com.br/software.php and https://holyrics.com.br/tips/features.html
- FreeShow and documented REST actions: https://github.com/ChurchApps/FreeShow and https://freeshow.app/api
- Quelea: https://github.com/quelea-projection/Quelea
- OpenLP: https://openlp.org/
- Streamlit architecture: https://docs.streamlit.io/develop/concepts/architecture/architecture
- See `THIRD_PARTY_NOTICES.md` for Bible data provenance and dependency licences.

### Twelve selected free Bible versions
Open **Bible desk → Browse 12 free Bible versions** to add BSB, KJV, WEB, ASV, BBE, FBV, Darby, YLT, Revised Version, Webster, Geneva 1599 or LSV. WEB is already included. Additional versions download on demand; internet is required for that download. Select an added translation in the Bible version dropdown.

Use **Download selected Bible JSON** to retain a version across sessions and re-import it under Settings & backups. Added versions are included in offline presentation exports. The workspace backup still saves the service/library rather than entire Bible datasets. Source attribution and licence notices accompany added translations. The catalogue is a curated selection, not every free translation worldwide.
