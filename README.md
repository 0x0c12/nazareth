simple discord bot
was gonna be made using twilight-rs but i actually cannot rust

dependencies(very ephemeral, will probably migrate to rust later):

```sh
pip install -r requirements.txt
```

i suggest creating an isolated environment(I used the name "lenv" for linux environments)
```sh
python -m venv env
```

also, place your discord bot token in a file named 'token.txt' in the src/ directory

also, if you want to use osu features, create a client on osu.ppy.sh and place the details as such:
```txt
<client_id>
<client_secret>
```

preliminary steps for quiche:

navigate over to the docker directory and build the image like so:
```sh
docker build -t quiche-python
```

also make sure that the user running the bot is able to connect to the docker. if you get anything like could not connect to docker socket, try the following:
```sh
usermod <username> -aG docker
```

or manually give your user permission in docker config

note: replay functionality for osu is broken and i won't be fixing it, feel free to modify the source if you're willing to make changes, i'm open to PRs
