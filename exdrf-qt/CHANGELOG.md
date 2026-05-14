# Changelog





## [Unreleased]

## [0.1.16] - 2026-05-14

## [0.1.15] - 2026-05-13

### Changed

- Update description

## [0.1.14] - 2026-05-13

### Added

- add PDF utilities and update template viewer

### Changed

- Added qt
- Context and worker in qt
- More importing
- Imported qt stuff
- Created dev
- app in qt
- editors
- Some base controls
- blob control
- The boolean control
- Date-time controls
- Numeric controls
- Text controls
- Nullable property
- Choices control
- Bring back models
- Progressive loading
- Fix loaded count
- Search list
- Relation selectors
- make is being silly
- Adjust child editor
- Can save the records
- Work on table fields
- More fields work. Assing sparse list
- Sparse list as cache
- fix enum
- Generate qt codde
- can change some in generated code. Single and multi editors not saving
- Fixing enums
- validation fixes in editors
- Show enums in list
- Implementtation for reference fields in table/list
- Prepare release 0.0.1
- tag_format is unknown
- Fix stringify for nested queries
- Bootstrap button in configuration
- Remove relations from load_only
- Fix typos in generator
- Sort model
- Added a filter editor in qt
- filter dsl tests
- Fixing filters
- Added a search box
- Can filter individual columns
- Added window title
- Ability to save the connection settings
- db toold, read-only and buddy
- Better sorting
- Move qt generator to its own module
- fix sql statement geneerators
- Some more work on filters
- Fix header icon for filter
- Reorder and hide columns in qt
- Make controls more flexible
- Template editor
- Better snippet handling in cide editor
- Overrides and html template
- Add auto-save to the editor
- Improved jinja build-ins
- Add a web page for controlling the URLs
- Use data-tables
- More work on the template viewer
- Added attr-dict
- Protect against loosing edits
- Added more jinja functions
- Working on word export 1
- exclude collapse
- Word no longer issues a warning
- Reformat code
- Move html2doc
- Can output tables with borders in word
- better color mapping for tables
- Title and subtitle styes
- Better image retrieval
- CRUD actions in qt. Rework Qt menus
- Replace editor/viewer with new router in list
- Use F5 and Ctrl+F5 to refresh
- Custom pdf save dialog
- Tree view update
- improve qt actions
- deletion in router
- Fix some issued created by previous commit
- get_one_db_item_by_id is now a context manager to allow for related items read
- Add alias in reference field filter to allow for multiple references from same resource to another resource
- Better filtering using has/any
- Make variables and related controls more flexible
- Fix settings in tree header
- Customisable read-only fields
- Remove unused selectors
- Priority  rows in model
- Database config functions moved to local settings class
- Added create hooks to qt templates
- Editor in selector
- Split field description into lines
- Added top-cache
- count_relationship and other fixes
- Allow choices in integer, float and string fields
- Set item in singe select
- Explicit model functions for dealing with IDs
- A json editor
- Split json editor
- preparing to replace sis
- New sise
- Fix typing of json dialog
- added filter header
- Toast and the proxy model
- Added a checkable combo
- Dealing with the missing html
- Fix all exdrf test failures
- exdrf-qt: enhance model system with improved field handling and comprehensive tests
- introduce . fields
- Update top level handler
- RefFilterByPart
- First attempt at a comparator
- Tree-view shows the diff
- Added a webview to the comparator
- Added comparator tests
- Improve template editor
- added a pdf viewer
- Account for parent missing in qt control
- prevent infinite loop when the item fails to load
- React to enabled/disabled
- Add prevent-save
- Improve field editors
- Add button in search box
- update pdf
- Add ability to use a callback fro adding a new record
- Add a label beneath the line control
- Added ability to recreate the field
- Allow for pre-exisintg connection string in context constructor
- Factor out base editor without record
- Start the session early
- Massage some code
- Delint moves imports around
- Safe block-signals implementation
- Can update the var bag while setting template source
- Fix selection slot
- Prepare records in worker thread
- PDF splitter
- Added excel i/o module
- Add exception guard
- Completer
- Add some logging
- top_level_handler now allows for optional ctx parameter
- Fixed bug in model regarding multple pk selection
- Better menus
- Generate menus and actions using the deffinition
- added command palette
- Added combo for choosing the database connection
- Some small fixes
- First steps towards a task runner
- Added tasks
- Improve documentation
- Check support
- Expand/collapse actions in grouped/category views; show result counts in ResultsModel; show synthetic 'passed' if no results; fix task step limit logic
- Added links to checks
- Improve formatting and remove unused imports
- Render the html for template viewer in a separate thread
- Better query constructor
- Showing some love to the qt model
- Delete-aware model
- Added some gui elements, save model settings
- Utility for reloading python modules
- Change list header to be more independent
- ListDbHeader
- Work with partially-initialized models in selectors.
- Update the connection settings dialog
- update the handling of read-only fields
- Added concepts
- Concepts integrates in qt
- Introducing new search lines
- Allow multiple levels in filters dot notation
- Fix search lines
- Some rogress for the ref editor
- Added ability to edit items in the list
- Working relational editor
- examine threads
- Load precision in ui for real/float editor. Visit hybrid properties.
- added docstrings
- Fix issue with terminating the thread abruptly
- Optional collector
- Transfer is better
- Transfer splitted to separate module for each class
- Database viewer implemented
- Ability to edit in database viewer
- Copy entire rows
- Visibility dialog. Better plugins
- Save and load database workspaces
- Add some count and color to transfer window
- Better count for transfer. verbose guard
- Clear verbose logging
- name threads
- Rewrite table viewer
- Fix t key. Cahneg error to warning in translation handler
- Use verbose
- Replace QThread with native threads
- Extend comparator
- Work on comparator
- Multiple improvements while working on the web app
- All tests are now green
- added more temates/plugins for generator
- Sync local sttings
- Changes after running tests in github
- actions trouble
- Eliminate lint inconsistencies
- Fix failing tests
- Check uniformization across projects
- Fix mypy errors
- A new attempt to clear the tests
- Fix a bunch of mypy errors. Change to unique pypi token. Fix license metadata.
- Fix license warning. More pypy fixes
- fix scm version
- more deploy attempts
- Break the dependency on qt
- Fix leftover exdrf_qt
- remove dynamic versioning

[0.1.14]: https://github.com/TNick/exdrf/compare/5c63497ca9407e723f6504245ac324094d46b6a6...v0.1.14-exdrf-qt
[0.1.15]: https://github.com/TNick/exdrf/compare/v0.1.14-exdrf-qt...v0.1.15-exdrf-qt
[0.1.16]: https://github.com/TNick/exdrf/compare/v0.1.15-exdrf-qt...v0.1.16-exdrf-qt
[unreleased]: https://github.com/TNick/exdrf/compare/v0.1.16-exdrf-qt...HEAD
