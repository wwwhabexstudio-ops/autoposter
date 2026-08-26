# AutoPoster Video Generation Architecture

## Goal

Generate both short-form and long-form videos using a provider-neutral pipeline.

## Pipeline

1. Topic / idea
2. Research and evidence collection
3. Script generation
4. Scene breakdown
5. Asset selection or generation
6. Voiceover generation
7. Subtitle generation
8. FFmpeg assembly
9. Quality checks
10. Platform-specific exports
11. Human approval
12. Scheduling and publishing
13. Analytics feedback

## Long-form

Long videos are not generated as one giant AI-video request. They are assembled from many scenes/chapters. This allows 5-, 10-, 20-, or 30-minute projects to be rendered from smaller assets, retried per scene, and reused for Shorts/Reels/TikTok clips.

## $0-first strategy

- Python for orchestration
- SQLite for job state
- FFmpeg for editing/assembly
- Local/open-source models when practical
- External AI providers only through optional adapters
- Official social APIs for publishing

The system must never promise viral reach or attempt to manipulate platform ranking systems.
