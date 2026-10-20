# Finding 131: the skin packs drawn whole and drawn again, headless, by
# frames.py - the Python the player runs and the pygame Debian ships.
FROM python:3.13-slim
RUN pip install --no-cache-dir pygame==2.6.1 pillow requests
ENV SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1
