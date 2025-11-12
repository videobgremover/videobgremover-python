# Changelog

All notable changes to the VideoBGRemover Python SDK will be documented in this file.

## [0.1.8] - 2025-11-12

### Removed
- Removed `ResultResponse` class - deprecated endpoint no longer exists in API

## [0.1.7] - 2025-11-01

### Added
- Model selection support: choose between videobgremover-original and videobgremover-light via RemoveBGOptions

## [0.1.6] - 2025-10-17

### Fixed
- Image background URLs now download to local temp files for faster composition performance

## [0.1.5] - 2025-10-09

### Fixed
- Background audio not mixing with foreground audio in compositions due to missing video metadata preservation in `.audio()` method

## [0.1.4] - 2025-10-03

### Added
- **Webhook support**: Added `webhook_url` parameter to `start_job()` method
- **Webhook delivery history**: New `webhook_deliveries()` method for checking delivery status

## [0.1.3] - 2025-09-27

### Removed
- Removed confusing `result_color()` method from client API
- Simplified API to use only status endpoint for getting results
- Fix basic example imports and remove deprecated parameters

## [0.1.2] - 2025-09-27

### Changed
- Clean up README with accurate examples and documentation
- Clean RemoveBGOptions API

## [0.1.1] - 2025-09-27

### Added
- Initial release of VideoBGRemover Python SDK
- Video background removal with AI
- Multi-layer video composition system
- Support for transparent video formats (WebM VP9, ProRes, Stacked Video, PNG Sequence)
- FFmpeg integration for video processing

[0.1.5]: https://github.com/videobgremover/videobgremover-python/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/videobgremover/videobgremover-python/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/videobgremover/videobgremover-python/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/videobgremover/videobgremover-python/compare/v0.1.0...v0.1.2
[0.1.1]: https://github.com/videobgremover/videobgremover-python/releases/tag/v0.1.1
