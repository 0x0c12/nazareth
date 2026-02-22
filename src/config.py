with open("token.txt", 'r') as f:
    token = f.read().strip()    

with open("osu_secrets.txt", 'r') as g:
        OSU_CLIENT_ID, OSU_CLIENT_SECRET = (next(g).strip() for _ in range(2))
 
prefix = "~"
cog_folder = "cogs"
event_folder = "events"
brainrot_channels = [
    1458815919374467228,
    1446208166160371714,
    1468657544926072865,
    1467258234439204957,
    1473024408091361473,
    1471190640074166315,
    1470427392328601665,
    1435671633271587018
]

USER_WHITELIST = [
    948957008160231474,
    886937741667999774,
    754944535506845767,
    1004685195288522813,
    1169634638524846090,
    852050006080749570
]

QUICHE_DOCKER_IMAGE = "quiche-python"
QUICHE_TIMEOUT = 300
MAX_MESSAGES = 30
