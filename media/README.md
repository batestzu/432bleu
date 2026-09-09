# media/

Large binaries served by the box office at `/media/*` — the pitch-deck video today,
show footage later.

**Nothing in here is tracked.** `.gitignore` keeps everything but this README and
`.gitkeep` out of the repo, on purpose: a 4MB rough cut is survivable in git history,
a 200MB master is not, and neither can ever be removed once pushed.

The directory is bind-mounted read-only into the boxoffice container as `/app/media`
(see the `volumes:` block on the `boxoffice` service in `docker-compose.yaml`). It sits
at the repo root rather than under `boxoffice/`, which keeps it out of that service's
Docker build context — so these files never enter an image layer either.

## Putting a file here

    scp yourfile.mp4 root@432bleu.com:/home/vspot/workadventure/media/
    ssh root@432bleu.com 'chown vspot:vspot /home/vspot/workadventure/media/yourfile.mp4'

`root` is used because it is the account that takes a key from the laptop; `vspot`
does not, so an scp to it just prompts for a password. Working on the box already,
skip all that and copy the file straight into `~/workadventure/media/`.

It is live immediately at `https://boxoffice.432bleu.com/media/yourfile.mp4` — no
rebuild, no restart, because the container reads through the bind mount. Responses
inherit the app's default `Cache-Control: no-cache`, so replacing a file under the
same name takes effect on the next load instead of being pinned in browser caches.

`.gitkeep` must stay committed: it guarantees `media/` exists after a fresh clone, so
Docker mounts the real directory instead of silently creating a root-owned empty one.
