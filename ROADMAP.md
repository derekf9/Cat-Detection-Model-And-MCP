ROADMAP.md

Hardware 

Raspberry Pi 5 (4GB or 8GB) — ~$60–$80. Get the 5 over the 4; the CPU is roughly 2–3x faster and the camera interface improved. 4GB is plenty for this project; 8GB only matters if you want headroom for other stuff.
Official Pi 5 power supply (27W USB-C) — ~$12. Don't cheap out; underpowered supplies cause weird intermittent failures that'll waste your weekend.
microSD card, 32GB or 64GB, A2-rated — ~$10. SanDisk Extreme or Samsung Evo Select. A2 rating matters for random I/O.
Active cooling case — ~$15. The Pi 5 throttles without a fan, and you'll be running inference continuously.
Pi Camera Module 3 — ~$25. The newer one with autofocus. Or a USB webcam (Logitech C270, ~$20) if you'd rather — both work, USB is easier to position.
Camera cable for Pi 5 — ~$3. The Pi 5 uses a different cable than the Pi 4 (smaller connector). Easy to forget.

Strongly recommended:

Coral USB Accelerator — ~$60. This is the one "do I really need it" item. Short answer: not strictly, but it makes everything 5–10x faster for ML inference and means your Pi can sit at low CPU load instead of running hot. For a resume project where you want smooth demos, get it.

The phased plan
I'm structuring this as eight phases. Each one ends with something working we can git commit and, if you want, demo. Don't move on until the current phase actually runs.

Phase 1 — Pi setup and repo skeleton. Flash Raspberry Pi OS (64-bit, Bookworm), enable SSH and the camera interface, get on your wifi, install Python tooling, create the project repo with a sensible directory layout, and push it to GitHub. End state: you can SSH into the Pi and python --version works.
Phase 2 — Camera capture. Write a small Python script using picamera2 (or opencv if you went USB) that grabs a frame and saves it to disk. Then a second script that grabs frames continuously when motion is detected (frame-differencing — no ML yet, just "did pixels change a lot"). End state: a folder on the Pi filling with snapshots when something moves in front of the camera.
Phase 3 — Cat-vs-not-cat with a pretrained model. Install a pretrained object detector (YOLOv8n is the easiest starting point — pip install ultralytics). Wire it up so each motion-triggered snapshot gets classified. The model already knows what a cat is — no training yet. End state: snapshots get tagged "cat / dog / person / nothing interesting" and sorted into folders automatically.
Phase 4 — Data collection for your cat. Now you start using the system to collect training data for the next phase. Let it run for a week or two, capturing every "cat" detection. You'll naturally end up with hundreds of photos of your cat in different poses, lighting, and times of day. End state: a labeled dataset of "my cat" photos, plus you find some "other cats" photos online for the negative class.
Phase 5 — Fine-tune to recognize your cat. This is the ML learning moment, but gentle. We'll use a tool called fastai or a Hugging Face pipeline — both let you fine-tune an image classifier in ~20 lines of Python. You'll train on a laptop or Colab (free GPU), not the Pi. Output: a small model file you copy to the Pi. End state: the Pi can now distinguish your cat from a stranger cat with maybe 90%+ accuracy.
Phase 6 — The MCP server. Now MCP enters. Write a Python MCP server on the Pi that exposes tools: get_recent_detections, get_snapshot, get_cat_status ("inside" / "outside" based on direction of travel or last seen), get_stats. Run it as an SSE server on the Pi's local IP. End state: from your laptop's Claude Desktop, you can ask "did Mimi go out today?" and get a real answer.
Phase 7 — Persistence and history. Add a SQLite database so detections, snapshots, and metadata persist. Expose richer queries through MCP — date ranges, comparisons, "show me the unrecognized animal from last Tuesday at 3am." This is where the project starts feeling like a real product. End state: weeks of history queryable from Claude.
Phase 8 — Polish for the resume. Systemd unit so it autostarts on boot, a README with architecture diagram and demo GIF, basic tests, a writeup of what you learned. Optionally, a tiny web dashboard (Flask + a single HTML page) for non-Claude users. End state: someone can read the repo and immediately get what you built.
If you want to push further later: door mechanism (Phase 9), prey detection as a separate classifier (Phase 10), multi-cat households, notifications via a separate MCP, etc. But Phase 8 is already a complete, demoable, resume-worthy project.